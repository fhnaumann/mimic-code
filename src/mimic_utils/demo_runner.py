"""Pathling demo runner for a concept-port attempt.

Takes an attempt directory containing the two hand-authored artifacts:

``ViewDefinition.<label>.json``
    One or more SQL-on-FHIR ViewDefinitions.  ``<label>`` in the filename is
    the SQL table name the concept SQL selects from, and must equal the
    ViewDefinition's ``name``.
``concept.sql``
    Spark SQL producing the ported concept, selecting from those labels.

and executes them through **embedded Pathling on Spark** over the demo Delta
warehouse -- the same executor, artifact format and comparator that
:mod:`mimic_utils.full_runner` uses on the HPC.  There is exactly one execution
path, deliberately: the full leg has no alternative (compute nodes have no FHIR
server), so any second path would mean the Spark leg's first real execution
happens on the HPC, where a failure costs a queue slot instead of seconds.

Local runs are serialised by the Spark lease when ``$MIMIC_SPARK_LOCK`` is set
(:func:`mimic_utils.embedded_runner._acquire_spark_lease`).  Parallel goals
share one laptop -- one driver heap, one repo-root ``spark-warehouse/`` Derby
metastore -- so a demo run may block for minutes before its JVM starts.  The
wait is logged; nothing else about the run changes.

The run:

1. Bind each ViewDefinition label to a temp view via ``createOrReplaceTempView``.
2. Execute ``concept.sql`` and take the authoritative column order and types
   from the resulting DataFrame.
3. Write ``candidate.demo.parquet`` straight from that DataFrame.
4. Run the **shape gate** against the oracle manifest and write
   ``shape.demo.json``.

Parquet, not a text format, and that is load-bearing.  Parquet carries the Spark
schema; a text round-trip does not, so the gate would end up checking DuckDB's
re-inference of serialised JSON rather than the types the HPC run will actually
produce.  An all-null column -- legitimate, when a concept's shape requires a
column MIMIC-on-FHIR cannot populate -- infers as ``JSON`` and fails a
``SMALLINT`` expectation; a ``DECIMAL`` serialises to a string and fails a
numeric one.  Both are artifacts of the artifact format, not port bugs.  Parquet
removes the class entirely, and removes the ``collect()`` into Python with it.

This is a **cheap shape gate, not a correctness gate**.  See
``mimic-iv/concepts_fhir/LOOP_CONTRACT.md``, which is authoritative.  It exists
to stop a malformed port from consuming a 10-30 minute HPC run, and checks only:

* did the ViewDefinition and SQL execute at all,
* do the column **names** match the oracle's,
* are the column **types** compatible.

Row count is **not** gated here, and **0 rows yields ``unsure``, never
``fail``** -- the 100-patient demo cohort legitimately contains nothing for
some concepts (``neuroblock`` has 0 demo rows and 14,174 on full data).

Consequently the demo run needs **no oracle export**: the target shape comes
from ``oracle_manifest.full.json``.  Correctness is decided later, on full
data, by the keyed diff.

The verdict is never hand-calculated: it comes from
:func:`mimic_utils.compare_port_results.compare_shape`.

Attempt artifacts are write-once.  A re-run needs a new attempt, so the
runner refuses to overwrite ``candidate.demo.parquet`` or ``shape.demo.json``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mimic_utils.compare_port_results import compare_shape, write_comparison

#: Demo Delta warehouse, used when the runner is invoked without an explicit
#: path or ``MIMIC_FHIR_WAREHOUSE``. The *full* runner deliberately has no such
#: default: there, defaulting to a demo path could let demo data decide a
#: correctness verdict. Here the blast radius is a wrong shape gate, and the
#: convenience of a laptop default is worth it.
DEMO_WAREHOUSE_DEFAULT = "/Users/nau025/warehouses/mimic-iv-demo/delta"

VIEWDEFINITION_GLOB = "ViewDefinition.*.json"
CONCEPT_SQL_NAME = "concept.sql"
CANDIDATE_NAME = "candidate.demo.parquet"
SHAPE_NAME = "shape.demo.json"

# Default manifest location, relative to the repo root.
DEFAULT_MANIFEST = Path("mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json")


class DemoRunError(RuntimeError):
    """A demo run could not be executed (missing artifacts, bad definitions)."""


@dataclass
class DemoRunResult:
    """Everything the run produced, plus the comparator's verdict."""

    concept: str
    attempt_dir: str
    warehouse: str = ""
    view_labels: List[str] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    column_types: Dict[str, str] = field(default_factory=dict)
    candidate_path: str = ""
    shape_path: str = ""
    compared: bool = False
    verdict: Optional[str] = None  # shape_ok | unsure | shape_fail
    schema_diagnostics: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def executed(self) -> bool:
        """True when the concept ran and a candidate artifact was written."""
        return bool(self.candidate_path) and not self.errors

    @property
    def blocked(self) -> bool:
        """True only when the shape gate positively rejected the port.

        This is the ONLY demo outcome that stops a concept. ``unsure`` (0 rows)
        does not block: the demo cohort may legitimately hold nothing, so the
        port proceeds to full-data validation.
        """
        return self.verdict == "shape_fail" or bool(self.errors)

    @property
    def may_proceed_to_full(self) -> bool:
        """True when the port has earned an HPC run.

        Both ``shape_ok`` and ``unsure`` qualify. Note this is *permission to
        spend a full run*, never evidence of correctness -- correctness is
        decided only by the full-data keyed diff.
        """
        return self.executed and self.verdict in ("shape_ok", "unsure")


