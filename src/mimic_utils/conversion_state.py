"""Durable per-concept conversion-loop state / controller.

State is serialised as JSON with schema validation.  Writes are atomic
(tmp-file + os.replace).  Attempt directories are **append-only and
immutable** -- once created, the controller never mutates artifacts inside
an attempt directory.  Three separate counters track distinct transition
categories: *semantic* (domain-meaning changes), *engineering* (build /
rewrite changes), and *HPC* (compute / scheduling changes).

Lifecycle states
----------------
::

  PENDING  -- RUNNING -- VALIDATING_DEMO -- VALIDATING_FULL -- COMPLETED
                 active validation states -- BLOCKED_REPRESENTATION
     |          |   |         |    |            |    |
     +-- SKIPPED   +-- FAILED -+    +-- FAILED --+    +-- FAILED

  SKIPPED -- RUNNING              (when dependencies resolve)
  FAILED  -- RUNNING              (retry)

Any number of concepts may be in an *active* state (``RUNNING``,
``VALIDATING_DEMO``, or ``VALIDATING_FULL``) at once: parallelism is composed
outside the loop, as one ``/goal`` per terminal, and the controller no longer
arbitrates it.  The three resources the old single-active rule was implicitly
protecting have their own mechanisms now -- an OS-level lease around the local
Spark JVM, per-attempt HPC staging, and per-concept notes fragments.  See
``mimic-iv/concepts_fhir/LOOP_CONTRACT.md`` -> "Concurrency: waves of parallel
goals".  Dependencies must still be completed before a concept can start.

Paths
-----
State files are stored under::

    {artifact_root}/mimic-iv/concepts_fhir/state/<concept>/state.json

Attempt directories are created under::

    {artifact_root}/mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/

where ``<category>`` is derived from the DAG node's ``path`` field
(e.g. ``medication/antibiotic.sql`` → ``medication``).

The DAG artifact is loaded from ``mimic-iv/concept_dag/concept_dag.json``
relative to *artifact_root*.  Validations performed:
  * ``total_concepts`` matches ``len(nodes)``
  * ``total_edges`` matches ``len(edges)``
  * Every edge consumer / dependency references an existing node
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUS_ORDER: List[str] = [
    "PENDING",
    "SKIPPED",
    "RUNNING",
    "VALIDATING_DEMO",
    "VALIDATING_FULL",
    "BLOCKED_REPRESENTATION",
    "FAILED",
    # A port the judge accepted despite divergence the comparator could not
    # clear on its own. Kept distinct from COMPLETED on purpose: the two are
    # different research results, and a headline of "65/65 completed" that
    # quietly folds them together is not a claim the artifacts support.
    "COMPLETED_WITH_DIVERGENCE",
    "COMPLETED",
]
STATUS_VALUES = frozenset(STATUS_ORDER)
ACTIVE_STATUSES = frozenset({"RUNNING", "VALIDATING_DEMO", "VALIDATING_FULL"})
COUNTER_NAMES = frozenset({"semantic", "engineering", "hpc"})
#: Who may accept a divergence. "judge" is the loop's own equivalence judge;
#: "human" is a manual override recorded against a BLOCKED_REPRESENTATION.
DIVERGENCE_DECIDERS = frozenset({"judge", "human"})
#: Statuses a concept can only leave through `reopen`, never through
#: `start`/`retry`.  Both are finished results with a recorded verdict, so
#: re-entering one is a decision about evidence rather than a scheduling step,
#: and it is made by a human with a reason or not at all.
REOPEN_ONLY_STATUSES = frozenset({"COMPLETED", "COMPLETED_WITH_DIVERGENCE"})
ATTEMPT_DIR_PATTERN = re.compile(r"^attempt_(\d{4})$")
CACHE_FILENAME = "state.json"

#: How long an active status may go without a transition before the concept is
#: reported stale.  This replaces the liveness signal the old single-active
#: invariant was accidentally providing: with several goals in flight a
#: stranded concept blocks its dependents through `depcheck` and says nothing.
#:
#: ``VALIDATING_DEMO`` must stay above the Spark lease's 60-minute wait
#: (``embedded_runner.SPARK_LEASE_TIMEOUT_SECONDS``), or a loop legitimately
#: queued behind the lease reads as dead.  ``VALIDATING_FULL`` can be short --
#: three missed polls -- only because ``hpc-poll`` heartbeats every 300 s.
STALENESS_THRESHOLDS: Dict[str, int] = {
    "RUNNING": 45 * 60,
    "VALIDATING_DEMO": 90 * 60,
    "VALIDATING_FULL": 15 * 60,
}

# Relative to artifact root
DEFAULT_STATE_DIR = "mimic-iv/concepts_fhir/state"
DEFAULT_ATTEMPT_BASE = "mimic-iv/concepts_fhir/concepts"
DEFAULT_DAG_PATH = "mimic-iv/concept_dag/concept_dag.json"

# ---------------------------------------------------------------------------
# Legal-transition table  (from -> {to})
# ---------------------------------------------------------------------------

LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "PENDING":         {"RUNNING", "SKIPPED"},
    "RUNNING":         {"VALIDATING_DEMO", "VALIDATING_FULL", "BLOCKED_REPRESENTATION", "FAILED"},
    "VALIDATING_DEMO": {"VALIDATING_FULL", "BLOCKED_REPRESENTATION", "FAILED"},
    # COMPLETED_WITH_DIVERGENCE is reachable only from here, and only after a
    # judge decision: there is no path to it that skips the full-data run.
    "VALIDATING_FULL": {
        "COMPLETED", "COMPLETED_WITH_DIVERGENCE",
        "BLOCKED_REPRESENTATION", "FAILED",
    },
    # Not sinks, but not ordinarily re-enterable either. The edge exists for one
    # case: a human found a defect in the *shipped SQL* of a finished port -- a
    # cast idiom, a construction that is engine-dependent, anything that changes
    # what the query means. Editing that file in place would leave the attempt's
    # comparison.full.json and its recorded justification describing a query
    # that no longer exists, and nothing in the loop hashes concept.sql, so the
    # drift would be undetectable from the artifacts alone. Re-entry costs a
    # full run and re-earns the verdict instead.
    #
    # `start`/`retry` refuse both (see REOPEN_ONLY_STATUSES): the only way in is
    # `reopen`, which requires a human and a recorded reason.
    "COMPLETED":                 {"RUNNING"},
    "COMPLETED_WITH_DIVERGENCE": {"RUNNING"},
    # BLOCKED_REPRESENTATION is not terminal-terminal: it means "a human must
    # look at this", and the two things a human can conclude are "you are right,
    # try again" (RUNNING) and "this divergence is intrinsic and I accept it"
    # (COMPLETED_WITH_DIVERGENCE). Without the second edge the only way to
    # record a human override is to re-run the concept to manufacture a state
    # the human has already decided -- an HPC run spent to satisfy a transition
    # table. The acceptance still requires a justification, and records that a
    # human and not the judge made it.
    "BLOCKED_REPRESENTATION": {"RUNNING", "COMPLETED_WITH_DIVERGENCE"},
    "FAILED":           {"RUNNING"},
    "SKIPPED":          {"RUNNING"},
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StateError(Exception):
    """Base for all conversion-state issues."""


class ValidationError(StateError):
    """State data failed schema validation."""


class TransitionError(StateError):
    """Illegal state transition attempted."""


class DependencyError(StateError):
    """Required dependencies are not yet COMPLETED."""


class DAGError(StateError):
    """Problem loading or validating the concept DAG artifact."""


# ---------------------------------------------------------------------------
# DAG loader
# ---------------------------------------------------------------------------


def _resolve_artifact_root(explicit: Optional[Union[str, Path]] = None) -> Path:
    """Return *explicit* if given, else walk upward from CWD to find
    ``mimic-iv/concept_dag/concept_dag.json``."""
    if explicit:
        return Path(explicit).resolve()
    candidate = Path.cwd().resolve()
    for _ in range(10):
        if (candidate / DEFAULT_DAG_PATH).exists():
            return candidate
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    return Path.cwd().resolve()


def load_dag(dag_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load and validate the concept DAG.

    Expected schema (generated by ``concept_dag`` generator)::

        {
          "generator": "concept_dag",
          "parser_version": "...",
          "source_root": "mimic-iv/concepts",
          "total_concepts": 65,
          "total_edges": 91,
          "nodes": { stem: {stem, path, sha256, level, dependencies, dependents} },
          "edges": [ {consumer, dependency}, ... ],
          "topological_order": [...],
          "levels": { "0": [...], ... }
        }

    Consistency validations:
      - ``total_concepts == len(nodes)``
      - ``total_edges == len(edges)``
      - Every consumer / dependency in edges references an existing node

    Raises ``DAGError`` on missing / malformed artifact.
    """
    dag_path = Path(dag_path) if dag_path else _resolve_artifact_root() / DEFAULT_DAG_PATH
    if not dag_path.exists():
        raise DAGError(f"DAG artifact not found: {dag_path}")

    try:
        raw: Dict[str, Any] = json.loads(dag_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DAGError(f"DAG artifact is not valid JSON: {exc}") from exc

    # --- shape / key validation ----------------------------------------------
    for key in ("nodes", "edges", "total_concepts", "total_edges"):
        if key not in raw:
            raise DAGError(f"DAG artifact missing key {key!r}")

    nodes = raw["nodes"]
    edges = raw["edges"]

    if not isinstance(nodes, dict) or len(nodes) == 0:
        raise DAGError("DAG 'nodes' must be a non-empty dict")
    if not isinstance(edges, list):
        raise DAGError("DAG 'edges' must be a list")

    # --- consistency ---------------------------------------------------------
    if raw["total_concepts"] != len(nodes):
        raise DAGError(
            f"total_concepts ({raw['total_concepts']}) != len(nodes) ({len(nodes)})"
        )
    if raw["total_edges"] != len(edges):
        raise DAGError(
            f"total_edges ({raw['total_edges']}) != len(edges) ({len(edges)})"
        )

    # Validate node shapes
    for stem, node in nodes.items():
        for key in ("stem", "sha256", "dependencies", "dependents"):
            if key not in node:
                raise DAGError(f"DAG node {stem!r} missing key {key!r}")
        if not isinstance(node.get("dependencies"), list):
            raise DAGError(f"DAG node {stem!r} dependencies must be a list")
        if not isinstance(node.get("dependents"), list):
            raise DAGError(f"DAG node {stem!r} dependents must be a list")

    # Validate edge consumers / dependencies reference real nodes
    for idx, edge in enumerate(edges):
        for role in ("consumer", "dependency"):
            val = edge.get(role)
            if val is None:
                raise DAGError(f"Edge {idx} missing {role!r}")
            if val not in nodes:
                raise DAGError(
                    f"Edge {idx} {role} {val!r} not in nodes"
                )

    return raw


def dag_to_dependency_dict(raw_dag: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Extract ``{concept_stem: {dependency_stems}}`` from a loaded DAG."""
    result: Dict[str, Set[str]] = {}
    for stem, node in raw_dag["nodes"].items():
        result[stem] = set(node.get("dependencies", []))
    return result


def dag_concepts(raw_dag: Dict[str, Any]) -> Set[str]:
    """Return all concept stems known to the DAG."""
    return set(raw_dag["nodes"])


def dag_node_path(raw_dag: Dict[str, Any], concept: str) -> Optional[str]:
    """Return the ``path`` field for *concept*, e.g. ``medication/antibiotic.sql``."""
    node = raw_dag.get("nodes", {}).get(concept)
    return node.get("path") if node else None


def dag_category(raw_dag: Dict[str, Any], concept: str) -> Optional[str]:
    """Derive category from the DAG node path.

    ``medication/antibiotic.sql`` → ``medication``.
    ``vitalsign.sql`` (root-level) → ``_root``.
    """
    p = dag_node_path(raw_dag, concept)
    if p is None:
        return None
    parts = p.replace("\\", "/").split("/")
    if len(parts) == 1:
        return "_root"
    return parts[0]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


StatusType = Literal[
    "PENDING", "RUNNING", "VALIDATING_DEMO", "VALIDATING_FULL",
    "COMPLETED", "COMPLETED_WITH_DIVERGENCE",
    "BLOCKED_REPRESENTATION", "FAILED", "SKIPPED",
]


@dataclass
class ConceptState:
    """Serialisable snapshot of one concept's conversion progress."""
    concept_name: str
    status: StatusType = "PENDING"
    attempt: int = 0
    semantic_counter: int = 0
    engineering_counter: int = 0
    hpc_counter: int = 0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    # Touched by every transition and by each `hpc-poll` iteration. It is the
    # only evidence that a goal running in some other terminal is still alive:
    # nothing else about a parked concept distinguishes "mid-run" from
    # "abandoned three hours ago".
    updated_at: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    category: Optional[str] = None
    # The reasoning for accepting a divergence, kept in its own field rather
    # than in `error_message`: an accepted port did not error, and a results
    # table that reads justifications out of an error field invites exactly the
    # wrong reading.
    divergence_justification: Optional[str] = None
    # Who accepted it: "judge" (the loop's own equivalence judge) or "human" (a
    # manual override of a BLOCKED_REPRESENTATION). Recorded because the two are
    # not the same evidence. A judge-accepted divergence was decided inside the
    # protocol; a human-accepted one was decided outside it, and a thesis that
    # cannot tell the reader which is which is asking to be trusted on the point
    # most worth checking.
    divergence_decided_by: Optional[str] = None
    # One entry per `reopen`, appended never rewritten. Each records who decided,
    # why, the verdict being set aside (status, justification, decider), and the
    # attempt/counter watermarks at that moment.
    #
    # The watermarks are what let `metrics-finalize` scope a run to the work that
    # run actually did. Attempt directories accumulate on disk across reopens and
    # the three counters are cumulative on this state, so without a baseline the
    # second run's artifact would bill it for the first run's attempts, judge
    # invocations and HPC seconds -- and the first run's metrics are already
    # written and correct, so the same work would appear in both.
    reopen_history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def reopen_count(self) -> int:
        return len(self.reopen_history)

    @property
    def run_baseline(self) -> Dict[str, int]:
        """Attempt/counter watermarks the current run started from.

        All zeroes on a concept that was never reopened, which makes
        "this run" and "all time" the same numbers -- as they should be.
        """
        if not self.reopen_history:
            return {"attempt": 0, "semantic": 0, "engineering": 0, "hpc": 0}
        baseline = self.reopen_history[-1].get("baseline") or {}
        return {
            key: int(baseline.get(key, 0) or 0)
            for key in ("attempt", "semantic", "engineering", "hpc")
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ConceptState":
        for key in ("concept_name", "status"):
            if key not in raw:
                raise ValidationError(f"Missing required field: {key}")
        if raw["status"] not in STATUS_VALUES:
            raise ValidationError(
                f"Invalid status {raw['status']!r}; must be one of {sorted(STATUS_VALUES)}"
            )
        if not isinstance(raw.get("concept_name", ""), str) or not raw["concept_name"].strip():
            raise ValidationError("concept_name must be a non-empty string")

        try:
            attempt = int(raw.get("attempt", 0))
            sem = int(raw.get("semantic_counter", 0))
            eng = int(raw.get("engineering_counter", 0))
            hpc = int(raw.get("hpc_counter", 0))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Numeric counter field invalid: {exc}") from exc

        if any(v < 0 for v in (attempt, sem, eng, hpc)):
            raise ValidationError("Counters must be >= 0")

        err = raw.get("error_message")
        if err is not None and not isinstance(err, str):
            raise ValidationError("error_message must be a string or null")

        deps = raw.get("dependencies", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise ValidationError("dependencies must be a list of strings")

        decided_by = raw.get("divergence_decided_by")
        if decided_by is not None and decided_by not in DIVERGENCE_DECIDERS:
            raise ValidationError(
                f"divergence_decided_by must be null or one of "
                f"{sorted(DIVERGENCE_DECIDERS)}; got {decided_by!r}"
            )

        history = raw.get("reopen_history", [])
        if not isinstance(history, list) or not all(isinstance(h, dict) for h in history):
            raise ValidationError("reopen_history must be a list of objects")
        for entry in history:
            baseline = entry.get("baseline")
            if baseline is not None and not isinstance(baseline, dict):
                raise ValidationError("reopen_history[].baseline must be an object or null")

        return cls(
            concept_name=raw["concept_name"].strip(),
            status=raw["status"],  # type: ignore[arg-type]
            attempt=attempt,
            semantic_counter=sem,
            engineering_counter=eng,
            hpc_counter=hpc,
            error_message=err,
            started_at=raw.get("started_at"),
            completed_at=raw.get("completed_at"),
            updated_at=raw.get("updated_at"),
            dependencies=deps,
            category=raw.get("category"),
            # Round-tripped, not dropped. These two fields ARE the record of an
            # accepted divergence; a reload that silently discarded them would
            # leave a COMPLETED_WITH_DIVERGENCE with no argument attached, which
            # is the state `transition` refuses to create in the first place.
            divergence_justification=raw.get("divergence_justification"),
            divergence_decided_by=decided_by,
            reopen_history=history,
        )


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def age_seconds(timestamp: Optional[str]) -> Optional[float]:
    """Seconds since an ISO-8601 *timestamp*, or ``None`` if unusable.

    A state written before ``updated_at`` existed has no age, and is therefore
    never reported stale -- claiming a concept is dead on the strength of a
    field that was never written would be a false alarm on every old state.
    """
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def format_age(seconds: Optional[float]) -> str:
    """``2h50m`` / ``12m`` / ``45s``. Compact because it sits inline in `status`."""
    if seconds is None:
        return "unknown"
    total = int(seconds)
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m"
    return f"{total // 3600}h{(total % 3600) // 60:02d}m"


# ---------------------------------------------------------------------------
# Status report model
# ---------------------------------------------------------------------------


@dataclass
class StatusReport:
    """Full status snapshot for all DAG concepts plus every active one.

    ``active_concepts`` is a list because a wave runs several goals at once.
    Each entry is ``{"concept", "status", "age_seconds", "stale"}``.
    """
    active_concepts: List[Dict[str, Any]]
    concepts: List[Dict[str, Any]]

    @property
    def stale_concepts(self) -> List[Dict[str, Any]]:
        return [a for a in self.active_concepts if a["stale"]]

    def format(self, *, color: bool = True, stale_only: bool = False) -> str:
        lines: List[str] = []
        G = "\033[92m" if color else ""
        R = "\033[91m" if color else ""
        Y = "\033[93m" if color else ""
        C = "\033[96m" if color else ""
        B = "\033[0m" if color else ""

        def active_line(a: Dict[str, Any]) -> str:
            age = f"no transition for {format_age(a['age_seconds'])}"
            mark = f"{R}STALE — {age}{B}" if a["stale"] else age
            return f"  Active: {C}{a['concept']}{B}  ->  {Y}{a['status']}{B} · {mark}"

        if stale_only:
            # Advisory only. Staleness never decides anything on its own; it
            # says where to go and look, because with several goals in flight
            # nothing else reports a loop that stopped.
            lines.append("Stale active concepts")
            lines.append("=" * 70)
            stale = self.stale_concepts
            if not stale:
                lines.append("  (none)")
            for a in stale:
                lines.append(active_line(a))
            return "\n".join(lines)

        lines.append("Conversion Status Report")
        lines.append("=" * 70)

        if self.active_concepts:
            for a in self.active_concepts:
                lines.append(active_line(a))
        else:
            lines.append("  Active: (none)")

        lines.append("")
        header = f"  {'Concept':<24} {'Lv':>2}  {'Status':<26} {'Att':>3}  Ready?"
        lines.append(header)
        lines.append(f"  {'-' * 74}")

        for c in self.concepts:
            status = c["status"]
            s = status
            if status == "COMPLETED":
                s = f"{G}COMPLETED{B}"
            elif status == "COMPLETED_WITH_DIVERGENCE":
                # Yellow, not green. It is a result, not a clean one.
                by = c.get("decided_by")
                s = f"{Y}COMPLETED_WITH_DIVERGENCE{f' ({by})' if by else ''}{B}"
            elif status in ACTIVE_STATUSES:
                s = f"{Y}{status}{B}"
            elif status == "FAILED":
                s = f"{R}FAILED{B}"

            if c.get("reopen_count"):
                s += f" {C}[reopened x{c['reopen_count']}]{B}"

            ready_mark = f"{G}yes{B}" if c["ready"] else f"{R}no{B}"
            lines.append(
                f"  {c['concept']:<24} {c['level']:>2}  {s:<42} {c['attempt']:>3}  {ready_mark}"
            )

        completed = sum(1 for c in self.concepts if c["status"] == "COMPLETED")
        divergent = [
            c for c in self.concepts if c["status"] == "COMPLETED_WITH_DIVERGENCE"
        ]
        by_judge = sum(1 for c in divergent if c.get("decided_by") != "human")
        by_human = sum(1 for c in divergent if c.get("decided_by") == "human")
        total = len(self.concepts)
        # Reported on separate lines, never summed. The distinction between an
        # exact port, one the judge accepted, and one a human accepted over a
        # blocker is the finding, not a formatting detail.
        lines.append(f"\n  {completed}/{total} exact match")
        if by_judge:
            lines.append(f"  {by_judge}/{total} divergence accepted by the judge")
        if by_human:
            lines.append(f"  {by_human}/{total} divergence accepted by a human (manual override)")
        # A fourth line, also never summed into the others. A reopened concept's
        # current verdict is sound -- it was re-earned on full data like any
        # other -- but the reader should know the loop was re-entered by hand
        # rather than converging on its own.
        reopened = sum(1 for c in self.concepts if c.get("reopen_count"))
        if reopened:
            lines.append(f"  {reopened}/{total} reopened by a human after a recorded verdict")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class ConversionController:
    """Manage durable per-concept state for the MIMIC-IV -> FHIR port.

    Parameters
    ----------
    artifact_root : str | Path | None
        Root directory for all artifacts (state, attempts, DAG).  Defaults
        to the repo root resolved from CWD.
    state_dir : str | Path | None
        Override the state directory.  Defaults to
        ``<artifact_root>/mimic-iv/concepts_fhir/state``.
    attempt_base : str | Path | None
        Override the attempt-directory base.  Defaults to
        ``<artifact_root>/mimic-iv/concepts_fhir/concepts``.
    dag_path : str | Path | None
        Override the DAG path.  Defaults to
        ``<artifact_root>/mimic-iv/concept_dag/concept_dag.json``.

    Immutability contract
    ---------------------
    Attempt directories are created by ``start()`` and are **never** modified
    afterward by this controller.  Counters and status are tracked exclusively
    in ``state.json``; the controller never writes inside an attempt directory
    beyond its initial creation.
    """

    def __init__(
        self,
        artifact_root: Optional[Union[str, Path]] = None,
        state_dir: Optional[Union[str, Path]] = None,
        attempt_base: Optional[Union[str, Path]] = None,
        dag_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.artifact_root = _resolve_artifact_root(artifact_root)

        # state directory
        if state_dir is None:
            self.state_dir = self.artifact_root / DEFAULT_STATE_DIR
        else:
            self.state_dir = Path(state_dir)
            if not self.state_dir.is_absolute():
                self.state_dir = self.artifact_root / self.state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # attempt base
        if attempt_base is None:
            self.attempt_base = self.artifact_root / DEFAULT_ATTEMPT_BASE
        else:
            self.attempt_base = Path(attempt_base)
            if not self.attempt_base.is_absolute():
                self.attempt_base = self.artifact_root / self.attempt_base
        self.attempt_base.mkdir(parents=True, exist_ok=True)

        # DAG
        if dag_path is None:
            dag_path = self.artifact_root / DEFAULT_DAG_PATH
        self._dag_raw = load_dag(dag_path)
        self._dag: Dict[str, Set[str]] = dag_to_dependency_dict(self._dag_raw)
        self._dag_concepts = dag_concepts(self._dag_raw)

    # -- properties -----------------------------------------------------------

    @property
    def dag(self) -> Dict[str, Set[str]]:
        return dict(self._dag)

    @property
    def dag_concepts(self) -> Set[str]:
        return set(self._dag_concepts)

    @property
    def dag_raw(self) -> Dict[str, Any]:
        """Read-only view of raw DAG dict (for category lookups, etc.)."""
        return dict(self._dag_raw)

    # -- file helpers ---------------------------------------------------------

    def _concept_dir(self, concept_name: str) -> Path:
        safe = concept_name.strip().replace("/", "_").replace("\\", "_").replace("..", "")
        return self.state_dir / safe

    def _path_for(self, concept_name: str) -> Path:
        return self._concept_dir(concept_name) / CACHE_FILENAME

    def _category_for(self, concept_name: str) -> str:
        cat = dag_category(self._dag_raw, concept_name)
        return cat if cat else "_unknown"

    def _attempt_dir(self, concept_name: str, attempt_number: int) -> Path:
        """Return path like ``.../concepts/<category>/<concept>/attempt_NNNN/``."""
        safe = concept_name.strip().replace("/", "_").replace("\\", "_").replace("..", "")
        cat = self._category_for(concept_name)
        return self.attempt_base / cat / safe / f"attempt_{attempt_number:04d}"

    def _read_state(self, concept_name: str) -> Optional[ConceptState]:
        path = self._path_for(concept_name)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise StateError(f"Cannot parse state for '{concept_name}': {exc}") from exc
        return ConceptState.from_dict(raw)

    def _write_state(self, state: ConceptState) -> None:
        # Stamped here rather than at each call site so no transition can be
        # added later that forgets to, which would make a live concept look
        # abandoned.
        state.updated_at = _now_iso()
        path = self._path_for(state.concept_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, sort_keys=True)
        fd, tmpname = tempfile.mkstemp(
            dir=str(path.parent), prefix=".state_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmpname, str(path))
        except Exception:
            os.unlink(tmpname)
            raise

    def _active(self) -> List[Dict[str, Any]]:
        """Every concept currently in an active status, in name order.

        A list, not a single concept: a wave runs several goals at once, and
        seeing siblings here is the normal case rather than corruption.
        """
        active: List[Dict[str, Any]] = []
        for child in sorted(self.state_dir.iterdir()):
            if not child.is_dir():
                continue
            if not (child / CACHE_FILENAME).exists():
                continue
            try:
                st = self._read_state(child.name)
            except StateError:
                continue
            if st is not None and st.status in ACTIVE_STATUSES:
                active.append(self._liveness_row(st))
        return active

    @staticmethod
    def _liveness_row(state: ConceptState) -> Dict[str, Any]:
        age = age_seconds(state.updated_at)
        threshold = STALENESS_THRESHOLDS.get(state.status)
        return {
            "concept": state.concept_name,
            "status": state.status,
            "age_seconds": age,
            "stale": age is not None and threshold is not None and age > threshold,
        }

    # -- public API -----------------------------------------------------------

    def initialize(self, concept_name: str) -> ConceptState:
        """Create a fresh ``PENDING`` state for *concept_name*.

        Validates DAG membership.  Derives category from DAG node path.
        """
        if concept_name not in self._dag_concepts:
            raise DAGError(
                f"Concept '{concept_name}' is not a known DAG node; "
                f"use one of: {sorted(self._dag_concepts)[:10]}..."
            )
        existing = self._read_state(concept_name)
        if existing is not None:
            raise StateError(
                f"Concept '{concept_name}' already initialised (status={existing.status})"
            )
        deps = sorted(self._dag.get(concept_name, set()))
        category = self._category_for(concept_name)
        state = ConceptState(
            concept_name=concept_name,
            status="PENDING",
            dependencies=list(deps),
            category=category,
        )
        self._write_state(state)
        return state

    def status_report(self) -> StatusReport:
        active = self._active()

        concepts: List[Dict[str, Any]] = []
        nodes_by_level: Dict[int, List[str]] = {}
        for stem, node in self._dag_raw["nodes"].items():
            nodes_by_level.setdefault(node["level"], []).append(stem)

        for level in sorted(nodes_by_level):
            for stem in sorted(nodes_by_level[level]):
                st = self._read_state(stem)
                ready = False
                missing: List[str] = []
                if st is not None:
                    _, missing = self.dependency_ready(stem)
                    ready = len(missing) == 0
                else:
                    deps = self._dag.get(stem, set())
                    for dep in deps:
                        dep_st = self._read_state(dep)
                        if dep_st is None or dep_st.status not in self.SATISFYING_STATUSES:
                            missing.append(dep)
                    ready = len(missing) == 0

                concepts.append({
                    "concept": stem,
                    "status": st.status if st else "PENDING",
                    "attempt": st.attempt if st else 0,
                    "ready": ready,
                    "missing_deps": sorted(missing),
                    "level": level,
                    "decided_by": st.divergence_decided_by if st else None,
                    "reopen_count": st.reopen_count if st else 0,
                })

        return StatusReport(active_concepts=active, concepts=concepts)

    def start(self, concept_name: str, *, _reopening: bool = False) -> ConceptState:
        """Transition *concept_name* to ``RUNNING``.

        Guards:
        * Status: concept must be in a startable status.
        * Dependencies: all must be COMPLETED.

        There is deliberately no concurrency guard: other concepts being active
        is the expected case under a wave of parallel goals.  What the old guard
        was protecting -- the local Spark JVM, the remote module tree, the
        shared notes file -- is protected directly now, each by its own
        mechanism.

        Creates an immutable attempt directory under
        ``concepts/<category>/<concept>/attempt_NNNN/``.
        """
        state = self._read_state(concept_name)
        if state is None:
            raise StateError(f"Concept '{concept_name}' has not been initialised")

        # --- transition ---
        if state.status not in LEGAL_TRANSITIONS or "RUNNING" not in LEGAL_TRANSITIONS.get(state.status, set()):
            raise TransitionError(
                f"Cannot start '{concept_name}' from status {state.status!r}; "
                f"allowed from: {sorted(s for s, ts in LEGAL_TRANSITIONS.items() if 'RUNNING' in ts)}"
            )

        # The edge out of a finished result exists, but not on this route. A
        # `retry` is a scheduling action and takes no argument; setting aside a
        # verdict that is already recorded, cited and counted in the results
        # table is not, so it is routed through `reopen` where a human and a
        # reason are mandatory.
        if state.status in REOPEN_ONLY_STATUSES and not _reopening:
            raise TransitionError(
                f"'{concept_name}' is {state.status} -- a finished result with a "
                f"recorded verdict. Use `mimic_utils reopen {concept_name} "
                f"--by human --reason \"...\"` to set that verdict aside and "
                f"start a new attempt. `retry` will not do it silently."
            )

        # --- deps ---
        missing = self._missing_dependencies(concept_name)
        if missing:
            raise DependencyError(
                f"Cannot start '{concept_name}': unmet dependencies {sorted(missing)}"
            )

        state.attempt += 1
        state.status = "RUNNING"
        state.started_at = datetime.now(timezone.utc).isoformat()
        state.completed_at = None
        state.error_message = None

        # Create the write-once attempt container. The controller never writes
        # artifacts into it; stages add each artifact once while the attempt runs.
        attempt_dir = self._attempt_dir(concept_name, state.attempt)
        attempt_dir.mkdir(parents=True, exist_ok=False)

        self._write_state(state)
        return state

    def reopen(
        self,
        concept_name: str,
        *,
        reason: str,
        decided_by: str = "human",
    ) -> ConceptState:
        """Set aside a finished verdict and start a fresh attempt.

        For the case the loop cannot otherwise express: the port is finished and
        recorded, and a human has found a defect in the SQL it shipped. The
        alternative -- editing ``concept.sql`` inside the finished attempt -- is
        worse than it looks. ``export_mappings`` reads the *current* attempt, so
        the edit silently becomes the exported mapping, while
        ``comparison.full.json``, ``run_meta.full.json`` and the recorded
        justification stay behind describing a query that no longer exists.
        Nothing hashes ``concept.sql``, so no artifact would ever contradict the
        pair. Re-entry costs a full run and makes the new SQL earn its own
        verdict.

        The superseded verdict is copied into ``reopen_history`` and then
        cleared from the live fields, so a reopened concept cannot carry an
        argument for a divergence it may no longer have.

        ``decided_by`` must be ``"human"``. There is no agent-initiated route
        into this: an orchestrator that could reopen its own finished concept
        could retry its way out of any verdict it disliked, and the run cap that
        bounds a concept at ten full runs would bound nothing.
        """
        if decided_by != "human":
            raise StateError(
                "reopen requires --by human. Setting aside a recorded verdict is "
                "a decision taken outside the protocol; an agent that could take "
                "it could retry its way past any judgement, and the ten-run cap "
                "would stop bounding anything."
            )
        if not (reason or "").strip():
            raise StateError(
                "reopen requires --reason: what is wrong with the shipped SQL. "
                "The superseded verdict was recorded with a cited justification, "
                "and replacing it with nothing would make the results table "
                "unreadable at exactly the point a reader would want to check."
            )

        state = self._read_state(concept_name)
        if state is None:
            raise StateError(f"Concept '{concept_name}' has not been initialised")
        if state.status not in REOPEN_ONLY_STATUSES:
            raise TransitionError(
                f"Cannot reopen '{concept_name}': it is {state.status}, not a "
                f"finished result. reopen applies to {sorted(REOPEN_ONLY_STATUSES)}; "
                f"use `retry` or `resume` for anything else."
            )

        # Pre-flight everything `start` will check, BEFORE touching state.
        # `reopen` is two writes -- the history entry, then the transition --
        # and a `start` that raises between them leaves a half-applied reopen:
        # the verdict cleared, the history appended, and the status still
        # terminal. That intermediate state is one `transition` refuses to
        # create (a COMPLETED_WITH_DIVERGENCE with no justification), and a
        # goal already running against the new attempt directory would fail at
        # its next transition with no way back.
        next_dir = self._attempt_dir(concept_name, state.attempt + 1)
        if next_dir.exists():
            raise StateError(
                f"Cannot reopen '{concept_name}': {next_dir.name}/ already exists. "
                f"Either a goal is already running against it -- in which case the "
                f"reopen it belongs to already happened and repeating it is the "
                f"error -- or a previous reopen half-applied and needs repairing. "
                f"Check `status` before retrying; do not delete the directory, it "
                f"may hold a live attempt's work."
            )
        missing = self._missing_dependencies(concept_name)
        if missing:
            raise DependencyError(
                f"Cannot reopen '{concept_name}': unmet dependencies {sorted(missing)}"
            )

        state.reopen_history = list(state.reopen_history) + [{
            "at": datetime.now(timezone.utc).isoformat(),
            "by": decided_by,
            "reason": reason.strip(),
            "superseded_status": state.status,
            "superseded_justification": state.divergence_justification,
            "superseded_decided_by": state.divergence_decided_by,
            # Watermarks. Everything at or below these belongs to a previous run
            # whose metrics artifact is already written.
            "baseline": {
                "attempt": state.attempt,
                "semantic": state.semantic_counter,
                "engineering": state.engineering_counter,
                "hpc": state.hpc_counter,
            },
        }]
        state.divergence_justification = None
        state.divergence_decided_by = None
        self._write_state(state)

        return self.start(concept_name, _reopening=True)

    def transition(
        self,
        concept_name: str,
        target: str,
        *,
        error_message: Optional[str] = None,
        justification: Optional[str] = None,
        decided_by: str = "judge",
        counter: Optional[Literal["semantic", "engineering", "hpc"]] = None,
    ) -> ConceptState:
        """Transition *concept_name* to *target*.

        Parameters
        ----------
        target :
            One of ``VALIDATING_DEMO``, ``VALIDATING_FULL``, ``COMPLETED``,
            ``COMPLETED_WITH_DIVERGENCE``, ``BLOCKED_REPRESENTATION``,
            ``FAILED``, or ``SKIPPED``.
        error_message :
            Recorded when transitioning to ``FAILED`` or
            ``BLOCKED_REPRESENTATION``.
        justification :
            Required for ``COMPLETED_WITH_DIVERGENCE``: the cited reason.
            Accepting a divergence without recording why would leave the
            strongest claim in the thesis resting on an unrecorded argument.
        decided_by :
            ``"judge"`` or ``"human"``.  Only meaningful for
            ``COMPLETED_WITH_DIVERGENCE``.  ``"human"`` is required to clear a
            ``BLOCKED_REPRESENTATION``, because the judge, by construction, is
            not what put it there.
        counter :
            Which of the three counters to increment.
        """
        state = self._read_state(concept_name)
        if state is None:
            raise StateError(f"Concept '{concept_name}' has not been initialised")

        if target not in STATUS_VALUES:
            raise StateError(f"Unknown target status {target!r}")

        allowed = LEGAL_TRANSITIONS.get(state.status, set())
        if target not in allowed:
            raise TransitionError(
                f"Illegal transition {state.status!r} -> {target!r} for '{concept_name}'; "
                f"allowed: {sorted(allowed)}"
            )

        if target == "COMPLETED_WITH_DIVERGENCE":
            if not (justification or "").strip():
                raise StateError(
                    "COMPLETED_WITH_DIVERGENCE requires --justification: the "
                    "cited reason for accepting the divergence, naming the FHIR "
                    "element or path that is missing, or the upstream ETL "
                    "statement that rewrote the value. An accepted divergence "
                    "with no recorded argument is indistinguishable from an "
                    "unchecked one."
                )
            if decided_by not in DIVERGENCE_DECIDERS:
                raise StateError(
                    f"--by must be one of {sorted(DIVERGENCE_DECIDERS)}; "
                    f"got {decided_by!r}"
                )
            # The judge never sees a BLOCKED_REPRESENTATION -- it is either what
            # the judge itself returned or what the loop recorded without
            # convening one. Letting `--by judge` clear it would let the loop
            # launder its own blocker into a judge decision that never happened.
            if state.status == "BLOCKED_REPRESENTATION" and decided_by != "human":
                raise StateError(
                    f"'{concept_name}' is BLOCKED_REPRESENTATION, which only a "
                    f"human can clear: pass --by human. The judge is not called "
                    f"on a blocked concept, so recording its acceptance as the "
                    f"judge's would misattribute the decision."
                )

        state.status = target  # type: ignore[assignment]

        if target in (
            "COMPLETED", "COMPLETED_WITH_DIVERGENCE",
            "BLOCKED_REPRESENTATION", "FAILED", "SKIPPED",
        ):
            state.completed_at = datetime.now(timezone.utc).isoformat()

        if target in ("FAILED", "BLOCKED_REPRESENTATION"):
            state.error_message = error_message
        else:
            state.error_message = None

        if target == "COMPLETED_WITH_DIVERGENCE":
            state.divergence_justification = justification
            state.divergence_decided_by = decided_by

        if counter is not None:
            if counter not in COUNTER_NAMES:
                raise StateError(
                    f"Unknown counter {counter!r}; use one of {sorted(COUNTER_NAMES)}"
                )
            setattr(state, f"{counter}_counter", getattr(state, f"{counter}_counter") + 1)

        self._write_state(state)
        return state

    def touch(self, concept_name: str) -> Optional[ConceptState]:
        """Record that *concept_name* is still being worked on.

        The heartbeat behind the ``VALIDATING_FULL`` staleness threshold: a
        healthy full run makes no transition for its whole queue wait plus
        runtime, so without this every full run would read as stale within
        fifteen minutes and the signal would be trained away.  Returns ``None``
        if the concept has no state yet, because a heartbeat is never a reason
        to create one.
        """
        state = self._read_state(concept_name)
        if state is None:
            return None
        self._write_state(state)
        return state

    def liveness(self, concept_name: str) -> Optional[Dict[str, Any]]:
        """``{"concept", "status", "age_seconds", "stale"}`` if active, else ``None``.

        Advisory. The only callers that act on it are ``resume --apply`` and
        ``retry``, which refuse a concept that still looks live rather than
        stealing an attempt out from under another terminal's goal.
        """
        state = self._read_state(concept_name)
        if state is None or state.status not in ACTIVE_STATUSES:
            return None
        return self._liveness_row(state)

    def dependency_ready(self, concept_name: str) -> Tuple[bool, List[str]]:
        missing = self._missing_dependencies(concept_name)
        return len(missing) == 0, sorted(missing)

    def divergent_dependencies(self, concept_name: str) -> List[str]:
        """Dependencies that only reached ``COMPLETED_WITH_DIVERGENCE``.

        These satisfy the dependency check -- refusing them would stall the DAG
        at the first accepted gap and make the whole permissive policy
        pointless -- but they are not silent.  A concept built on a divergent
        dependency *inherits* that divergence, so its own judge must be told
        which part of the gap it is being asked to assess is not this concept's
        doing.
        """
        return sorted(
            dep
            for dep in self._dag.get(concept_name, set())
            if (st := self._read_state(dep)) is not None
            and st.status == "COMPLETED_WITH_DIVERGENCE"
        )

    def attempt_dir(self, concept_name: str) -> Optional[Path]:
        state = self._read_state(concept_name)
        if state is None or state.attempt == 0:
            return None
        ad = self._attempt_dir(concept_name, state.attempt)
        return ad if ad.exists() else None

    # -- internal -------------------------------------------------------------

    #: Statuses that satisfy a dependency. A judge-accepted divergence counts:
    #: the concept has a defensible port, and refusing to build on it would
    #: halt the DAG at the first coverage gap. See `divergent_dependencies`,
    #: which is how the inherited gap stays visible instead of vanishing.
    SATISFYING_STATUSES = frozenset({"COMPLETED", "COMPLETED_WITH_DIVERGENCE"})

    def _missing_dependencies(self, concept_name: str) -> Set[str]:
        deps = self._dag.get(concept_name, set())
        missing: Set[str] = set()
        for dep in deps:
            dep_state = self._read_state(dep)
            if dep_state is None or dep_state.status not in self.SATISFYING_STATUSES:
                missing.add(dep)
        return missing
