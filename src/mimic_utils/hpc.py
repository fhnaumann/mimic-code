"""Stage, submit, poll and fetch a full-data concept run on Petrichor.

The full-data gate runs on the CSIRO HPC, so something has to move the attempt
there, start the job, wait, and bring the verdict back.  Doing that in agent
prose is how ssh invocations drift between runs; this module is the code the
``hpc-launcher`` and ``hpc-poller`` agents call instead of improvising.

Four steps, in order:

``stage``
    rsync this repo's ``src/mimic_utils/``, the oracle manifest, and the
    completed dependency attempts **into the attempt's own remote directory**,
    along with the attempt itself.  The rendered ``submit.slurm`` and the
    dependency manifest travel with it, so what ran is recoverable from the
    staged attempt afterwards.
``smoke``
    A cheap login-node check: warehouse present, oracle present, the staged
    manifest present, and the imports the job needs actually resolve *on the
    staged copy*.  It exists because a failed job still costs a queue slot, and
    the imports are exactly what breaks when the remote env drifts.  It
    deliberately does **not** create a PathlingContext -- that is a heavy JVM,
    and login nodes are shared.
``submit``
    ``sbatch``, capturing the job id from ``Submitted batch job <id>``.
``poll`` / ``fetch``
    ``squeue`` every 5 minutes, watching the job's log for fatal markers, then
    rsync the two small result artifacts and record final ``sacct`` accounting.
    ``candidate.full.parquet`` is deliberately left on scratch -- it can be
    hundreds of MB and the verdict does not need it.

Polling is normally against cluster etiquette (jobs mail their own status).
The concept-port loop is the sanctioned exception, on the same terms as the
`auto-repro` loop it is modelled on: no more often than every 5 minutes, and
only so the goal loop can advance unattended.

Each poll also touches the concept's ``updated_at``.  A healthy full run makes
no state transition for its entire queue wait plus runtime, so without that
heartbeat every full run would cross the ``VALIDATING_FULL`` staleness
threshold and the signal would be trained away within a day.  Poll only **your**
job id, read from ``hpc_job.json``: under a wave, ``squeue`` shows siblings.

**Nothing is staged to a path two jobs share.**  Concepts are ported in
parallel, one goal per terminal, and the previous shared layout failed twice
over:

1. *Version skew.*  A job launched at 14:00 lazily imports
   ``compare_port_results`` at 14:22 and gets whatever another loop staged at
   14:10 -- a verdict produced by two code versions, recorded nowhere.
2. *``rsync --delete`` into a shared destination.*  Two concurrent launches
   delete and rewrite the module tree a third job is importing.

Staging per attempt also makes ``attempt_NNNN/`` self-describing: the code that
produced the verdict is part of the evidence, not a moving target beside it.

Every command runs through :func:`run_command`, which callers may substitute --
that is what makes this testable without a cluster.

Every step opens its own ssh connection.  ``ControlMaster auto`` /
``ControlPersist 60s`` for this host in ``~/.ssh/config`` collapses them onto
one, which matters more now that several goals launch and poll at once.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from mimic_utils.demo_runner import DemoRunError, resolve_attempt_dir
from mimic_utils.derived_dependencies import (
    DEPENDENCY_MANIFEST_NAME,
    STAGED_DEPENDENCY_DIR,
    dependency_manifest,
    resolve_dependency_plan,
)

# --- Cluster facts ---------------------------------------------------------
# Overridable by env so a different account or scratch layout needs no edit.

HOST = os.environ.get("MIMIC_HPC_HOST", "nau025@petrichor.hpc.csiro.au")
REMOTE_REPO = os.environ.get("MIMIC_HPC_REPO", "/scratch3/nau025/mimic-code")
REMOTE_ENV_PROJECT = os.environ.get(
    "MIMIC_HPC_ENV_PROJECT", "/scratch3/nau025/mimic-on-fhir-delta"
)
REMOTE_WAREHOUSE = os.environ.get(
    "MIMIC_HPC_WAREHOUSE", "/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse"
)
REMOTE_ORACLE = os.environ.get(
    "MIMIC_HPC_ORACLE", "/scratch3/nau025/oracle/mimic4-full.db"
)
ACCOUNT = os.environ.get("MIMIC_HPC_ACCOUNT", "OD-221174")
WALLTIME = os.environ.get("MIMIC_HPC_WALLTIME", "2:00:00")
MAIL_USER = os.environ.get("MIMIC_HPC_MAIL", "Felix.Naumann@csiro.au")
MODULES = ("python/3.12.3", "amazon-corretto/21.0.0.35.1")

MANIFEST_RELPATH = "mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json"
TEMPLATE_RELPATH = "mimic-iv/concepts_fhir/submit_concept_run.slurm"

#: What the manifest is called once staged into the attempt. The job reads it
#: from there, never from a shared copy under REMOTE_REPO.
MANIFEST_NAME = "oracle_manifest.full.json"

SUBMIT_NAME = "submit.slurm"
JOB_RECORD_NAME = "hpc_job.json"
COMPARISON_NAME = "comparison.full.json"
RUN_META_NAME = "run_meta.full.json"
HPC_ACCOUNTING_NAME = "hpc_accounting.json"

#: Sanctioned polling interval. See the module docstring.
POLL_INTERVAL_SECONDS = 300

#: Markers that mean the job is already lost; no point waiting out the wall time.
#
# Every entry must be a string that CANNOT appear in a healthy run's log, because
# a marker hit ends the wait: a bare ``"Error"`` matches ``NoSuchMethodError`` and
# any Spark component that logs the word, so a live, healthy job would be declared
# crashed, its write-once attempt burnt, and one of the ten HPC runs spent while
# the real job was still on its way to a verdict. Prefer a longer, unambiguous
# phrase over a short word; the cost of missing a marker is waiting out the
# walltime, the cost of a false one is a wrong verdict.
FATAL_MARKERS = (
    "Traceback (most recent call last)",
    "java.lang.OutOfMemoryError",
    "slurmstepd: error:",
    "CANCELLED AT",
    "DUE TO TIME LIMIT",
)

_JOB_ID_RE = re.compile(r"Submitted batch job (\d+)")
_JOB_ID_VALUE_RE = re.compile(r"^\d+$")


class HPCError(RuntimeError):
    """An HPC operation failed."""


@dataclass
class CommandResult:
    """The outcome of one local command."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(cmd: Sequence[str], *, timeout: Optional[float] = None) -> CommandResult:
    """Run *cmd* and capture its output. The single seam every step goes through."""
    completed = subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


