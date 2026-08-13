"""Embedded Pathling executor for a concept-port attempt.

The single execution path for both legs of the loop.  Pathling runs
**in-process** on top of PySpark, reading a Delta warehouse directly: no FHIR
server, no HTTP, no serialisation boundary between the query and its result.

That is what makes the full-data leg possible.  Petrichor compute nodes have
no internet access and no FHIR server, but they do have the warehouse sitting
beside them on Lustre, so the job embeds Pathling rather than calling one.
:mod:`mimic_utils.demo_runner` runs this same executor locally against the demo
warehouse, which is the only way to debug the HPC path without a queue -- and
the reason a demo failure is a genuine prediction about the full run rather
than a guess.

**The local JVM is leased, one at a time** -- see :func:`_acquire_spark_lease`.
The laptop has one heap and one repo-root ``spark-warehouse/`` Derby metastore,
and parallel goals would otherwise start several sessions in the same working
directory.  The HPC path never sets the env var that enables the lease, so the
compute node is lock-free by construction and never touches a Lustre ``flock``.

The attempt layout encodes the binding this relies on: **the ViewDefinition's
label is the SQL table name**, bound through ``createOrReplaceTempView``.  Get
the label wrong and ``concept.sql`` selects from a table that was never
registered.

Pathling owns Spark session creation (``PathlingContext.create()``): the FHIR
encoders and the Delta jars must be on the classpath before the JVM starts,
and hand-building a bare ``SparkSession`` is what produces the
``JavaPackage is not callable`` failure.  For the same reason the driver heap
is fixed through ``PYSPARK_SUBMIT_ARGS`` *before* first context creation --
``SparkConf`` cannot resize a heap that already exists.

**Both legs run in one fixed zone** (:data:`SESSION_TIMEZONE`), pinned here
rather than in any ``concept.sql``.  A session zone can only damage MIMIC's
de-identified wall-clock datetimes, and the damage is silent and rare enough to
survive review -- so it is removed once, at the single point where the JVM is
created, instead of being re-argued in every generated query.

``pathling`` and ``pyspark`` are optional dependencies (extra ``fhir``).  They
are imported lazily so that the rest of ``mimic_utils`` -- the state machine,
the DAG, the comparator -- keeps working on a machine that has neither.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mimic_utils.demo_runner import (
    DemoRunError,
    discover_view_definitions,
    read_concept_sql,
)

# Env keys, so a job script can point the executor at a warehouse without
# threading a flag through every layer.
WAREHOUSE_ENV_KEY = "MIMIC_FHIR_WAREHOUSE"
DRIVER_MEMORY_ENV_KEY = "SPARK_DRIVER_MEMORY"

#: Path to the local Spark lease file.  Absent means no leasing at all, which
#: is how the HPC job stays lock-free: the Slurm script never sets it.
SPARK_LOCK_ENV_KEY = "MIMIC_SPARK_LOCK"

#: How long a goal will wait for the JVM before giving up.  Coupled to the
#: `VALIDATING_DEMO` staleness threshold in `LOOP_CONTRACT.md`, which must stay
#: larger than this or a loop queued behind the lease reads as dead.
SPARK_LEASE_TIMEOUT_SECONDS = 3600
SPARK_LEASE_POLL_SECONDS = 5

DEFAULT_DRIVER_MEMORY = "4g"

#: The one zone every leg of the loop runs in.  MIMIC datetimes are de-identified
#: *wall-clock* values, not instants, so the only thing a session zone can do to
#: them is damage: Spark 4.0.2 ``DATE_FORMAT`` and ``DATE_TRUNC`` consult
#: ``spark.sql.session.timeZone`` even for a zone-*less* ``TIMESTAMP_NTZ``, and a
#: wall time that lands in that zone's DST spring-forward gap comes back an hour
#: later.  Under the machine default here -- ``Australia/Sydney`` on both the
#: laptop and Petrichor -- 02:xx on the first Sunday in October became 03:xx,
#: which is the whole "October family" of phantom divergences.  ``UTC`` has no
#: DST in any year, so no wall clock can be normalised by accident.
#:
#: Overridable for a deliberate experiment, never for convenience: setting this
#: to a DST-observing zone reintroduces the defect.
SESSION_TIMEZONE_ENV_KEY = "MIMIC_SPARK_TIMEZONE"
SESSION_TIMEZONE = os.environ.get(SESSION_TIMEZONE_ENV_KEY) or "UTC"


def _pin_session_timezone() -> None:
    """Fix the process zone before the JVM reads it.

    Ordering is the whole point: the JVM samples ``TZ`` once at startup and
    derives Spark's default session zone from it, so this must run before
    ``PathlingContext.create()``.  It also pins DuckDB and Python ``datetime``
    in this same process, which is why it is an env export rather than a Spark
    conf alone -- the comparator runs in here too.

    ``spark.sql.session.timeZone`` is set again after the context exists (see
    :meth:`_EmbeddedContext._context`); this half only covers what the JVM
    decides at boot.
    """
    os.environ["TZ"] = SESSION_TIMEZONE
    # No-op on Windows, where tzset does not exist; every host that runs this
    # loop is POSIX.
    if hasattr(time, "tzset"):
        time.tzset()


class EmbeddedRunError(RuntimeError):
    """The embedded executor could not start or could not run the attempt."""


def _acquire_spark_lease(holder: Optional[str]) -> Optional[Any]:
    """Take the exclusive local-Spark lease, or return ``None`` if unleased.

    An OS-level ``flock`` on the file named by ``$MIMIC_SPARK_LOCK``.  Parallel
    goals are composed outside the loop (one per terminal), and the scarce
    resource they share is this machine: one driver heap, and one repo-root
    ``spark-warehouse/`` Derby metastore that two sessions in the same working
    directory collide on.  The wait is logged so the duty cycle of that
    serialisation can be measured rather than guessed at.

    ``flock`` rather than a flag in ``state.json``: the kernel releases it when
    the holder dies, so a crashed run cannot strand the lease, and there is no
    read-then-write window for two agents to slip through.  The pid/holder
    payload written into the file is **diagnostics only** -- correctness comes
    entirely from the lock, never from the contents.

    Returns the open file handle, which the caller must keep alive: closing it
    releases the lease.
    """
    raw = os.environ.get(SPARK_LOCK_ENV_KEY)
    if not raw:
        return None

    import fcntl

    lock_path = Path(raw).expanduser()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+", encoding="utf-8")  # noqa: SIM115 - held for the session
    started = time.monotonic()
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            waited = time.monotonic() - started
            if waited >= SPARK_LEASE_TIMEOUT_SECONDS:
                handle.seek(0)
                incumbent = handle.read().strip() or "(no diagnostics written)"
                handle.close()
                raise EmbeddedRunError(
                    f"timed out after {waited:.0f}s waiting for the Spark lease "
                    f"at {lock_path}. Held by: {incumbent}. Nothing was run."
                ) from None
            time.sleep(SPARK_LEASE_POLL_SECONDS)

    waited = time.monotonic() - started
    handle.seek(0)
    handle.truncate()
    handle.write(
        json.dumps(
            {
                "pid": os.getpid(),
                "holder": holder,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        + "\n"
    )
    handle.flush()
    # stderr, not stdout: this is progress, and a caller running with --json
    # parses stdout. Two of these lines ahead of the object made `jq` fail.
    print(f"spark lease acquired after {waited:.0f}s", file=sys.stderr, flush=True)
    return handle


def resolve_warehouse(explicit: Optional[str | Path] = None) -> Path:
    """Resolve the Delta warehouse path from *explicit* -> env, and verify it.

    There is deliberately no default: the demo warehouse and the 156 GB full
    warehouse are not interchangeable, and silently picking one would let a
    full-data verdict be produced from demo data.
    """
    raw = explicit if explicit is not None else os.environ.get(WAREHOUSE_ENV_KEY)
    if not raw:
        raise EmbeddedRunError(
            "No Delta warehouse given: pass --warehouse or set "
            f"{WAREHOUSE_ENV_KEY}. There is no default -- the demo and full "
            "warehouses must never be confused."
        )
    path = Path(raw).expanduser()
    if not path.is_dir():
        raise EmbeddedRunError(f"Delta warehouse not found: {path}")
    return path


class EmbeddedExecutor:
    """A lazily-started embedded ``PathlingContext`` over a Delta warehouse.

    The context is created on first use and reused for the whole run: JVM
    startup and FHIR encoder registration cost seconds, and a concept may
    register several ViewDefinitions before its SQL runs.
    """

    def __init__(
        self,
        warehouse_path: str | Path,
        *,
        driver_memory: Optional[str] = None,
        holder: Optional[str] = None,
    ) -> None:
        self.warehouse_path = str(warehouse_path)
        self.driver_memory = driver_memory
        #: Written into the lease file for diagnostics only.
        self.holder = holder
        self._ctx: Any = None
        self._lease: Any = None

    # -- lifecycle ---------------------------------------------------------

    @staticmethod
    def _configure_spark_launch(driver_memory: Optional[str]) -> None:
        """Bound the driver JVM before it starts.

        An explicit ``PYSPARK_SUBMIT_ARGS`` (what the Slurm script sets, sizing
        the driver for the compute-node allocation) or an already-live session
        is left untouched: the caller with the most context wins.
        """
        try:
            from pyspark.sql import SparkSession
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise EmbeddedRunError(
                "pyspark is not installed. The embedded executor needs the "
                "'fhir' extra: uv pip install 'mimic_utils[fhir]'"
            ) from exc

        if SparkSession.getActiveSession() is not None:
            return
        if "PYSPARK_SUBMIT_ARGS" in os.environ:
            return
        memory = (
            driver_memory
            or os.environ.get(DRIVER_MEMORY_ENV_KEY)
            or DEFAULT_DRIVER_MEMORY
        )
        os.environ["PYSPARK_SUBMIT_ARGS"] = (
            f"--driver-memory {memory} --conf spark.ui.enabled=false pyspark-shell"
        )

    def _context(self) -> Any:
        if self._ctx is None:
            # Before the JVM, not after: the point is that only one exists.
            self._lease = _acquire_spark_lease(self.holder)
            _pin_session_timezone()
            self._configure_spark_launch(self.driver_memory)
            try:
                from pathling import PathlingContext
            except ImportError as exc:  # pragma: no cover - env-dependent
                raise EmbeddedRunError(
                    "pathling is not installed. The embedded executor needs "
                    "the 'fhir' extra: uv pip install 'mimic_utils[fhir]'"
                ) from exc
            self._ctx = PathlingContext.create()
            conf = self._ctx.spark.conf
            # Belt to the TZ export's braces. TZ fixes the zone the JVM starts
            # with; this fixes the zone Spark SQL actually resolves against, and
            # survives a caller who set PYSPARK_SUBMIT_ARGS or TZ themselves.
            conf.set("spark.sql.session.timeZone", SESSION_TIMEZONE)
            # Adaptive execution coalesces the demo's tiny shuffles (the
            # 200-partition default is pure overhead on 100 patients) and
            # still scales up on full MIMIC.
            conf.set("spark.sql.adaptive.enabled", "true")
            conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
        return self._ctx

    @property
    def spark(self) -> Any:
        """The live SparkSession (starting the context if needed)."""
        return self._context().spark

    def close(self) -> None:
        """Stop the Spark session and release the lease, if either was taken.

        The lease is released last, and only after the JVM is down, so the next
        waiter never starts a second session against a live metastore. A crash
        that skips this path is handled by the kernel dropping the ``flock``.
        """
        try:
            if self._ctx is not None:
                try:
                    self._ctx.spark.stop()
                finally:
                    self._ctx = None
        finally:
            if self._lease is not None:
                try:
                    self._lease.close()
                finally:
                    self._lease = None

    def __enter__(self) -> "EmbeddedExecutor":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- execution ---------------------------------------------------------

    def register_views(self, definitions: Sequence[Dict[str, Any]]) -> List[str]:
        """Materialise each ViewDefinition as a temp view named by its label.

        *definitions* is the structure :func:`discover_view_definitions`
        returns, so the filename label -- already validated against the
        ViewDefinition's ``name`` -- is what the SQL will select from.
        """
        ctx = self._context()
        source = ctx.read.delta(self.warehouse_path)
        labels: List[str] = []
        for definition in definitions:
            label = definition["label"]
            try:
                view = source.view(json=json.dumps(definition["body"]))
                view.createOrReplaceTempView(label)
            except Exception as exc:  # noqa: BLE001 - surface Spark/Pathling verbatim
                raise EmbeddedRunError(
                    f"ViewDefinition {label!r} failed to materialise: {exc}"
                ) from exc
            labels.append(label)
        return labels

    def run_sql(self, sql: str) -> Any:
        """Evaluate *sql* against the registered views, returning a DataFrame."""
        try:
            return self._context().spark.sql(sql)
        except Exception as exc:  # noqa: BLE001 - surface Spark verbatim
            raise EmbeddedRunError(f"concept SQL failed: {exc}") from exc


def execute_attempt(
    attempt_dir: str | Path,
    *,
    warehouse_path: str | Path,
    executor: Optional[EmbeddedExecutor] = None,
    driver_memory: Optional[str] = None,
) -> Tuple[Any, EmbeddedExecutor, List[str]]:
    """Run one attempt's artifacts embedded, returning ``(df, executor, labels)``.

    The executor is returned rather than closed: the caller still needs the
    live session to write the result, and closing it would invalidate the
    lazily-evaluated DataFrame.
    """
    attempt = Path(attempt_dir)
    if not attempt.is_dir():
        raise EmbeddedRunError(f"Attempt directory not found: {attempt}")

    try:
        definitions = discover_view_definitions(attempt)
        sql = read_concept_sql(attempt)
    except DemoRunError as exc:
        # The artifact contract is shared with the server backend; only the
        # error type is rebranded so a caller can catch one class.
        raise EmbeddedRunError(str(exc)) from exc

    owned = executor or EmbeddedExecutor(
        warehouse_path, driver_memory=driver_memory, holder=str(attempt)
    )
    labels = owned.register_views(definitions)
    return owned.run_sql(sql), owned, labels
