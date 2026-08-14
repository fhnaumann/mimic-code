"""Resolve and describe candidate versions of derived dependencies.

The canonical MIMIC-IV build exposes ``mimiciv_derived`` tables in DAG order.
The FHIR runner has no shared derived database, so it materialises the same
dependency boundary as Spark temp views before running a dependent concept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


DEPENDENCY_MANIFEST_NAME = "dependency_manifest.json"
STAGED_DEPENDENCY_DIR = "dependencies"
SATISFYING_STATUSES = frozenset({"COMPLETED", "COMPLETED_WITH_DIVERGENCE"})


class DependencyPlanError(RuntimeError):
    """The derived dependency plan cannot be executed safely."""


@dataclass(frozen=True)
class DependencySpec:
    """One completed dependency attempt and its direct dependencies."""

    concept: str
    attempt: int
    path: Path
    dependencies: Tuple[str, ...] = ()


def infer_artifact_root(attempt: Path) -> Path:
    """Find the repository root containing the concept DAG for *attempt*."""
    resolved = attempt.expanduser().resolve()
    for candidate in resolved.parents:
        if (candidate / "mimic-iv/concept_dag/concept_dag.json").is_file():
            return candidate
    raise DependencyPlanError(
        f"Cannot infer artifact root from attempt directory {resolved}; "
        "the concept DAG is not an ancestor"
    )


def _load_dag(root: Path) -> Dict[str, Any]:
    path = root / "mimic-iv/concept_dag/concept_dag.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyPlanError(f"Cannot read concept DAG {path}: {exc}") from exc


def _state(root: Path, concept: str) -> Dict[str, Any]:
    path = root / "mimic-iv/concepts_fhir/state" / concept / "state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyPlanError(
            f"Cannot read state for derived dependency {concept!r} at {path}: {exc}"
        ) from exc


def _attempt_path(root: Path, dag: Dict[str, Any], concept: str, attempt: int) -> Path:
    node = (dag.get("nodes") or {}).get(concept)
    if not isinstance(node, dict):
        raise DependencyPlanError(f"Derived dependency {concept!r} is not in the DAG")
    source_path = str(node.get("path") or "")
    category = source_path.split("/", 1)[0]
    if not category:
        raise DependencyPlanError(f"DAG node {concept!r} has no source category")
    return (
        root
        / "mimic-iv/concepts_fhir/concepts"
        / category
        / concept
        / f"attempt_{attempt:04d}"
    )


def resolve_dependency_plan(
    concept: str,
    attempt: Path,
    *,
    artifact_root: Optional[str | Path] = None,
) -> List[DependencySpec]:
    """Resolve completed dependency attempts in dependency-first order.

    The current state selects the immutable attempt to execute.  A divergent
    dependency is valid input and remains visible in the dependent's comparison;
    active, failed, missing, or blocked dependencies are refused.
    """
    root = (
        Path(artifact_root).expanduser().resolve()
        if artifact_root
        else infer_artifact_root(attempt)
    )
    dag = _load_dag(root)
    nodes = dag.get("nodes") or {}
    concept = concept.strip().lower()
    if concept not in nodes:
        raise DependencyPlanError(f"Concept {concept!r} is not in the DAG")

    specs: List[DependencySpec] = []
    visited: Set[str] = set()
    visiting: Set[str] = set()

    def visit(consumer: str) -> None:
        if consumer in visiting:
            raise DependencyPlanError(
                f"Cycle encountered while resolving dependencies of {concept!r}: {consumer}"
            )
        visiting.add(consumer)
        node = nodes.get(consumer) or {}
        direct = tuple(
            sorted(str(dep).lower() for dep in node.get("dependencies") or [])
        )
        for dependency in direct:
            if dependency in visited:
                continue
            dependency_state = _state(root, dependency)
            status = dependency_state.get("status")
            if status not in SATISFYING_STATUSES:
                raise DependencyPlanError(
                    f"Derived dependency {dependency!r} is {status!r}; "
                    "only COMPLETED or COMPLETED_WITH_DIVERGENCE can be executed"
                )
            try:
                dependency_attempt = int(dependency_state["attempt"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DependencyPlanError(
                    f"State for derived dependency {dependency!r} has no valid attempt"
                ) from exc
            dependency_path = _attempt_path(root, dag, dependency, dependency_attempt)
            if not dependency_path.is_dir():
                raise DependencyPlanError(
                    f"Attempt directory for derived dependency {dependency!r} does not exist: "
                    f"{dependency_path}"
                )
            visit(dependency)
            specs.append(
                DependencySpec(
                    concept=dependency,
                    attempt=dependency_attempt,
                    path=dependency_path,
                    dependencies=tuple(
                        sorted(
                            str(dep).lower()
                            for dep in (nodes[dependency].get("dependencies") or [])
                        )
                    ),
                )
            )
            visited.add(dependency)
        visiting.remove(consumer)

    visit(concept)
    return specs


def dependency_manifest(
    concept: str, specs: List[DependencySpec], *, staged_root: str = STAGED_DEPENDENCY_DIR
) -> Dict[str, Any]:
    """Build the small manifest carried with an HPC target attempt."""
    return {
        "format_version": 1,
        "concept": concept,
        "dependencies": [
            {
                "concept": spec.concept,
                "attempt": spec.attempt,
                "path": f"{staged_root}/{spec.concept}",
                "dependencies": list(spec.dependencies),
            }
            for spec in specs
        ],
    }


def load_staged_dependency_plan(attempt: Path) -> List[DependencySpec]:
    """Load dependency attempts staged beside a remote target attempt."""
    manifest_path = attempt / DEPENDENCY_MANIFEST_NAME
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DependencyPlanError(
            f"Cannot read staged dependency manifest {manifest_path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise DependencyPlanError(
            f"Staged dependency manifest {manifest_path} must contain an object"
        )

    specs: List[DependencySpec] = []
    seen: Set[str] = set()
    for raw in payload.get("dependencies") or []:
        if not isinstance(raw, dict):
            raise DependencyPlanError(
                f"Invalid dependency entry in staged manifest {manifest_path}"
            )
        concept = str(raw.get("concept") or "").strip().lower()
        relative = Path(str(raw.get("path") or ""))
        if not concept or relative.is_absolute() or ".." in relative.parts:
            raise DependencyPlanError(
                f"Invalid staged dependency path for {concept or '<unknown>'!r}"
            )
        if concept in seen:
            raise DependencyPlanError(f"Duplicate staged dependency {concept!r}")
        path = (attempt / relative).resolve()
        if not path.is_dir() or attempt.resolve() not in path.parents:
            raise DependencyPlanError(
                f"Staged dependency directory is missing or escapes the attempt: {path}"
            )
        dependencies = tuple(
            sorted(str(dep).lower() for dep in raw.get("dependencies") or [])
        )
        if any(dep not in seen for dep in dependencies):
            raise DependencyPlanError(
                f"Staged dependency {concept!r} appears before one of its dependencies"
            )
        try:
            attempt_number = int(raw.get("attempt", 0))
        except (TypeError, ValueError) as exc:
            raise DependencyPlanError(
                f"Invalid attempt number for staged dependency {concept!r}"
            ) from exc
        specs.append(
            DependencySpec(
                concept=concept,
                attempt=attempt_number,
                path=path,
                dependencies=dependencies,
            )
        )
        seen.add(concept)
    return specs