Runner = Callable[..., CommandResult]


# ---------------------------------------------------------------------------
# Path mapping
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """This repository's root."""
    return Path(__file__).resolve().parents[2]


def remote_attempt_dir(attempt: Path, *, root: Optional[Path] = None) -> str:
    """Map a local attempt directory onto its remote twin.

    The remote tree mirrors the local one under ``REMOTE_REPO``, so the
    relative path is the whole mapping -- no per-concept lookup table to drift.
    """
    local_root = (root or repo_root()).resolve()
    try:
        relative = attempt.resolve().relative_to(local_root)
    except ValueError as exc:
        raise HPCError(
            f"Attempt directory {attempt} is outside the repo ({local_root}); "
            f"cannot derive its remote path"
        ) from exc
    return f"{REMOTE_REPO}/{relative.as_posix()}"


# ---------------------------------------------------------------------------
# Step 1 — render + stage
# ---------------------------------------------------------------------------


def render_submit_script(
    concept: str,
    remote_attempt: str,
    *,
    template_path: Optional[Path] = None,
    walltime: str = WALLTIME,
) -> str:
    """Fill the Slurm template for one concept attempt."""
    template = template_path or (repo_root() / TEMPLATE_RELPATH)
    if not template.is_file():
        raise HPCError(f"Slurm template not found: {template}")
    text = template.read_text(encoding="utf-8")

    substitutions = {
        "JOB_NAME": f"port-{concept}",
        "ACCOUNT": ACCOUNT,
        "WALLTIME": walltime,
        "MAIL": MAIL_USER,
        "LOG_PATH": f"{remote_attempt}/slurm-%j.out",
        "MODULES": " ".join(MODULES),
        # No REPO or MANIFEST placeholder: the job reads its code and its
        # manifest out of ATTEMPT_DIR. A rendered-but-unread variable is how a
        # shared path gets quietly reintroduced, and the leftover-placeholder
        # assertion below would not catch it -- an unused substitution still
        # substitutes cleanly.
        "ENV_PROJECT": REMOTE_ENV_PROJECT,
        "ATTEMPT_DIR": remote_attempt,
        "WAREHOUSE": REMOTE_WAREHOUSE,
        "ORACLE": REMOTE_ORACLE,
        "CONCEPT": concept,
    }
    for key, value in substitutions.items():
        text = text.replace("{{" + key + "}}", value)

    leftover = re.findall(r"\{\{(\w+)\}\}", text)
    if leftover:
        raise HPCError(f"Slurm template has unsubstituted placeholders: {leftover}")
    return text


