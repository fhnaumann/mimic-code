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
        assert report.active_concepts == []

    def test_active_shown(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        report = ctrl_dag.status_report()
        assert [(a["concept"], a["status"], a["stale"]) for a in report.active_concepts] == [
            ("a", "RUNNING", False)
        ]


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------


class TestStart:
    def test_start_from_pending(self, ctrl_dag):
        ctrl_dag.initialize("a")
        st = ctrl_dag.start("a")
        assert st.status == "RUNNING"
        assert st.attempt == 1

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

    def test_accept_divergence_requires_a_justification(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        with pytest.raises(StateError, match="requires --justification"):
            ctrl_dag.transition("a", "COMPLETED_WITH_DIVERGENCE")

    def test_judge_acceptance_records_its_provenance(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        st = ctrl_dag.transition(
            "a", "COMPLETED_WITH_DIVERGENCE", justification="Encounter.period absent"
        )
        assert st.divergence_decided_by == "judge"

    def test_a_human_can_clear_a_representability_block(self, ctrl_dag):
        """The other thing a human can conclude besides "try again".

        Without this edge, recording a human's acceptance of a blocked concept
        means re-running it to manufacture a VALIDATING_FULL the human has
        already ruled on -- an HPC run spent on a transition table.
        """
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "BLOCKED_REPRESENTATION", error_message="conflict")
        st = ctrl_dag.transition(
            "a", "COMPLETED_WITH_DIVERGENCE",
            justification="fhir_patient.sql:15 synthesises birthDate differently",
            decided_by="human",
        )
        assert st.status == "COMPLETED_WITH_DIVERGENCE"
        assert st.divergence_decided_by == "human"
        assert st.error_message is None

    def test_the_judge_cannot_clear_a_representability_block(self, ctrl_dag):
        """The judge is never called on a blocked concept, so an acceptance
        attributed to it there did not happen."""
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "BLOCKED_REPRESENTATION", error_message="conflict")
        with pytest.raises(StateError, match="only a human can clear"):
            ctrl_dag.transition(
                "a", "COMPLETED_WITH_DIVERGENCE", justification="x" * 40,
            )

    def test_an_accepted_divergence_survives_a_reload(self, ctrl_dag):
        """The justification IS the record. Dropping it on read would leave a
        COMPLETED_WITH_DIVERGENCE with no argument -- the exact state
        `transition` refuses to create."""
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        ctrl_dag.transition(
            "a", "COMPLETED_WITH_DIVERGENCE",
            justification="Patient.birthDate collapses the anchor pair",
            decided_by="human",
        )
        st = ctrl_dag._read_state("a")
        assert st.divergence_justification == (
            "Patient.birthDate collapses the anchor pair"
        )
        assert st.divergence_decided_by == "human"

    def test_status_report_splits_judge_from_human_acceptance(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        ctrl_dag.transition(
            "a", "COMPLETED_WITH_DIVERGENCE",
            justification="x" * 40, decided_by="human",
        )
        report = ctrl_dag.status_report().format(color=False)
        assert "accepted by a human (manual override)" in report
        assert "accepted by the judge" not in report

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


# ---------------------------------------------------------------------------
# reopen — the human-intervention edge out of a finished verdict
# ---------------------------------------------------------------------------


def _finish_with_divergence(ctrl, concept="a", justification="cited reason"):
    ctrl.initialize(concept)
    ctrl.start(concept)
    ctrl.transition(concept, "VALIDATING_DEMO")
    ctrl.transition(concept, "VALIDATING_FULL")
    return ctrl.transition(
        concept, "COMPLETED_WITH_DIVERGENCE",
        justification=justification, counter="semantic",
    )


class TestReopen:
    def test_retry_refuses_a_finished_verdict(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        with pytest.raises(TransitionError, match="reopen"):
            ctrl_dag.start("a")

    def test_reopen_requires_a_reason(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        with pytest.raises(StateError, match="--reason"):
            ctrl_dag.reopen("a", reason="   ")

    def test_reopen_refuses_a_non_human_decider(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        with pytest.raises(StateError, match="--by human"):
            ctrl_dag.reopen("a", reason="bad cast", decided_by="judge")

    def test_reopen_refuses_an_unfinished_concept(self, ctrl_dag):
        ctrl_dag.initialize("a")
        ctrl_dag.start("a")
        with pytest.raises(TransitionError, match="not a\n?\\s*finished result"):
            ctrl_dag.reopen("a", reason="bad cast")

    def test_reopen_starts_a_fresh_attempt(self, ctrl_dag):
        before = _finish_with_divergence(ctrl_dag)
        after = ctrl_dag.reopen("a", reason="TRY_TO_TIMESTAMP is session-tz dependent")
        assert after.status == "RUNNING"
        assert after.attempt == before.attempt + 1
        assert ctrl_dag.attempt_dir("a").name == f"attempt_{after.attempt:04d}"

    def test_reopen_clears_the_superseded_verdict_but_keeps_it(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag, justification="the old argument")
        after = ctrl_dag.reopen("a", reason="bad cast")

        # Cleared: a reopened concept has no verdict and must earn a new one.
        assert after.divergence_justification is None
        assert after.divergence_decided_by is None

        # Kept: the argument that was set aside is still on the record.
        assert after.reopen_count == 1
        entry = after.reopen_history[-1]
        assert entry["superseded_status"] == "COMPLETED_WITH_DIVERGENCE"
        assert entry["superseded_justification"] == "the old argument"
        assert entry["superseded_decided_by"] == "judge"
        assert entry["by"] == "human"
        assert entry["reason"] == "bad cast"

    def test_reopen_stamps_the_metrics_baseline(self, ctrl_dag):
        finished = _finish_with_divergence(ctrl_dag)
        after = ctrl_dag.reopen("a", reason="bad cast")
        assert after.run_baseline == {
            "attempt": finished.attempt,
            "semantic": finished.semantic_counter,
            "engineering": finished.engineering_counter,
            "hpc": finished.hpc_counter,
        }

    def test_baseline_is_zero_when_never_reopened(self, ctrl_dag):
        state = _finish_with_divergence(ctrl_dag)
        assert state.reopen_count == 0
        assert state.run_baseline == {
            "attempt": 0, "semantic": 0, "engineering": 0, "hpc": 0,
        }

    def test_reopen_history_round_trips_through_state_json(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        ctrl_dag.reopen("a", reason="bad cast")
        reloaded = ConversionController(artifact_root=ctrl_dag.artifact_root)
        state = reloaded._read_state("a")  # noqa: SLF001 -- same package
        assert state.reopen_count == 1
        assert state.reopen_history[-1]["reason"] == "bad cast"

    def test_reopened_concept_can_finish_again(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        ctrl_dag.reopen("a", reason="bad cast")
        ctrl_dag.transition("a", "VALIDATING_DEMO")
        ctrl_dag.transition("a", "VALIDATING_FULL")
        final = ctrl_dag.transition("a", "COMPLETED")
        assert final.status == "COMPLETED"
        assert final.reopen_count == 1

    def test_status_report_counts_reopened_separately(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag)
        ctrl_dag.reopen("a", reason="bad cast")
        rows = {c["concept"]: c for c in ctrl_dag.status_report().concepts}
        assert rows["a"]["reopen_count"] == 1
        assert rows["b"]["reopen_count"] == 0
        rendered = ctrl_dag.status_report().format(color=False)
        assert "reopened by a human after a recorded verdict" in rendered

    def test_a_reopened_dependency_still_satisfies_depcheck_only_when_done(self, ctrl_dag):
        """Reopening withdraws the dependency: it is RUNNING, not finished."""
        _finish_with_divergence(ctrl_dag)
        assert ctrl_dag.dependency_ready("b")[0] is True
        ctrl_dag.reopen("a", reason="bad cast")
        ready, missing = ctrl_dag.dependency_ready("b")
        assert ready is False and missing == ["a"]


class TestReopenIsAtomic:
    """A reopen that cannot complete must not leave the verdict half-cleared."""

    def test_refuses_when_the_next_attempt_dir_exists(self, ctrl_dag):
        state = _finish_with_divergence(ctrl_dag)
        # Simulate the collision: a goal is already working in attempt_0002.
        ctrl_dag._attempt_dir("a", state.attempt + 1).mkdir(parents=True)  # noqa: SLF001

        with pytest.raises(StateError, match="already exists"):
            ctrl_dag.reopen("a", reason="bad cast")

        after = ctrl_dag._read_state("a")  # noqa: SLF001 -- same package
        assert after.status == "COMPLETED_WITH_DIVERGENCE"
        assert after.attempt == state.attempt
        assert after.divergence_justification == "cited reason"
        assert after.divergence_decided_by == "judge"
        assert after.reopen_history == []

    def test_refuses_on_a_withdrawn_dependency_without_mutating(self, ctrl_dag):
        _finish_with_divergence(ctrl_dag, concept="a")
        ctrl_dag.initialize("b")
        ctrl_dag.start("b")
        ctrl_dag.transition("b", "VALIDATING_DEMO")
        ctrl_dag.transition("b", "VALIDATING_FULL")
        ctrl_dag.transition("b", "COMPLETED")
        # Withdraw 'a' by reopening it, then try to reopen its dependent.
        ctrl_dag.reopen("a", reason="bad cast")

        with pytest.raises(DependencyError):
            ctrl_dag.reopen("b", reason="same bad cast downstream")

        after = ctrl_dag._read_state("b")  # noqa: SLF001 -- same package
        assert after.status == "COMPLETED"
        assert after.reopen_history == []
