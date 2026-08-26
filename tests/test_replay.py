"""Tests for replaying a finished port against rebuilt data.

Three behaviours are load-bearing:

* The port must come across **byte-identical**. A replay whose SQL drifted is
  not a measurement of the upstream fix, it is a comparison of two queries.
* A fix that ADDS a served element must be refused. That refusal is the only
  thing standing between "the divergence was repaired" and "the divergence was
  laundered": the carried SQL still emits NULL, the column really is 100% NULL,
  so nothing downstream notices.
* ``resume`` must print the replay block instead of the defect block. The defect
  block's instruction is "hand this to the implementer", which on a replay is
  the one thing that must not happen.
"""

from __future__ import annotations

import json

import pytest

from mimic_utils.conversion_state import ConversionController, StateError
from mimic_utils.replay import (
    FIXED_UPSTREAM_DEFECTS,
    PROVENANCE_NAME,
    check_replay,
    read_provenance,
    replay,
)
from mimic_utils.resume import resume_plan


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_raw():
    return {
        "generator": "concept_dag",
        "parser_version": "sqlglot 30.15.0",
        "source_root": "mimic-iv",
        "total_concepts": 2,
        "total_edges": 1,
        "nodes": {
            "age": {
                "stem": "age",
                "path": "demographics/age.sql",
                "sha256": "a" * 64,
                "level": 0,
                "dependencies": [],
                "dependents": ["charlson"],
            },
            "charlson": {
                "stem": "charlson",
                "path": "comorbidity/charlson.sql",
                "sha256": "b" * 64,
                "level": 1,
                "dependencies": ["age"],
                "dependents": [],
            },
        },
        "edges": [{"consumer": "charlson", "dependency": "age"}],
        "topological_order": ["age", "charlson"],
        "levels": {"0": ["age"], "1": ["charlson"]},
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


GOOD_SQL = """
SELECT
    subject_id,
    patient_key,
    hadm_id,
    encounter_key,
    CAST(NULL AS SMALLINT) AS anchor_age
FROM patient
"""


def _finish(
    ctrl,
    concept="age",
    *,
    status="COMPLETED_WITH_DIVERGENCE",
    justification="upstream TIMESTAMPTZ DST shift, fhir_encounter.sql:65",
    sql=GOOD_SQL,
    declarations=None,
):
    """Drive *concept* to a recorded verdict with artifacts on disk."""
    ctrl.initialize(concept)
    ctrl.start(concept)
    attempt = ctrl.attempt_dir(concept)
    (attempt / "concept.sql").write_text(sql, encoding="utf-8")
    (attempt / "ViewDefinition.patient.json").write_text('{"name": "patient"}', encoding="utf-8")
    if declarations:
        (attempt / "unrepresentable.json").write_text(
            json.dumps(declarations), encoding="utf-8"
        )
    # results the replay must NOT carry
    (attempt / "shape.demo.json").write_text('{"verdict": "shape_ok"}', encoding="utf-8")
    (attempt / "comparison.full.json").write_text('{"verdict": "review"}', encoding="utf-8")
    (attempt / "hpc_job.json").write_text('{"job_id": "1234"}', encoding="utf-8")
    ctrl.transition(concept, "VALIDATING_DEMO")
    ctrl.transition(concept, "VALIDATING_FULL")
    if status == "COMPLETED":
        ctrl.transition(concept, "COMPLETED")
    else:
        ctrl.transition(
            concept, status, justification=justification, counter="semantic"
        )
    return attempt


# ---------------------------------------------------------------------------
# carrying the port forward
# ---------------------------------------------------------------------------


def test_replay_carries_the_port_byte_identical(ctrl):
    source = _finish(ctrl)
    source_sql = (source / "concept.sql").read_bytes()

    result = replay("age", reason="upstream #124 fixed", controller=ctrl)

    assert result.attempt == 2
    assert (result.attempt_dir / "concept.sql").read_bytes() == source_sql
    assert (result.attempt_dir / "ViewDefinition.patient.json").is_file()


def test_replay_does_not_carry_earned_results(ctrl):
    _finish(ctrl)
    result = replay("age", reason="upstream #124 fixed", controller=ctrl)

    for earned in ("shape.demo.json", "comparison.full.json", "hpc_job.json"):
        assert not (result.attempt_dir / earned).exists(), earned


def test_replay_records_provenance_with_hashes(ctrl):
    source = _finish(ctrl)
    result = replay("age", reason="warehouse rebuilt 2026-08-24", controller=ctrl)

    prov = read_provenance(result.attempt_dir)
    assert prov["kind"] == "data_rebuild"
    assert prov["source_attempt"] == source.name
    assert prov["reason"] == "warehouse rebuilt 2026-08-24"
    carried = {entry["name"]: entry["sha256"] for entry in prov["carried"]}
    assert "concept.sql" in carried
    assert len(carried["concept.sql"]) == 64
    # the fix being measured is named, so the artifact says what the rerun tested
    assert any(f["id"] == "dst-timestamptz-wall-clock" for f in prov["fixes_measured"])


def test_replay_marks_the_reopen_as_a_data_rebuild(ctrl):
    _finish(ctrl)
    replay("age", reason="upstream #124 fixed", controller=ctrl)

    state = ctrl._read_state("age")
    assert state.reopen_history[-1]["reason"].startswith("[replay:data_rebuild]")
    # the superseded verdict is preserved, exactly as a defect reopen preserves it
    assert state.reopen_history[-1]["superseded_status"] == "COMPLETED_WITH_DIVERGENCE"
    assert state.divergence_justification is None


def test_replay_requires_a_human_and_a_reason(ctrl):
    _finish(ctrl)
    with pytest.raises(StateError, match="requires --reason"):
        replay("age", reason="   ", controller=ctrl)
    with pytest.raises(StateError, match="reopen requires --by human"):
        replay("age", reason="x", decided_by="judge", controller=ctrl)


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------


def test_refuses_when_a_fix_adds_a_served_element(ctrl):
    """The gcs case: the declaration is now false, so the SQL must change."""
    _finish(
        ctrl,
        declarations={
            "gcs_unable": (
                "No FHIR element. Numeric chartevents are served as Quantity while "
                "the source No Response-ETT discriminator is discarded."
            )
        },
    )
    check = check_replay("age", controller=ctrl)
    assert not check.replayable
    assert any("chartevents-value-text-dropped" in r for r in check.refusals)
    assert any("carryover-invalidate" in r for r in check.refusals)
    with pytest.raises(StateError, match="Cannot replay"):
        replay("age", reason="rebuild", controller=ctrl)


def test_refused_replay_leaves_the_verdict_intact(ctrl):
    """A refusal must cost nothing -- no reopen, no attempt, no cleared verdict."""
    _finish(
        ctrl,
        declarations={"gcs_unable": "the No Response-ETT discriminator is discarded"},
    )
    before = ctrl._read_state("age")
    with pytest.raises(StateError):
        replay("age", reason="rebuild", controller=ctrl)
    after = ctrl._read_state("age")

    assert after.status == before.status == "COMPLETED_WITH_DIVERGENCE"
    assert after.attempt == before.attempt
    assert after.divergence_justification == before.divergence_justification
    assert not (ctrl._attempt_dir("age", before.attempt + 1)).exists()


def test_refuses_sql_the_lint_would_reject(ctrl):
    """Catch it before the reopen, not after validate-demo has spent it."""
    _finish(ctrl, sql="SELECT CAST(charttime AS TIMESTAMP) AS charttime FROM obs")
    check = check_replay("age", controller=ctrl)
    assert not check.replayable
    assert any("lint" in r for r in check.refusals)


def test_refuses_a_blocked_concept(ctrl):
    ctrl.initialize("age")
    ctrl.start("age")
    (ctrl.attempt_dir("age") / "concept.sql").write_text(GOOD_SQL, encoding="utf-8")
    ctrl.transition("age", "BLOCKED_REPRESENTATION", error_message="essential loss")

    check = check_replay("age", controller=ctrl)
    assert not check.replayable
    assert any("BLOCKED_REPRESENTATION" in r for r in check.refusals)
    assert any("fhir-prober" in r for r in check.refusals)


def test_refuses_an_unfinished_concept(ctrl):
    ctrl.initialize("age")
    ctrl.start("age")
    check = check_replay("age", controller=ctrl)
    assert not check.replayable
    assert any("not a recorded verdict" in r for r in check.refusals)


def test_refuses_when_a_dependency_is_mid_replay(ctrl):
    """DAG order is forced: a dependency must be terminal before its dependent."""
    _finish(ctrl, "age")
    _finish(ctrl, "charlson", justification="age divergence inherited")
    replay("age", reason="rebuild", controller=ctrl)  # age is now RUNNING

    check = check_replay("charlson", controller=ctrl)
    assert not check.replayable
    assert any("unmet dependencies" in r for r in check.refusals)


def test_refuses_when_there_is_no_sql_to_carry(ctrl):
    ctrl.initialize("age")
    ctrl.start("age")
    ctrl.transition("age", "VALIDATING_DEMO")
    ctrl.transition("age", "VALIDATING_FULL")
    ctrl.transition("age", "COMPLETED")

    check = check_replay("age", controller=ctrl)
    assert not check.replayable
    assert any("no concept.sql" in r for r in check.refusals)


# ---------------------------------------------------------------------------
# warnings
# ---------------------------------------------------------------------------


def test_warns_when_a_declaration_cites_a_repaired_mechanism(ctrl):
    """age's declarations still hold, but their stated mechanism is now wrong."""
    _finish(
        ctrl,
        declarations={
            "anchor_year": (
                "No FHIR element. Patient.birthDate is synthesized from "
                "MIN(transfers.intime) minus anchor_age."
            )
        },
    )
    check = check_replay("age", controller=ctrl)
    assert check.replayable
    assert any("rewrite its stated mechanism" in w for w in check.warnings)


def test_warns_when_part_of_the_divergence_is_still_open_upstream(ctrl):
    _finish(
        ctrl,
        justification=(
            "DST shift on 44 rows (fhir_encounter.sql:65) plus linkorderid, which "
            "no served element carries"
        ),
    )
    check = check_replay("age", controller=ctrl)
    assert check.replayable
    assert any("NOT fixed upstream" in w for w in check.warnings)
    assert any("linkorderid" in w for w in check.warnings)


# ---------------------------------------------------------------------------
# resume integration
# ---------------------------------------------------------------------------


def test_resume_sends_a_replayed_attempt_to_the_demo_gate(ctrl, root):
    _finish(ctrl)
    replay("age", reason="upstream #124 fixed", controller=ctrl)

    plan = resume_plan("age", artifact_root=root)
    assert plan.action == "continue_attempt"
    assert plan.phase.startswith("4")
    assert plan.replay is not None


def test_resume_prints_the_replay_block_not_the_defect_block(ctrl, root):
    _finish(ctrl)
    replay("age", reason="upstream #124 fixed, warehouse rebuilt", controller=ctrl)

    text = resume_plan("age", artifact_root=root).format()
    assert "REPLAY (data rebuild)" in text
    assert "REOPENED" not in text
    assert "implementer:   SKIP" in text
    assert "concept-implementer" in text
    # the carryover lines must not appear: they answer a question about a stage
    # that does not run here
    assert "must re-run" not in text


def test_resume_still_prints_the_defect_block_for_an_ordinary_reopen(ctrl, root):
    _finish(ctrl)
    ctrl.reopen("age", reason="bare TIMESTAMP cast in two places", decided_by="human")

    text = resume_plan("age", artifact_root=root).format()
    assert "REOPENED" in text
    assert "REPLAY (data rebuild)" not in text


# ---------------------------------------------------------------------------
# the registry itself
# ---------------------------------------------------------------------------


def test_every_mapping_invalidating_defect_names_what_is_served_now():
    """A refusal that cannot say where to look instead is not actionable."""
    for defect in FIXED_UPSTREAM_DEFECTS:
        if defect.invalidates_mapping:
            assert defect.now_served, defect.id


def test_registry_ids_are_unique():
    ids = [d.id for d in FIXED_UPSTREAM_DEFECTS]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# the batch driver
# ---------------------------------------------------------------------------


def test_dry_run_writes_no_ledger(ctrl, root, monkeypatch):
    """A dry run that flushed would tell the real wave everything was done."""
    from mimic_utils import replay_batch

    _finish(ctrl)
    monkeypatch.setattr(
        replay_batch.subprocess,
        "run",
        lambda *a, **k: pytest.fail("dry run executed a command"),
    )
    ledger = root / "ledger.json"
    code = replay_batch.run_wave(
        ["age"], reason="rebuild", artifact_root=str(root),
        ledger_path=ledger, dry_run=True,
    )
    assert code == 0
    assert not ledger.exists()
    # and nothing moved
    assert ctrl._read_state("age").status == "COMPLETED_WITH_DIVERGENCE"


def test_a_launched_concept_is_never_launched_twice(ctrl, root, monkeypatch):
    """hpc_job.json is write-once; a second launch abandons a live job."""
    from mimic_utils import replay_batch

    ledger_path = root / "ledger.json"
    ledger = replay_batch.WaveLedger(ledger_path, wave="w", reason="rebuild")
    run = ledger.get("age")
    run.stage = "launch"
    ledger.flush()

    calls = []
    monkeypatch.setattr(
        replay_batch.subprocess,
        "run",
        lambda argv, **k: calls.append(argv) or type("R", (), {"returncode": 0})(),
    )
    replay_batch.run_wave(
        ["age"], reason="rebuild", artifact_root=str(root),
        ledger_path=ledger_path, stages=("replay", "demo", "launch"),
    )
    assert calls == []


def test_a_corrupt_ledger_is_refused_not_reset(root):
    from mimic_utils import replay_batch

    path = root / "ledger.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit, match="unreadable"):
        replay_batch.WaveLedger(path, wave="w", reason="rebuild")


def test_provenance_is_absent_for_a_normal_attempt(ctrl):
    source = _finish(ctrl)
    assert not (source / PROVENANCE_NAME).exists()
    assert read_provenance(source) is None