def stage_attempt(
    concept: str,
    attempt: Path,
    *,
    runner: Runner = run_command,
    root: Optional[Path] = None,
    walltime: str = WALLTIME,
) -> str:
    """Render ``submit.slurm``, then rsync code, dependencies and attempt.

    Everything lands **inside the attempt's own remote directory** -- see the
    module docstring for why a shared destination was two separate bugs under
    parallel goals.  ``--delete`` is still used on the code tree, and is safe
    here precisely because the destination belongs to this attempt alone: it
    removes files a previous staging of *this* attempt left behind, and can
    never touch a tree another job is importing.

    Returns the remote attempt path.  Result artifacts are excluded from the
    attempt rsync so that anything named ``comparison.full.json`` on the remote
    is unambiguously the product of a run there, never a stale laptop copy.
    """
    local_root = (root or repo_root()).resolve()
    remote_attempt = remote_attempt_dir(attempt, root=local_root)
    try:
        dependency_specs = resolve_dependency_plan(
            concept, attempt, artifact_root=local_root
        )
    except Exception as exc:
        raise HPCError(f"could not resolve derived dependencies: {exc}") from exc

    submit_path = attempt / SUBMIT_NAME
    if not submit_path.exists():
        submit_path.write_text(
            render_submit_script(concept, remote_attempt, walltime=walltime),
            encoding="utf-8",
        )

    mkdir = runner(
        [
            "ssh",
            HOST,
            "mkdir -p "
            f"{shlex.quote(remote_attempt + '/src/mimic_utils')} "
            f"{shlex.quote(remote_attempt + '/' + STAGED_DEPENDENCY_DIR)}",
        ]
    )
    if not mkdir.ok:
        raise HPCError(f"remote mkdir failed: {mkdir.stderr.strip() or mkdir.stdout}")

    with tempfile.TemporaryDirectory(prefix="mimic-deps-") as temp_dir:
        manifest_path = Path(temp_dir) / DEPENDENCY_MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(dependency_manifest(concept, dependency_specs), indent=2),
            encoding="utf-8",
        )
        transfers: List[Tuple[List[str], str]] = [
            (
                [
                    "rsync", "-a", "--delete", "--exclude", "__pycache__",
                    f"{local_root / 'src' / 'mimic_utils'}/",
                    f"{HOST}:{remote_attempt}/src/mimic_utils/",
                ],
                "mimic_utils source",
            ),
            (
                [
                    "rsync", "-a",
                    str(local_root / MANIFEST_RELPATH),
                    f"{HOST}:{remote_attempt}/{MANIFEST_NAME}",
                ],
                "oracle manifest",
            ),
            (
                [
                    "rsync", "-a",
                    "--exclude", COMPARISON_NAME,
                    "--exclude", RUN_META_NAME,
                    "--exclude", "candidate.full.parquet",
                    "--exclude", DEPENDENCY_MANIFEST_NAME,
                    "--exclude", STAGED_DEPENDENCY_DIR,
                    "--exclude", "slurm-*.out",
                    f"{attempt}/",
                    f"{HOST}:{remote_attempt}/",
                ],
                "attempt directory",
            ),
            (
                [
                    "rsync", "-a",
                    str(manifest_path),
                    f"{HOST}:{remote_attempt}/{DEPENDENCY_MANIFEST_NAME}",
                ],
                "dependency manifest",
            ),
        ]
        for spec in dependency_specs:
            transfers.append(
                (
                    [
                        "rsync", "-a",
                        "--exclude", "__pycache__",
                        "--exclude", "candidate.demo.parquet",
                        "--exclude", "candidate.full.parquet",
                        "--exclude", COMPARISON_NAME,
                        "--exclude", RUN_META_NAME,
                        "--exclude", "hpc_job.json",
                        "--exclude", "hpc_accounting.json",
                        "--exclude", "submit.slurm",
                        "--exclude", "shape.demo.json",
                        "--exclude", "slurm-*.out",
                        f"{spec.path}/",
                        f"{HOST}:{remote_attempt}/{STAGED_DEPENDENCY_DIR}/{spec.concept}/",
                    ],
                    f"derived dependency {spec.concept}",
                )
            )
        for cmd, what in transfers:
            result = runner(cmd)
            if not result.ok:
                raise HPCError(
                    f"rsync of {what} failed: {result.stderr.strip() or result.stdout}"
                )
    return remote_attempt