# ---------------------------------------------------------------------------
# Attempt-directory discovery
# ---------------------------------------------------------------------------


def resolve_attempt_dir(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    attempt: Optional[int] = None,
) -> Path:
    """Resolve the attempt directory to run.

    An explicit *attempt_dir* wins, which is how a controlled or temporary
    run is done without touching durable state.  Otherwise the state
    controller supplies the concept's current attempt directory (or the
    explicitly numbered one).
    """
    if attempt_dir is not None:
        resolved = Path(attempt_dir).expanduser().resolve()
        if not resolved.is_dir():
            raise DemoRunError(f"Attempt directory not found: {resolved}")
        return resolved

    # Imported lazily: a temp-dir run should not require initialised state.
    from mimic_utils.conversion_state import ConversionController

    controller = ConversionController(artifact_root=artifact_root)
    if attempt is not None:
        resolved = controller._attempt_dir(concept, attempt)
        if not resolved.is_dir():
            raise DemoRunError(
                f"Attempt {attempt:04d} for '{concept}' not found: {resolved}"
            )
        return resolved

    found = controller.attempt_dir(concept)
    if found is None:
        raise DemoRunError(
            f"No attempt directory for '{concept}'. Run `mimic_utils start "
            f"{concept}` first, or pass --attempt-dir for a controlled run."
        )
    return found


def discover_view_definitions(attempt: Path) -> List[Dict[str, Any]]:
    """Load every ``ViewDefinition.<label>.json`` in *attempt*, sorted by label.

    The filename label is authoritative for the SQL table name, so a
    ViewDefinition whose ``name`` disagrees with its filename is rejected:
    the concept SQL would silently select from a table that was never
    registered.
    """
    definitions: List[Dict[str, Any]] = []
    for path in sorted(attempt.glob(VIEWDEFINITION_GLOB)):
        label = path.name[len("ViewDefinition.") : -len(".json")]
        if not label:
            raise DemoRunError(f"ViewDefinition file has an empty label: {path.name}")
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DemoRunError(f"{path.name} is not valid JSON: {exc}") from exc
        if body.get("resourceType") != "ViewDefinition":
            raise DemoRunError(
                f"{path.name} has resourceType "
                f"{body.get('resourceType')!r}, expected 'ViewDefinition'"
            )
        declared = body.get("name")
        if declared is not None and declared != label:
            raise DemoRunError(
                f"{path.name}: ViewDefinition name {declared!r} does not match "
                f"the filename label {label!r} — the concept SQL selects from "
                f"the label, so these must agree"
            )
        body["name"] = label
        definitions.append({"label": label, "path": path, "body": body})
    if not definitions:
        raise DemoRunError(
            f"No {VIEWDEFINITION_GLOB} files in {attempt} — nothing to register"
        )
    return definitions


def read_concept_sql(attempt: Path) -> str:
    """Read ``concept.sql`` from *attempt*."""
    path = attempt / CONCEPT_SQL_NAME
    if not path.is_file():
        raise DemoRunError(f"{CONCEPT_SQL_NAME} not found in {attempt}")
    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        raise DemoRunError(f"{path} is empty")
    return sql


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _resolve_demo_warehouse(explicit: Optional[str | Path]) -> Path:
    """Resolve the demo warehouse: explicit -> env -> laptop default."""
    from mimic_utils.embedded_runner import WAREHOUSE_ENV_KEY, resolve_warehouse

    target = explicit or os.environ.get(WAREHOUSE_ENV_KEY) or DEMO_WAREHOUSE_DEFAULT
    return resolve_warehouse(target)


