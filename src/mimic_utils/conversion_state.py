"""Durable one-concept-at-a-time conversion-loop state / controller.

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

Concurrency constraint: exactly one concept may be in an *active* state
(``RUNNING``, ``VALIDATING_DEMO``, or ``VALIDATING_FULL``) at any time.
Dependencies must always be completed before a concept can start.

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
    "COMPLETED",
]
STATUS_VALUES = frozenset(STATUS_ORDER)
ACTIVE_STATUSES = frozenset({"RUNNING", "VALIDATING_DEMO", "VALIDATING_FULL"})
COUNTER_NAMES = frozenset({"semantic", "engineering", "hpc"})
ATTEMPT_DIR_PATTERN = re.compile(r"^attempt_(\d{4})$")
CACHE_FILENAME = "state.json"

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
    "VALIDATING_FULL": {"COMPLETED", "BLOCKED_REPRESENTATION", "FAILED"},
    "COMPLETED":        set(),
    "BLOCKED_REPRESENTATION": {"RUNNING"},
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


class ConcurrencyError(StateError):
    """Another concept is already in an active state."""


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
    "COMPLETED", "BLOCKED_REPRESENTATION", "FAILED", "SKIPPED",
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
    dependencies: List[str] = field(default_factory=list)
    category: Optional[str] = None

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
            dependencies=deps,
            category=raw.get("category"),
        )


# ---------------------------------------------------------------------------
# Status report model
# ---------------------------------------------------------------------------


@dataclass
class StatusReport:
    """Full status snapshot for all DAG concepts plus the active concept."""
    active_concept: Optional[str]
    active_status: Optional[str]
    concepts: List[Dict[str, Any]]

    def format(self, *, color: bool = True) -> str:
        lines: List[str] = []
        G = "\033[92m" if color else ""
        R = "\033[91m" if color else ""
        Y = "\033[93m" if color else ""
        C = "\033[96m" if color else ""
        B = "\033[0m" if color else ""

        lines.append("Conversion Status Report")
        lines.append("=" * 70)

        if self.active_concept:
            lines.append(f"  Active: {C}{self.active_concept}{B}  ->  {Y}{self.active_status}{B}")
        else:
            lines.append("  Active: (none)")

        lines.append("")
        header = f"  {'Concept':<24} {'Lv':>2}  {'Status':<18} {'Att':>3}  Ready?"
        lines.append(header)
        lines.append(f"  {'-' * 66}")

        for c in self.concepts:
            status = c["status"]
            s = status
            if status == "COMPLETED":
                s = f"{G}COMPLETED{B}"
            elif status in ACTIVE_STATUSES:
                s = f"{Y}{status}{B}"
            elif status == "FAILED":
                s = f"{R}FAILED{B}"

            ready_mark = f"{G}yes{B}" if c["ready"] else f"{R}no{B}"
            lines.append(
                f"  {c['concept']:<24} {c['level']:>2}  {s:<34} {c['attempt']:>3}  {ready_mark}"
            )

        completed = sum(1 for c in self.concepts if c["status"] == "COMPLETED")
        total = len(self.concepts)
        lines.append(f"\n  {completed}/{total} completed")
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

    def _active(self) -> Tuple[Optional[str], Optional[str]]:
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
                return (st.concept_name, st.status)
        return (None, None)

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
        active_name, active_status = self._active()

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
                        if dep_st is None or dep_st.status != "COMPLETED":
                            missing.append(dep)
                    ready = len(missing) == 0

                concepts.append({
                    "concept": stem,
                    "status": st.status if st else "PENDING",
                    "attempt": st.attempt if st else 0,
                    "ready": ready,
                    "missing_deps": sorted(missing),
                    "level": level,
                })

        return StatusReport(
            active_concept=active_name,
            active_status=active_status,
            concepts=concepts,
        )

    def start(self, concept_name: str) -> ConceptState:
        """Transition *concept_name* to ``RUNNING``.

        Guards:
        * Concurrency: no other concept is active (always enforced).
        * Status: concept must be in a startable status.
        * Dependencies: all must be COMPLETED.

        Creates an immutable attempt directory under
        ``concepts/<category>/<concept>/attempt_NNNN/``.
        """
        state = self._read_state(concept_name)
        if state is None:
            raise StateError(f"Concept '{concept_name}' has not been initialised")

        # --- concurrency (always) ---
        active_name, active_status = self._active()
        if active_name is not None and active_name != concept_name:
            raise ConcurrencyError(
                f"Cannot start '{concept_name}': '{active_name}' "
                f"is already {active_status}"
            )

        # --- transition ---
        if state.status not in LEGAL_TRANSITIONS or "RUNNING" not in LEGAL_TRANSITIONS.get(state.status, set()):
            raise TransitionError(
                f"Cannot start '{concept_name}' from status {state.status!r}; "
                f"allowed from: {sorted(s for s, ts in LEGAL_TRANSITIONS.items() if 'RUNNING' in ts)}"
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

    def transition(
        self,
        concept_name: str,
        target: str,
        *,
        error_message: Optional[str] = None,
        counter: Optional[Literal["semantic", "engineering", "hpc"]] = None,
    ) -> ConceptState:
        """Transition *concept_name* to *target*.

        Parameters
        ----------
        target :
            One of ``VALIDATING_DEMO``, ``VALIDATING_FULL``, ``COMPLETED``,
            ``BLOCKED_REPRESENTATION``, ``FAILED``, or ``SKIPPED``.
        error_message :
            Recorded when transitioning to ``FAILED`` or
            ``BLOCKED_REPRESENTATION``.
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

        state.status = target  # type: ignore[assignment]

        if target in ("COMPLETED", "BLOCKED_REPRESENTATION", "FAILED", "SKIPPED"):
            state.completed_at = datetime.now(timezone.utc).isoformat()

        if target in ("FAILED", "BLOCKED_REPRESENTATION"):
            state.error_message = error_message
        else:
            state.error_message = None

        if counter is not None:
            if counter not in COUNTER_NAMES:
                raise StateError(
                    f"Unknown counter {counter!r}; use one of {sorted(COUNTER_NAMES)}"
                )
            setattr(state, f"{counter}_counter", getattr(state, f"{counter}_counter") + 1)

        self._write_state(state)
        return state

    def dependency_ready(self, concept_name: str) -> Tuple[bool, List[str]]:
        missing = self._missing_dependencies(concept_name)
        return len(missing) == 0, sorted(missing)

    def attempt_dir(self, concept_name: str) -> Optional[Path]:
        state = self._read_state(concept_name)
        if state is None or state.attempt == 0:
            return None
        ad = self._attempt_dir(concept_name, state.attempt)
        return ad if ad.exists() else None

    # -- internal -------------------------------------------------------------

    def _missing_dependencies(self, concept_name: str) -> Set[str]:
        deps = self._dag.get(concept_name, set())
        missing: Set[str] = set()
        for dep in deps:
            dep_state = self._read_state(dep)
            if dep_state is None or dep_state.status != "COMPLETED":
                missing.add(dep)
        return missing