# ---------------------------------------------------------------------------
# Step 2 — login-node smoke test
# ---------------------------------------------------------------------------


def smoke_test(
    remote_attempt: str, *, runner: Runner = run_command
) -> CommandResult:
    """Verify the remote env can run the job, without starting a JVM.

    Checks the two data paths, the staged manifest, and the imports the job
    needs -- all against *remote_attempt*, the exact ``PYTHONPATH`` the Slurm
    script exports.  It takes the attempt path rather than assuming a shared
    tree because the job no longer reads one: a smoke test that imported from
    ``REMOTE_REPO/src`` would pass while the job's own copy was missing or
    half-written, which is worse than no smoke test, since a green result is
    what tells the launcher the imports resolve.

    A ``PathlingContext`` is emphatically not created here: it is a heavy JVM
    and the login node is shared.
    """
    script = (
        f"module load {' '.join(MODULES)} && "
        f"test -d {shlex.quote(REMOTE_WAREHOUSE)} && echo 'warehouse OK' && "
        f"test -f {shlex.quote(REMOTE_ORACLE)} && echo 'oracle OK' && "
        f"test -f {shlex.quote(remote_attempt + '/' + MANIFEST_NAME)} && "
        "echo 'staged manifest OK' && "
        f"cd {shlex.quote(REMOTE_ENV_PROJECT)} && "
        f"PYTHONPATH={shlex.quote(remote_attempt + '/src')} "
        "uv run --no-sync python3 -c "
        "'import duckdb, pathling, pyspark; "
        "import mimic_utils.full_runner; print(\"imports OK\")'"
    )
    return runner(["ssh", HOST, f"bash -lc {shlex.quote(script)}"], timeout=600)


# ---------------------------------------------------------------------------
# Step 3 — submit
# ---------------------------------------------------------------------------


def submit(remote_attempt: str, *, runner: Runner = run_command) -> str:
    """``sbatch`` the staged job and return its job id."""
    result = runner(
        [
            "ssh",
            HOST,
            f"cd {shlex.quote(remote_attempt)} && sbatch {SUBMIT_NAME}",
        ]
    )
    if not result.ok:
        raise HPCError(f"sbatch failed: {result.stderr.strip() or result.stdout}")
    match = _JOB_ID_RE.search(result.stdout)
    if not match:
        raise HPCError(f"could not parse a job id from sbatch output: {result.stdout!r}")
    return match.group(1)