def run_demo(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    manifest_path: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    repo_root: Optional[Path] = None,
    attempt: Optional[int] = None,
    skip_compare: bool = False,
    warehouse: Optional[str | Path] = None,
) -> DemoRunResult:
    """Register, execute and shape-check one concept-port attempt on demo data.

    Runs embedded Pathling in-process over the demo Delta *warehouse* on Spark
    -- the same executor the HPC full run uses -- and writes the result as
    Parquet, so the gate sees the Spark schema rather than a re-inferred one.

    The runner never reads an oracle database.  The target shape comes from
    *manifest_path* (default ``oracle_manifest.full.json``), so no
    ``export-oracle`` step is required for the demo gate.

    A ``shape_ok`` or ``unsure`` verdict earns permission to spend a full-data
    HPC run; neither is evidence of correctness.
    """
    # Imported here: `embedded_runner` imports this module, and pathling and
    # pyspark are optional dependencies the rest of mimic_utils must not need.
    from mimic_utils.embedded_runner import EmbeddedExecutor, EmbeddedRunError, execute_attempt

    resolved_attempt = resolve_attempt_dir(
        concept,
        attempt_dir=attempt_dir,
        artifact_root=artifact_root,
        attempt=attempt,
    )
    result = DemoRunResult(concept=concept, attempt_dir=str(resolved_attempt))

    candidate_path = resolved_attempt / CANDIDATE_NAME
    shape_path = resolved_attempt / SHAPE_NAME
    for path in (candidate_path, shape_path):
        if path.exists():
            result.errors.append(
                f"{path.name} already exists (attempts are write-once); "
                f"start a new attempt instead of re-running this one"
            )
            return result

    try:
        resolved_warehouse = _resolve_demo_warehouse(warehouse)
    except EmbeddedRunError as exc:
        result.errors.append(str(exc))
        return result
    result.warehouse = str(resolved_warehouse)

    # -- 1-3. execute and write Parquet --------------------------------------
    executor: Optional[EmbeddedExecutor] = None
    try:
        frame, executor, labels = execute_attempt(
            resolved_attempt, warehouse_path=resolved_warehouse
        )
        result.view_labels = labels
        result.columns = list(frame.columns)
        result.column_types = dict(frame.dtypes)
        # `mode("error")` rather than overwrite: the write-once rule is
        # enforced by the filesystem, not only by the check above.
        frame.write.mode("error").parquet(str(candidate_path))
        # Counted from the written artifact rather than by re-evaluating the
        # query, which would run the whole concept a second time.
        result.row_count = executor.spark.read.parquet(str(candidate_path)).count()
    except EmbeddedRunError as exc:
        result.errors.append(str(exc))
        return result
    except Exception as exc:  # noqa: BLE001 - a Spark failure is a real shape failure
        result.errors.append(f"embedded execution failed: {exc}")
        return result
    finally:
        if executor is not None:
            executor.close()

    result.candidate_path = str(candidate_path)

    # -- 4. shape gate against the oracle manifest --------------------------
    # No oracle export: the target shape comes from the manifest. Row count is
    # NOT gated here and 0 rows is `unsure`, never `fail` -- see LOOP_CONTRACT.
    if skip_compare:
        return result

    manifest = Path(manifest_path) if manifest_path else _default_manifest(repo_root)
    if not manifest.is_file():
        result.errors.append(
            f"Oracle manifest not found: {manifest} — generate it with "
            f"`mimic_utils.oracle_manifest`"
        )
        return result

    # DuckDB reads the Spark part-files through a glob, exactly as the full
    # runner does; `scan_expression` dispatches on the `.parquet` suffix, which
    # the glob preserves.
    scan_target = str(candidate_path / "*.parquet")
    comparison = compare_shape(concept, manifest, scan_target)
    result.shape_path = str(write_comparison(comparison, shape_path))
    result.compared = True
    result.verdict = comparison.get("verdict")

    schema = comparison.get("schema") or {}
    for field_name in ("missing_columns", "extra_columns"):
        if schema.get(field_name):
            result.schema_diagnostics.append(f"{field_name}: {schema[field_name]}")
    for bad in schema.get("incompatible_types", []):
        result.schema_diagnostics.append(
            f"column {bad['column']!r}: expected {bad['expected']}, got {bad['actual']}"
        )
    return result


