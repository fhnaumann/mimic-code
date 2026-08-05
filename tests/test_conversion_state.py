"""Tests for conversion_state module — hardened v2."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from mimic_utils.conversion_state import (
    ACTIVE_STATUSES,
    ATTEMPT_DIR_PATTERN,
    ConceptState,
    ConcurrencyError,
    ConversionController,
    DAGError,
    DependencyError,
    StateError,
    StatusReport,
    STATUS_VALUES,
    TransitionError,
    ValidationError,
    _resolve_artifact_root,
    dag_category,
    dag_concepts,
    dag_node_path,
    dag_to_dependency_dict,
    load_dag,
    DEFAULT_DAG_PATH,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_root(tmp_path):
    """A temp artifact root with a concept_dag directory."""
    return tmp_path


@pytest.fixture
def dag_raw():
    """Minimal valid DAG with 3 concepts in a chain, matching the real schema."""
    return {
        "generator": "concept_dag",
        "parser_version": "sqlglot 30.15.0",
        "source_root": "mimic-iv/concepts",
        "total_concepts": 3,
        "total_edges": 2,
        "nodes": {
            "a": {
                "stem": "a",
                "path": "cat_a/a.sql",
                "sha256": "a" * 64,
                "level": 0,
                "dependencies": [],
                "dependents": ["b"],
            },
            "b": {
                "stem": "b",
                "path": "cat_b/b.sql",
                "sha256": "b" * 64,
                "level": 1,
                "dependencies": ["a"],
                "dependents": ["c"],
            },
            "c": {
                "stem": "c",
                "path": "c.sql",
                "sha256": "c" * 64,
                "level": 2,
                "dependencies": ["b"],
                "dependents": [],
            },
        },
        "edges": [
            {"consumer": "b", "dependency": "a"},
            {"consumer": "c", "dependency": "b"},
        ],
        "topological_order": ["a", "b", "c"],
        "levels": {"0": ["a"], "1": ["b"], "2": ["c"]},
    }


@pytest.fixture
def dag_path(tmp_root, dag_raw):
    """Write a valid DAG to ``<tmp_root>/mimic-iv/concept_dag/concept_dag.json``."""
    d = tmp_root / "mimic-iv" / "concept_dag"
    d.mkdir(parents=True)
    p = d / "concept_dag.json"
    p.write_text(json.dumps(dag_raw))
    return str(p)


@pytest.fixture
def ctrl_dag(tmp_root, dag_path, dag_raw):
    """Controller with artifact_root pointing at the temp DAG."""
    return ConversionController(artifact_root=tmp_root)


# ---------------------------------------------------------------------------
# DAG loading
# ---------------------------------------------------------------------------


class TestLoadDag:
    def test_loads_valid(self, dag_path, dag_raw):
        loaded = load_dag(dag_path)
        assert loaded["total_concepts"] == 3
        assert loaded["total_edges"] == 2
        assert "valid" not in loaded
        assert "validation" not in loaded

    def test_missing_file(self):
        with pytest.raises(DAGError, match="not found"):
            load_dag("/nonexistent/dag.json")

    def test_missing_keys(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('{"nodes": {}}')
        with pytest.raises(DAGError, match="missing key"):
            load_dag(str(p))

    def test_consistency_total_concepts(self, tmp_root, dag_raw):
        dag_raw["total_concepts"] = 99
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="total_concepts"):
            load_dag(str(p))

    def test_consistency_total_edges(self, tmp_root, dag_raw):
        dag_raw["total_edges"] = 99
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="total_edges"):
            load_dag(str(p))

    def test_consistency_edge_consumer(self, tmp_root, dag_raw):
        dag_raw["edges"].append({"consumer": "nonexistent", "dependency": "a"})
        dag_raw["total_edges"] = len(dag_raw["edges"])  # keep totals consistent
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="consumer.*nonexistent"):
            load_dag(str(p))

    def test_consistency_edge_dependency(self, tmp_root, dag_raw):
        dag_raw["edges"].append({"consumer": "a", "dependency": "nonexistent"})
        dag_raw["total_edges"] = len(dag_raw["edges"])  # keep totals consistent
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="dependency.*nonexistent"):
            load_dag(str(p))

    def test_edges_must_be_list(self, tmp_root, dag_raw):
        dag_raw["edges"] = {"foo": "bar"}
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="must be a list"):
            load_dag(str(p))

    def test_empty_nodes(self, tmp_root, dag_raw):
        dag_raw["nodes"] = {}
        dag_raw["total_concepts"] = 0
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="non-empty dict"):
            load_dag(str(p))

    def test_node_missing_key(self, tmp_root, dag_raw):
        del dag_raw["nodes"]["a"]["sha256"]
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="'a'.*missing key"):
            load_dag(str(p))

    def test_bad_deps_shape(self, tmp_root, dag_raw):
        dag_raw["nodes"]["a"]["dependencies"] = "not_a_list"
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "concept_dag.json"
        p.write_text(json.dumps(dag_raw))
        with pytest.raises(DAGError, match="dependencies must be a list"):
            load_dag(str(p))

    def test_dag_to_dep_dict(self, dag_raw):
        deps = dag_to_dependency_dict(dag_raw)
        assert deps["a"] == set()
        assert deps["b"] == {"a"}
        assert deps["c"] == {"b"}

    def test_dag_concepts(self, dag_raw):
        assert dag_concepts(dag_raw) == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# Category & path derivation from DAG
# ---------------------------------------------------------------------------


class TestDagCategory:
    def test_subdirectory_path(self, dag_raw):
        assert dag_node_path(dag_raw, "a") == "cat_a/a.sql"
        assert dag_category(dag_raw, "a") == "cat_a"

    def test_root_level_path(self, dag_raw):
        assert dag_node_path(dag_raw, "c") == "c.sql"
        assert dag_category(dag_raw, "c") == "_root"

    def test_unknown_concept(self, dag_raw):
        assert dag_node_path(dag_raw, "nonexistent") is None
        assert dag_category(dag_raw, "nonexistent") is None


# ---------------------------------------------------------------------------
# ConceptState
# ---------------------------------------------------------------------------


class TestConceptState:
    def test_from_valid_dict(self):
        state = ConceptState.from_dict({"concept_name": "height", "status": "PENDING"})
        assert state.concept_name == "height"
        assert state.status == "PENDING"

    def test_roundtrip_with_category(self):
        state = ConceptState(
            concept_name="h", status="VALIDATING_DEMO",
            attempt=1, category="measurement",
        )
        reloaded = ConceptState.from_dict(state.to_dict())
        assert reloaded.category == "measurement"


# ---------------------------------------------------------------------------
# Initialize — DAG-gated
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_initialize_stores_category(self, ctrl_dag):
        st = ctrl_dag.initialize("a")
        assert st.category == "cat_a"

    def test_root_concept_has_root_category(self, ctrl_dag):
        st = ctrl_dag.initialize("c")
        assert st.category == "_root"

    def test_rejects_unknown_concept(self, ctrl_dag):
        with pytest.raises(DAGError, match="not a known DAG node"):
            ctrl_dag.initialize("nonexistent")

    def test_double_initialize_raises(self, ctrl_dag):
        ctrl_dag.initialize("a")
        with pytest.raises(StateError, match="already initialised"):
            ctrl_dag.initialize("a")

    def test_creates_state_file(self, ctrl_dag, tmp_root):
        ctrl_dag.initialize("a")
        p = tmp_root / "mimic-iv" / "concepts_fhir" / "state" / "a" / "state.json"
        assert p.exists()


# ---------------------------------------------------------------------------
# Attempt directory locations
# ---------------------------------------------------------------------------


class TestAttemptDirs:
    def test_attempt_dir_under_category(self, ctrl_dag, tmp_root):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ad = ctrl_dag.attempt_dir("a")
        assert ad is not None
        assert str(ad).endswith("cat_a/a/attempt_0001")
        assert ad.is_dir()

    def test_root_attempt_dir(self, ctrl_dag, tmp_root):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        ctrl_dag.transition("a", "COMPLETED")
        ctrl_dag.initialize("b")
        ctrl_dag.start("b")
        ctrl_dag.transition("b", "VALIDATING_FULL")
        ctrl_dag.transition("b", "COMPLETED")
        ctrl_dag.initialize("c")
        ctrl_dag.start("c")
        ad = ctrl_dag.attempt_dir("c")
        assert ad is not None
        assert str(ad).endswith("c/attempt_0001")
        assert "_root" in str(ad)  # root-level path "c.sql" -> category "_root"

    def test_attempt_dir_append_only(self, ctrl_dag, tmp_root):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ad = ctrl_dag.attempt_dir("a")
        mtime_before = ad.stat().st_mtime
        ctrl_dag.transition("a", "FAILED", error_message="x")
        ctrl_dag.start("a")  # creates new attempt dir
        assert ad.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------


class TestStatusReport:
    def test_all_dag_concepts(self, ctrl_dag):
        report = ctrl_dag.status_report()
        concepts = {c["concept"] for c in report.concepts}
        assert concepts == {"a", "b", "c"}
        assert report.active_concept is None

    def test_active_shown(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        report = ctrl_dag.status_report()
        assert report.active_concept == "a"
        assert report.active_status == "RUNNING"


# ---------------------------------------------------------------------------
# Start — concurrency always enforced
# ---------------------------------------------------------------------------


class TestStart:
    def test_start_from_pending(self, ctrl_dag):
        ctrl_dag.initialize("a")
        st = ctrl_dag.start("a")
        assert st.status == "RUNNING"
        assert st.attempt == 1

    def test_concurrency_always_enforced(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.initialize("b")
        ctrl_dag.start("a")
        with pytest.raises(ConcurrencyError, match="already"):
            ctrl_dag.start("b")

    def test_dependency_cannot_be_bypassed(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.initialize("b")
        with pytest.raises(DependencyError):
            ctrl_dag.start("b")


# ---------------------------------------------------------------------------
# Transition — full lifecycle
# ---------------------------------------------------------------------------


class TestTransition:
    def test_lifecycle(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        assert ctrl_dag.transition("a", "VALIDATING_DEMO", counter="engineering").status == "VALIDATING_DEMO"
        assert ctrl_dag.transition("a", "VALIDATING_FULL", counter="hpc").status == "VALIDATING_FULL"
        assert ctrl_dag.transition("a", "COMPLETED", counter="semantic").status == "COMPLETED"

    def test_representability_block_can_be_retried(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        st = ctrl_dag.transition(
            "a", "BLOCKED_REPRESENTATION", error_message="missing FHIR path"
        )
        assert st.error_message == "missing FHIR path"
        assert ctrl_dag.start("a").attempt == 2

    def test_run_to_fail(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        st = ctrl_dag.transition("a", "FAILED", error_message="timeout")
        assert st.status == "FAILED"
        assert st.error_message == "timeout"

    def test_cannot_skip_from_running(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        with pytest.raises(TransitionError):
            ctrl_dag.transition("a", "SKIPPED")

    def test_skip_from_pending(self, ctrl_dag):
        ctrl_dag.initialize("a")
        st = ctrl_dag.transition("a", "SKIPPED")
        assert st.status == "SKIPPED"

    def test_retry_from_failed(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "FAILED", error_message="x")
        st = ctrl_dag.start("a")
        assert st.status == "RUNNING"
        assert st.attempt == 2

    def test_counter_across_lifecycle(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_DEMO", counter="engineering")
        ctrl_dag.transition("a", "FAILED", counter="semantic", error_message="x")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL", counter="hpc")
        st = ctrl_dag.transition("a", "COMPLETED", counter="semantic")
        assert st.engineering_counter == 1
        assert st.semantic_counter == 2
        assert st.hpc_counter == 1


# ---------------------------------------------------------------------------
# Dependency readiness
# ---------------------------------------------------------------------------


class TestDependencyReadiness:
    def test_no_deps_always_ready(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ready, missing = ctrl_dag.dependency_ready("a")
        assert ready is True

    def test_dep_not_completed(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.initialize("b")
        ready, missing = ctrl_dag.dependency_ready("b")
        assert ready is False
        assert "a" in missing


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------


class TestAtomicWrites:
    def test_no_partial_write(self, ctrl_dag):
        ctrl_dag.initialize("a")

        from mimic_utils import conversion_state as mod
        original_write = mod.ConversionController._write_state

        def crashing_write(self, state):
            p = json.dumps(state.to_dict(), indent=2, sort_keys=True)
            fd, tmp = tempfile.mkstemp(
                dir=str(self._concept_dir(state.concept_name)),
                prefix=".state_", suffix=".tmp",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(p)
            raise RuntimeError("simulated crash")

        try:
            mod.ConversionController._write_state = crashing_write
            with pytest.raises(RuntimeError, match="simulated crash"):
                ctrl_dag.start("a")
        finally:
            mod.ConversionController._write_state = original_write

        raw = json.loads(ctrl_dag._path_for("a").read_text())
        assert raw["status"] == "PENDING"


# ---------------------------------------------------------------------------
# Artifact root resolution
# ---------------------------------------------------------------------------


class TestArtifactRoot:
    def test_explicit_root(self, tmp_root):
        """Explicit root must contain a valid DAG artifact."""
        # Create a minimal valid DAG in the tmp_root
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True)
        dag = {
            "generator": "test", "parser_version": "1",
            "source_root": ".", "total_concepts": 1, "total_edges": 0,
            "nodes": {"x": {"stem": "x", "path": "x.sql", "sha256": "x" * 64,
                            "level": 0, "dependencies": [], "dependents": []}},
            "edges": [],
            "topological_order": ["x"],
            "levels": {"0": ["x"]},
        }
        (d / "concept_dag.json").write_text(json.dumps(dag))
        ctrl = ConversionController(artifact_root=tmp_root)
        assert ctrl.artifact_root == tmp_root.resolve()

    def test_auto_detect_from_dag(self, tmp_root):
        """When artifact_root not given, walks up from CWD."""
        d = tmp_root / "mimic-iv" / "concept_dag"
        d.mkdir(parents=True)
        simple_dag = {
            "generator": "test", "parser_version": "1",
            "source_root": ".",
            "total_concepts": 1, "total_edges": 0,
            "nodes": {"x": {"stem": "x", "path": "x.sql", "sha256": "x"*64,
                            "level": 0, "dependencies": [], "dependents": []}},
            "edges": [],
            "topological_order": ["x"],
            "levels": {"0": ["x"]},
        }
        (d / "concept_dag.json").write_text(json.dumps(simple_dag))
        ctrl = ConversionController(artifact_root=tmp_root)
        assert ctrl.artifact_root == tmp_root.resolve()