def write_job_record(attempt: Path, record: Dict[str, object]) -> Path:
    """Write ``hpc_job.json`` write-once into the attempt directory."""
    path = attempt / JOB_RECORD_NAME
    if path.exists():
        raise HPCError(
            f"{JOB_RECORD_NAME} already exists (attempts are write-once): a "
            f"second full run needs a new attempt"
        )
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_job_record(attempt: Path) -> Dict[str, object]:
    """Read back the job record written at launch."""
    path = attempt / JOB_RECORD_NAME
    if not path.is_file():
        raise HPCError(f"No {JOB_RECORD_NAME} in {attempt} — launch the job first")
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class LaunchResult:
    """What a launch produced."""

    concept: str
    attempt_dir: str
    remote_attempt: str
    job_id: str = ""
    smoke_output: str = ""
    errors: List[str] = field(default_factory=list)

    @property
    def submitted(self) -> bool:
        return bool(self.job_id) and not self.errors


def launch(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    attempt: Optional[int] = None,
    artifact_root: Optional[str | Path] = None,
    runner: Runner = run_command,
    skip_smoke: bool = False,
    walltime: str = WALLTIME,
    root: Optional[Path] = None,
) -> LaunchResult:
    """Stage, smoke-test and submit one attempt. Never submits after a bad smoke test."""
    try:
        resolved = resolve_attempt_dir(
            concept,
            attempt_dir=attempt_dir,
            artifact_root=artifact_root,
            attempt=attempt,
        )
    except DemoRunError as exc:
        raise HPCError(str(exc)) from exc

    if (resolved / JOB_RECORD_NAME).exists():
        raise HPCError(
            f"{concept} attempt {resolved.name} already has a submitted job "
            f"({JOB_RECORD_NAME}); attempts are write-once, so a second full "
            f"run needs a new attempt"
        )

    remote = stage_attempt(
        concept, resolved, runner=runner, walltime=walltime, root=root
    )
    result = LaunchResult(
        concept=concept, attempt_dir=str(resolved), remote_attempt=remote
    )

    if not skip_smoke:
        smoke = smoke_test(remote, runner=runner)
        result.smoke_output = (smoke.stdout + smoke.stderr).strip()
        if not smoke.ok:
            result.errors.append(
                "login-node smoke test failed; not submitting (a failed job "
                f"still costs a queue slot):\n{result.smoke_output}"
            )
            return result

    result.job_id = submit(remote, runner=runner)
    write_job_record(
        resolved,
        {
            "concept": concept,
            "job_id": result.job_id,
            "host": HOST,
            "remote_attempt": remote,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "walltime": walltime,
        },
    )
    return result


# ---------------------------------------------------------------------------
# Step 4 — poll + fetch
# ---------------------------------------------------------------------------


@dataclass
class PollStatus:
    """One observation of a job's state."""

    job_id: str
    in_queue: bool
    fatal_markers: List[str] = field(default_factory=list)
    log_excerpt: str = ""

    @property
    def finished(self) -> bool:
        """True when waiting longer cannot change the outcome."""
        return (not self.in_queue) or bool(self.fatal_markers)


def poll_once(
    job_id: str,
    remote_attempt: str,
    *,
    runner: Runner = run_command,
) -> PollStatus:
    """One ``squeue`` + fatal-marker observation, for *job_id* alone.

    ``squeue -u $USER`` lists every job this account has, which under a wave
    means siblings. Only membership of *job_id* is read out of it, and nothing
    here ever cancels anything -- another concept's job in the queue is not
    this poller's business.
    """
    queue = runner(["ssh", HOST, "squeue -u $USER -h -o %i"])
    if not queue.ok:
        raise HPCError(f"squeue failed: {queue.stderr.strip() or queue.stdout}")
    in_queue = job_id in queue.stdout.split()

    pattern = "|".join(FATAL_MARKERS)
    log_glob = f"{remote_attempt}/slurm-{job_id}.out"
    grep = runner(
        [
            "ssh",
            HOST,
            f"grep -E {shlex.quote(pattern)} {shlex.quote(log_glob)} || true",
        ]
    )
    markers = sorted({m for m in FATAL_MARKERS if m in grep.stdout})
    return PollStatus(
        job_id=job_id,
        in_queue=in_queue,
        fatal_markers=markers,
        log_excerpt=grep.stdout.strip()[:2000],
    )


