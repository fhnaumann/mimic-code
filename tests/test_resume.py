"""Tests for carryover reuse and resume planning.

Two behaviours are load-bearing and get the most attention here:

* A concept parked in an active status must be resumable. ``VALIDATING_DEMO``
  has no legal edge to ``RUNNING``, so a rerun that does not first ``fail``
  dies at phase 2 -- that is the bug this module exists to remove.
* Reuse must be revocable. Skipping an analysis stage is only safe while the
  analysis is right, so an invalidated stage has to come back as "must re-run"
  even though its file is still sitting on disk.
"""

from __future__ import annotations

import json

import pytest

from mimic_utils.conversion_state import ConversionController, StateError
from mimic_utils.resume import (
    CARRYOVER_STAGES,
    CarryoverStore,
    resume_plan,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_raw():
    return {
        "generator": "concept_dag",
        "parser_version": "sqlglot 30.15.0",
        "source_root": "mimic-iv/concepts",
        "total_concepts": 1,
        "total_edges": 0,
        "nodes": {
            "age": {
                "stem": "age",
                "path": "demographics/age.sql",
                "sha256": "a" * 64,
                "level": 0,
                "dependencies": [],
                "dependents": [],
            },
        },
        "edges": [],
        "topological_order": ["age"],
        "levels": {"0": ["age"]},
    }


@pytest.fixture
def root(tmp_path, dag_raw):
    d = tmp_path / "mimic-iv" / "concept_dag"
    d.mkdir(parents=True)
    (d / "concept_dag.json").write_text(json.dumps(dag_raw))
    return tmp_path


@pytest.fixture
def ctrl(root):
    return ConversionController(artifact_root=root)


@pytest.fixture
def store(root):
    return CarryoverStore(artifact_root=root)


def _write_stage(store, concept, stage, body="analysis"):
    path = store.stage_path(concept, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _shape(ctrl, concept, verdict):
    """Write a demo verdict into the current attempt directory."""
    ad = ctrl.attempt_dir(concept)
    (ad / "concept.sql").write_text("SELECT 1", encoding="utf-8")
    (ad / "shape.demo.json").write_text(
        json.dumps({"verdict": verdict, "concept": concept}), encoding="utf-8"
    )
    return ad


# ---------------------------------------------------------------------------
# CarryoverStore
# ---------------------------------------------------------------------------


class TestCarryoverStore:
    def test_absent_stage_is_not_fresh(self, store):
        assert store.fresh_stages("age") == []
        assert store.stale_stages("age") == list(CARRYOVER_STAGES)

    def test_present_file_without_ledger_is_reusable(self, store):
        """Analysis written before the ledger existed is still good analysis."""
        _write_stage(store, "age", "fhir-prober")
        assert store.fresh_stages("age") == ["fhir-prober"]

    def test_record_then_reuse(self, store):
        _write_stage(store, "age", "source-analyst")
        store.record("age", "source-analyst", attempt=2)
        (row,) = [r for r in store.status("age") if r.stage == "source-analyst"]
        assert row.fresh is True
        assert row.written_at_attempt == 2

    def test_record_without_file_is_refused(self, store):
        with pytest.raises(StateError, match="does not exist"):
            store.record("age", "source-analyst", attempt=1)

    def test_invalidate_forces_rerun_but_keeps_the_file(self, store):
        path = _write_stage(store, "age", "fhir-prober")
        store.record("age", "fhir-prober", attempt=1)
        store.invalidate("age", "fhir-prober", reason="mapped the wrong resource")

        assert "fhir-prober" in store.stale_stages("age")
        # The wrong analysis stays readable -- it is the evidence for the fix.
        assert path.is_file()
        (row,) = [r for r in store.status("age") if r.stage == "fhir-prober"]
        assert row.present is True
        assert row.invalidated_reason == "mapped the wrong resource"

    def test_rerunning_an_invalidated_stage_makes_it_fresh_again(self, store):
        _write_stage(store, "age", "fhir-prober")
        store.invalidate("age", "fhir-prober", reason="wrong system")
        assert "fhir-prober" in store.stale_stages("age")

        _write_stage(store, "age", "fhir-prober", body="corrected")
        store.record("age", "fhir-prober", attempt=2)
        assert "fhir-prober" in store.fresh_stages("age")

    def test_invalidate_requires_a_reason(self, store):
        _write_stage(store, "age", "fhir-prober")
        with pytest.raises(StateError, match="requires a reason"):
            store.invalidate("age", "fhir-prober", reason="   ")

    def test_unknown_stage_is_refused(self, store):
        with pytest.raises(StateError, match="Unknown carryover stage"):
            store.stage_path("age", "implementer")


# ---------------------------------------------------------------------------
# resume_plan
# ---------------------------------------------------------------------------


class TestResumePlan:
    def test_uninitialised_concept_is_an_error(self, root):
        with pytest.raises(StateError, match="has not been initialised"):
            resume_plan("age", artifact_root=root)

    def test_pending_starts_a_first_attempt(self, root, ctrl):
        ctrl.initialize("age")
        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "start_new_attempt"
        assert plan.transitions == ["start"]

    def test_shape_fail_in_validating_demo_plans_fail_then_start(self, root, ctrl):
        """The exact situation a rerun used to die on."""
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_fail")
        ctrl.transition("age", "VALIDATING_DEMO")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "start_new_attempt"
        assert plan.transitions == ["fail", "start"]
        assert plan.phase.startswith("5")
        assert plan.applied is False

    def test_apply_performs_the_transitions_and_opens_a_new_attempt(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_fail")
        ctrl.transition("age", "VALIDATING_DEMO")

        plan = resume_plan("age", artifact_root=root, apply=True)
        assert plan.applied is True
        assert plan.new_attempt_dir is not None
        assert plan.new_attempt_dir.name == "attempt_0002"

        state = ConversionController(artifact_root=root)._read_state("age")
        assert state.status == "RUNNING"
        assert state.attempt == 2

    def test_shape_ok_resumes_at_the_full_run_without_a_new_attempt(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "continue_attempt"
        assert plan.phase.startswith("6")

    def test_full_run_is_never_spent_as_a_side_effect_of_apply(self, root, ctrl):
        """`resume --apply` may retry a port; it may not authorise an HPC run."""
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")

        resume_plan("age", artifact_root=root, apply=True)
        state = ConversionController(artifact_root=root)._read_state("age")
        assert state.status == "VALIDATING_DEMO"

    def test_running_without_sql_resumes_at_the_implementer(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "continue_attempt"
        assert plan.phase.startswith("3")
        assert plan.transitions == []

    def test_running_with_sql_but_no_verdict_resumes_at_the_demo_gate(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        (ctrl.attempt_dir("age") / "concept.sql").write_text("SELECT 1")
        plan = resume_plan("age", artifact_root=root)
        assert plan.phase.startswith("4")

    def test_full_mismatch_plans_a_new_attempt(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")
        ctrl.transition("age", "VALIDATING_FULL")
        (ctrl.attempt_dir("age") / "comparison.full.json").write_text(
            json.dumps({"verdict": "mismatch"})
        )

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "start_new_attempt"
        assert plan.transitions == ["fail", "start"]

    def test_full_review_resumes_at_the_judge(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")
        ctrl.transition("age", "VALIDATING_FULL")
        (ctrl.attempt_dir("age") / "comparison.full.json").write_text(
            json.dumps({"verdict": "review"})
        )

        plan = resume_plan("age", artifact_root=root)
        assert plan.phase.startswith("7")

    def test_a_contested_review_diagnoses_before_retrying_or_judging(
        self, root, ctrl
    ):
        """A conflict is neither a retry nor a judgement until it is diagnosed.

        Planning `fail`/`start` here would discard a result that may need no
        fix — the conflict can be upstream ETL loss no attempt can undo.
        """
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")
        ctrl.transition("age", "VALIDATING_FULL")
        (ctrl.attempt_dir("age") / "comparison.full.json").write_text(
            json.dumps({"verdict": "review", "divergence": {"tier": "contested"}})
        )

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "continue_attempt"
        assert plan.transitions == []
        assert plan.phase.startswith("5")

    def test_a_blocked_concept_names_both_ways_a_human_can_clear_it(
        self, root, ctrl
    ):
        ctrl.initialize("age")
        ctrl.start("age")
        ctrl.transition("age", "BLOCKED_REPRESENTATION", error_message="conflict")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "blocked"
        assert "accept-divergence --by human" in plan.reason

    def test_validating_full_without_comparison_waits_on_the_job(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")
        ctrl.transition("age", "VALIDATING_FULL")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "continue_attempt"
        assert plan.phase.startswith("6")
        assert plan.transitions == []

    def test_completed_is_left_alone(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        _shape(ctrl, "age", "shape_ok")
        ctrl.transition("age", "VALIDATING_DEMO")
        ctrl.transition("age", "VALIDATING_FULL")
        ctrl.transition("age", "COMPLETED")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "nothing_to_do"
        assert plan.transitions == []

    def test_blocked_representability_needs_a_human(self, root, ctrl):
        ctrl.initialize("age")
        ctrl.start("age")
        ctrl.transition("age", "BLOCKED_REPRESENTATION", error_message="no element")

        plan = resume_plan("age", artifact_root=root)
        assert plan.action == "blocked"
        assert plan.transitions == []

    def test_plan_reports_which_stages_are_reusable(self, root, ctrl, store):
        ctrl.initialize("age")
        _write_stage(store, "age", "source-analyst")
        _write_stage(store, "age", "fhir-prober")
        store.invalidate("age", "fhir-prober", reason="wrong coding system")

        plan = resume_plan("age", artifact_root=root)
        assert plan.fresh_stages == ["source-analyst"]
        assert "fhir-prober" in plan.stale_stages

    def test_unreadable_verdict_is_treated_as_no_verdict(self, root, ctrl):
        """A truncated artifact must not crash the planner."""
        ctrl.initialize("age")
        ctrl.start("age")
        ad = ctrl.attempt_dir("age")
        (ad / "concept.sql").write_text("SELECT 1")
        (ad / "shape.demo.json").write_text("{not json")

        plan = resume_plan("age", artifact_root=root)
        assert plan.phase.startswith("4")