def _default_manifest(repo_root: Optional[Path]) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / DEFAULT_MANIFEST


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_demo_report(result: DemoRunResult, *, color: bool = True) -> str:
    """Render *result* as a human-readable report string."""
    lines: List[str] = []
    GREEN = "\033[92m" if color else ""
    RED = "\033[91m" if color else ""
    YELLOW = "\033[93m" if color else ""
    RESET = "\033[0m" if color else ""

    lines.append("=" * 68)
    lines.append(f"  Pathling demo run — concept '{result.concept}'")
    lines.append(f"  Attempt:   {result.attempt_dir}")
    lines.append(f"  Warehouse: {result.warehouse or '(unresolved)'}")
    lines.append("=" * 68)
    lines.append("")

    if result.view_labels:
        lines.append(f"  Views registered: {', '.join(result.view_labels)}")
        lines.append("")

    if result.columns:
        lines.append(f"  Result columns ({len(result.columns)}):")
        for col in result.columns:
            lines.append(f"    {col:<28} {result.column_types.get(col, '?')}")
        # Explicitly labelled: the demo gate does not compare row counts.
        lines.append(f"  Result rows: {result.row_count:,}  (observation — not gated)")
        lines.append("")

    if result.candidate_path:
        lines.append(f"  Candidate:  {result.candidate_path}")
    if result.shape_path:
        lines.append(f"  Shape gate: {result.shape_path}")
    lines.append("")

    if result.compared:
        if result.verdict == "shape_ok":
            lines.append(f"  Shape gate: {GREEN}SHAPE OK{RESET}")
            lines.append("    Proceed to full-data validation. This is NOT")
            lines.append("    evidence of correctness.")
        elif result.verdict == "unsure":
            lines.append(f"  Shape gate: {YELLOW}UNSURE{RESET} (0 rows)")
            lines.append("    The demo cohort may legitimately contain nothing")
            lines.append("    for this concept. Not a failure — proceed to full data.")
        else:
            lines.append(f"  Shape gate: {RED}SHAPE FAIL{RESET}")
        for diag in result.schema_diagnostics:
            lines.append(f"    {RED}x{RESET} {diag}")
    elif result.executed:
        lines.append(f"  {YELLOW}Shape gate not run{RESET} (--skip-compare).")

    for err in result.errors:
        lines.append(f"    {RED}x{RESET} {err}")

    lines.append("")
    lines.append("=" * 68)
    if result.blocked:
        lines.append(f"  {RED}Overall: BLOCKED — fix the port before spending an HPC run{RESET}")
    elif result.may_proceed_to_full:
        lines.append(f"  {GREEN}Overall: MAY PROCEED TO FULL DATA{RESET}")
    else:
        lines.append(f"  {YELLOW}Overall: INCOMPLETE{RESET}")
    lines.append("=" * 68)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def run_demo_cli(args: Optional[List[str]] = None) -> int:
    """Run the demo shape gate.

    Exit codes: 0 shape_ok, 1 shape_fail/error, 2 unsure (0 rows -- neither a
    pass nor a failure; proceed to full data).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute a concept-port attempt over the local demo Delta "
        "warehouse via embedded Pathling on Spark — the same engine the HPC "
        "full run uses — and check its SHAPE against the oracle manifest. Row "
        "count is not gated; 0 rows yields 'unsure'."
    )
    parser.add_argument("concept", help="Concept stem (e.g. age).")
    parser.add_argument(
        "--attempt-dir", default=None,
        help="Attempt directory to run (default: the concept's current attempt).",
    )
    parser.add_argument(
        "--attempt", type=int, default=None,
        help="Explicit attempt number instead of the current one.",
    )
    parser.add_argument(
        "--warehouse", default=None,
        help=f"Demo Delta warehouse (env: MIMIC_FHIR_WAREHOUSE, default "
        f"{DEMO_WAREHOUSE_DEFAULT}).",
    )
    parser.add_argument(
        "--manifest", default=None,
        help="Oracle manifest JSON (default: oracle_manifest.full.json).",
    )
    parser.add_argument("--artifact-root", default=None, help="Artifact root directory.")
    parser.add_argument(
        "--skip-compare", action="store_true",
        help=f"Write {CANDIDATE_NAME} only; do not run the shape gate.",
    )
    parser.add_argument("--no-color", action="store_true")
    opts = parser.parse_args(args)

    result = run_demo(
        concept=opts.concept,
        attempt_dir=opts.attempt_dir,
        attempt=opts.attempt,
        manifest_path=opts.manifest,
        artifact_root=opts.artifact_root,
        skip_compare=opts.skip_compare,
        warehouse=opts.warehouse,
    )
    print(format_demo_report(result, color=not opts.no_color))
    if result.blocked:
        return 1
    if result.verdict == "unsure":
        return 2
    return 0 if result.may_proceed_to_full else 1