def fetch_results(
    attempt: Path,
    remote_attempt: str,
    *,
    runner: Runner = run_command,
) -> List[str]:
    """Pull the verdict artifacts back. Returns the local paths fetched.

    ``candidate.full.parquet`` stays on scratch: it can be hundreds of MB and
    the verdict does not depend on having it locally.  Existing local files are
    never overwritten -- ``--ignore-existing`` keeps the write-once rule true
    even if a fetch is repeated.
    """
    fetched: List[str] = []
    for name in (COMPARISON_NAME, RUN_META_NAME):
        result = runner(
            [
                "rsync", "-a", "--ignore-existing",
                f"{HOST}:{remote_attempt}/{name}",
                str(attempt / name),
            ]
        )
        if result.ok:
            fetched.append(str(attempt / name))
    return fetched


def fetch_log(
    attempt: Path,
    remote_attempt: str,
    job_id: str,
    *,
    runner: Runner = run_command,
) -> Optional[str]:
    """Pull the Slurm log back after a crash, for diagnosis."""
    name = f"slurm-{job_id}.out"
    result = runner(
        [
            "rsync", "-a", "--ignore-existing",
            f"{HOST}:{remote_attempt}/{name}",
            str(attempt / name),
        ]
    )
    return str(attempt / name) if result.ok else None


def query_job_accounting(
    job_id: str, *, runner: Runner = run_command
) -> Dict[str, object]:
    """Read the completed allocation's elapsed time from Slurm accounting."""
    if not _JOB_ID_VALUE_RE.fullmatch(job_id):
        raise HPCError(f"Invalid Slurm job id: {job_id!r}")
    result = runner(
        [
            "ssh",
            HOST,
            "sacct -X "
            f"-j {shlex.quote(job_id)} --noheader --parsable2 "
            "--format=JobIDRaw,State,ElapsedRaw,Start,End",
        ]
    )
    if not result.ok:
        raise HPCError(f"sacct failed: {result.stderr.strip() or result.stdout}")

    row: Optional[List[str]] = None
    for line in result.stdout.splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 5 and fields[0] == job_id:
            row = fields[:5]
            break
    if row is None:
        raise HPCError(f"sacct returned no allocation row for job {job_id}")

    _, state, elapsed_raw, started_at, ended_at = row
    try:
        elapsed_seconds = int(elapsed_raw)
    except ValueError as exc:
        raise HPCError(
            f"sacct returned invalid ElapsedRaw for job {job_id}: {elapsed_raw!r}"
        ) from exc
    if elapsed_seconds < 0 or not ended_at or ended_at == "Unknown":
        raise HPCError(f"sacct accounting for job {job_id} is not final")
    return {
        "format_version": "1.0",
        "source": "slurm_sacct",
        "job_id": job_id,
        "state": state,
        "elapsed_seconds": elapsed_seconds,
        "started_at": started_at,
        "ended_at": ended_at,
    }


def record_job_accounting(
    attempt: Path,
    job_id: str,
    *,
    runner: Runner = run_command,
) -> Path:
    """Write final Slurm accounting once after the job leaves the queue."""
    path = attempt / HPC_ACCOUNTING_NAME
    if path.is_file():
        return path
    payload = query_job_accounting(job_id, runner=runner)
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        pass
    return path


@dataclass
class PollResult:
    """The outcome of waiting for a job."""

    concept: str
    job_id: str
    attempt_dir: str
    remote_attempt: str
    outcome: str = "pending"  # complete | crash | timeout | pending
    # match | mismatch | review, read from the fetched comparison. Distinct
    # from `outcome`: a job can complete perfectly and still return `review`.
    verdict: Optional[str] = None
    fetched: List[str] = field(default_factory=list)
    log_path: Optional[str] = None
    accounting_path: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    polls: int = 0
    diagnostics: List[str] = field(default_factory=list)


def _heartbeat(
    concept: str, artifact_root: Optional[str | Path], attempt: Path
) -> None:
    """Stamp ``updated_at`` so a waiting full run is not read as abandoned.

    The root is taken from *attempt* when none was given, rather than from the
    CWD: an attempt directory is always
    ``<root>/mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN``,
    so it names its own root, and a controlled run against a directory outside
    any artifact root then heartbeats nothing instead of stamping a same-named
    concept somewhere else.

    Best-effort by design: a state file that cannot be touched is not a reason
    to abandon a live cluster job, which is the only thing this is in the way of.
    """
    try:
        from mimic_utils.conversion_state import ConversionController

        root = artifact_root if artifact_root is not None else attempt.parents[5]
        ConversionController(artifact_root=root).touch(concept)
    except Exception:  # noqa: BLE001 - a heartbeat must never fail a poll
        pass


def poll_until_done(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    attempt: Optional[int] = None,
    artifact_root: Optional[str | Path] = None,
    job_id: Optional[str] = None,
    runner: Runner = run_command,
    interval: int = POLL_INTERVAL_SECONDS,
    max_polls: int = 288,  # 24 h at the 5-minute interval
    sleeper: Callable[[float], None] = time.sleep,
) -> PollResult:
    """Poll until the job leaves the queue or dies, then fetch the verdict."""
    try:
        resolved = resolve_attempt_dir(
            concept,
            attempt_dir=attempt_dir,
            artifact_root=artifact_root,
            attempt=attempt,
        )
    except DemoRunError as exc:
        raise HPCError(str(exc)) from exc

    record = read_job_record(resolved)
    resolved_job = job_id or str(record.get("job_id", ""))
    remote = str(record.get("remote_attempt", ""))
    if not resolved_job or not remote:
        raise HPCError(f"{JOB_RECORD_NAME} is missing job_id or remote_attempt")

    result = PollResult(
        concept=concept,
        job_id=resolved_job,
        attempt_dir=str(resolved),
        remote_attempt=remote,
    )

    status: Optional[PollStatus] = None
    for poll_index in range(max_polls):
        status = poll_once(resolved_job, remote, runner=runner)
        result.polls = poll_index + 1
        _heartbeat(concept, artifact_root, resolved)
        if status.finished:
            break
        sleeper(interval)
    else:
        result.outcome = "timeout"
        result.diagnostics.append(
            f"job {resolved_job} still queued after {max_polls} polls "
            f"({max_polls * interval / 3600:.1f} h)"
        )
        return result

    # A verdict artifact is the only proof of success. Leaving the queue is
    # not: a job that OOMs also leaves the queue.
    result.fetched = fetch_results(resolved, remote, runner=runner)
    if status is not None and not status.in_queue:
        try:
            accounting_path = record_job_accounting(
                resolved, resolved_job, runner=runner
            )
            result.accounting_path = str(accounting_path)
            accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
            result.elapsed_seconds = int(accounting["elapsed_seconds"])
        except (
            HPCError,
            OSError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            result.diagnostics.append(f"Slurm accounting unavailable: {exc}")
    comparison = resolved / COMPARISON_NAME
    if comparison.is_file():
        payload = json.loads(comparison.read_text(encoding="utf-8"))
        result.verdict = payload.get("verdict")
        result.diagnostics.extend(payload.get("diagnostics") or [])
        result.outcome = "complete"
        return result

    result.outcome = "crash"
    result.log_path = fetch_log(resolved, remote, resolved_job, runner=runner)
    if status is not None and status.fatal_markers:
        result.diagnostics.append(
            f"fatal markers in the job log: {', '.join(status.fatal_markers)}"
        )
    if status is not None and status.in_queue:
        # The wait ended on a marker, not on the job finishing. Say so: the job
        # is still holding a slot, and a retry that ignores it would run two
        # jobs for one concept.
        result.diagnostics.append(
            f"job {resolved_job} is STILL IN THE QUEUE — the wait ended on a log "
            f"marker, not on job exit. Cancel it (scancel {resolved_job}) before "
            f"retrying, or re-poll if the marker was a false positive."
        )
    else:
        result.diagnostics.append(
            "job left the queue without producing comparison.full.json"
        )
    return result


# ---------------------------------------------------------------------------
# CLI entry-points
# ---------------------------------------------------------------------------


def hpc_launch_cli(args: Optional[List[str]] = None) -> int:
    """Stage, smoke-test and submit a full run. Exit 0 when submitted."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Stage a concept-port attempt to Petrichor, smoke-test the "
        "remote environment on the login node, and submit the full-data Slurm "
        "job. The job id is recorded in the attempt's hpc_job.json.",
    )
    parser.add_argument("concept", help="Concept stem (e.g. age).")
    parser.add_argument("--attempt-dir", default=None)
    parser.add_argument("--attempt", type=int, default=None)
    parser.add_argument("--artifact-root", default=None)
    parser.add_argument("--walltime", default=WALLTIME)
    parser.add_argument(
        "--skip-smoke", action="store_true",
        help="Submit without the login-node check (not recommended: a failed "
        "job still costs a queue slot).",
    )
    opts = parser.parse_args(args)

    try:
        result = launch(
            opts.concept,
            attempt_dir=opts.attempt_dir,
            attempt=opts.attempt,
            artifact_root=opts.artifact_root,
            walltime=opts.walltime,
            skip_smoke=opts.skip_smoke,
        )
    except HPCError as exc:
        print(f"launch failed: {exc}")
        return 1

    print(f"concept:        {result.concept}")
    print(f"attempt:        {result.attempt_dir}")
    print(f"remote attempt: {result.remote_attempt}")
    if result.smoke_output:
        print(f"smoke test:\n{result.smoke_output}")
    for err in result.errors:
        print(f"x {err}")
    if result.submitted:
        print(f"submitted:      job {result.job_id}")
        print(f"poll with:      uv run mimic_utils hpc-poll {result.concept}")
        return 0
    return 1


def hpc_poll_cli(args: Optional[List[str]] = None) -> int:
    """Poll a submitted full run and fetch its verdict. Exit 0 on a match."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Poll a submitted full-data job every 5 minutes until it "
        "leaves the queue or dies, then fetch comparison.full.json and "
        "run_meta.full.json and record final Slurm accounting.",
    )
    parser.add_argument("concept", help="Concept stem (e.g. age).")
    parser.add_argument("--attempt-dir", default=None)
    parser.add_argument("--attempt", type=int, default=None)
    parser.add_argument("--artifact-root", default=None)
    parser.add_argument("--job-id", default=None, help="Override the recorded job id.")
    parser.add_argument(
        "--interval", type=int, default=POLL_INTERVAL_SECONDS,
        help="Seconds between polls (default 300; do not go lower).",
    )
    parser.add_argument("--max-polls", type=int, default=288)
    opts = parser.parse_args(args)

    try:
        result = poll_until_done(
            opts.concept,
            attempt_dir=opts.attempt_dir,
            attempt=opts.attempt,
            artifact_root=opts.artifact_root,
            job_id=opts.job_id,
            interval=opts.interval,
            max_polls=opts.max_polls,
        )
    except HPCError as exc:
        print(f"poll failed: {exc}")
        return 1

    print(f"concept:  {result.concept}")
    print(f"job:      {result.job_id}")
    print(f"polls:    {result.polls}")
    print(f"outcome:  {result.outcome}")
    if result.verdict:
        print(f"verdict:  {result.verdict}")
    for path in result.fetched:
        print(f"fetched:  {path}")
    if result.log_path:
        print(f"log:      {result.log_path}")
    if result.accounting_path:
        print(f"accounting: {result.accounting_path}")
    if result.elapsed_seconds is not None:
        print(f"runtime:  {result.elapsed_seconds}s (Slurm elapsed)")
    for diag in result.diagnostics:
        print(f"  - {diag}")

    if result.verdict == "match":
        return 0
    if result.verdict == "review":
        print(
            "\nreview: only divergence a MIMIC-on-FHIR coverage gap could "
            "explain. This is NOT a failed port — spawn the equivalence judge."
        )
        return 2
    return 1
