"""Tests for driving a wave of orchestrator sessions k at a time.

Four behaviours are load-bearing, and each of them is a way to spend a run you
cannot get back:

* **The dependency gate must test the ledger, not the disk.** Every concept in a
  replay wave is ``COMPLETED`` when the wave starts -- that is what makes it
  replayable -- so a disk check passes for all of them at t=0 and a dependent
  opens before its dependency has been reopened at all. It is then measured
  against the dependency's old candidate, which is the verdict the wave exists
  to invalidate.
* **A resumed pool continues a session, never restarts it.** A restart re-enters
  the loop with the concept already open and spends a second HPC run.
* **The state file decides the outcome, not the marker.** On an accepted
  divergence the orchestrator emits ``[goal:complete-with-divergence]`` and then
  a ``[goal:complete]`` pair, so believing the last marker records an exact match
  that never happened.
* **A dry run must leave no ledger.** A persisted dry run tells the real wave
  everything is done, consuming the wave it was meant to preview.
"""

from __future__ import annotations

import json

import pytest

from mimic_utils import goal_pool
from mimic_utils.__main__ import _GOAL_MODES
from mimic_utils.conversion_state import ConversionController
from mimic_utils.goal_pool import (
    MODES,
    GoalLedger,
    GoalRun,
    _child_env,
    _marker_in,
    _text_in,
    run_pool,
    wave_concepts,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_raw():
    """``age`` -> ``charlson``: the smallest graph with a real dependency."""
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


def _complete(ctrl, concept):
    """Drive *concept* to COMPLETED so it is replayable."""
    ctrl.initialize(concept)
    ctrl.start(concept)
    ctrl.transition(concept, "VALIDATING_DEMO")
    ctrl.transition(concept, "VALIDATING_FULL")
    ctrl.transition(concept, "COMPLETED")


@pytest.fixture
def fake_pool(monkeypatch, root):
    """Replace both subprocess boundaries with recorders.

    ``_open_concept`` and ``_run_turn`` are the only places this module shells
    out, so stubbing them exercises the scheduler, the ledger, and the outcome
    classification without an OpenCode process or a real reopen.
    """

    class Fake:
        def __init__(self):
            self.opened = []
            self.turns = []
            #: concept -> list of assistant texts, one per turn
            self.replies = {}
            #: concept -> controller status reported once its session stops
            self.final_status = {}

        def open_concept(self, run, **kwargs):
            self.opened.append(run.concept)
            run.phase = "opened"
            return True

        def run_turn(self, argv, **kwargs):
            self.turns.append(list(argv))
            concept = argv[-1]
            # A continuation turn carries the nudge, not the stem; recover the
            # concept from the session id the first turn returned.
            if concept not in self.replies:
                concept = self._concept_for_session(argv)
            queue = self.replies.get(concept) or [""]
            text = queue.pop(0) if queue else ""
            return goal_pool._TurnResult(
                session_id=f"ses_{concept}", text=text, returncode=0
            )

        def _concept_for_session(self, argv):
            if "--session" in argv:
                return argv[argv.index("--session") + 1].removeprefix("ses_")
            return argv[-1]

        def status_of(self, concept, artifact_root):
            return self.final_status.get(concept)

    fake = Fake()
    monkeypatch.setattr(goal_pool, "_open_concept", fake.open_concept)
    monkeypatch.setattr(goal_pool, "_run_turn", fake.run_turn)
    monkeypatch.setattr(goal_pool, "_status_of", fake.status_of)
    return fake


# ---------------------------------------------------------------------------
# markers
# ---------------------------------------------------------------------------


def test_a_divergence_marker_is_not_read_as_an_exact_match():
    # The orchestrator emits both, in this order, on a judge `accept`.
    text = "[goal:complete-with-divergence] ... [goal:evidence] ... [goal:complete]"
    assert _marker_in(text) == "complete_with_divergence"


def test_blocked_outranks_a_completion_marker():
    assert _marker_in("[goal:complete] ... actually [goal:blocked]") == "blocked"


def test_a_bare_completion_marker_is_a_completion():
    assert _marker_in("all done [goal:complete]") == "complete"
    assert _marker_in("still working") is None


def test_a_marker_inside_a_tool_call_is_not_a_claim():
    """Only assistant text counts.

    An agent grepping for the marker, or writing it into a doc, is not the agent
    saying it finished -- and a driver that stopped on that would leave the
    concept mid-loop while reporting it complete.
    """
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "tool_use",
                    "part": {
                        "tool": "bash",
                        "state": {"input": {"command": "grep -r '[goal:complete]' ."}},
                    },
                }
            ),
            json.dumps({"type": "text", "part": {"text": "searching now"}}),
        ]
    )
    assert _marker_in(_text_in(stdout)) is None


# ---------------------------------------------------------------------------
# worker isolation
# ---------------------------------------------------------------------------


def test_each_worker_gets_its_own_goal_state_path(tmp_path, monkeypatch):
    """The goal plugin's lease is exclusive; a shared path fails workers 2..k."""
    monkeypatch.delenv("MIMIC_SPARK_LOCK", raising=False)
    a = _child_env(tmp_path / "a" / "state.json", "/tmp/spark.lock")
    b = _child_env(tmp_path / "b" / "state.json", "/tmp/spark.lock")
    assert a["OPENCODE_GOAL_STATE_PATH"] != b["OPENCODE_GOAL_STATE_PATH"]
    assert a["MIMIC_SPARK_LOCK"] == "/tmp/spark.lock"


def test_an_existing_spark_lock_is_not_overridden(tmp_path, monkeypatch):
    # A human already running a /goal in another terminal set this; taking a
    # different lock path would let two local Sparks run at once.
    monkeypatch.setenv("MIMIC_SPARK_LOCK", "/existing/lock")
    env = _child_env(tmp_path / "state.json", "/tmp/other.lock")
    assert env["MIMIC_SPARK_LOCK"] == "/existing/lock"


# ---------------------------------------------------------------------------
# the dependency gate
# ---------------------------------------------------------------------------


def test_a_dependent_waits_for_its_dependency_to_finish(root, ctrl, fake_pool):
    """Not for the dependency to *look* complete on disk -- it already does."""
    _complete(ctrl, "age")
    _complete(ctrl, "charlson")
    assert ctrl._read_state("age").status == "COMPLETED"  # the trap

    fake_pool.replies = {
        "age": ["[goal:complete]"],
        "charlson": ["[goal:complete]"],
    }
    fake_pool.final_status = {"age": "COMPLETED", "charlson": "COMPLETED"}

    # Two slots, so without a gate both would start together.
    code = run_pool(
        ["age", "charlson"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=2,
        run_dir=root / "run",
    )
    assert code == 0
    assert fake_pool.opened == ["age", "charlson"]


def test_a_dependent_is_skipped_when_its_dependency_fails(root, ctrl, fake_pool):
    _complete(ctrl, "age")
    _complete(ctrl, "charlson")

    fake_pool.replies = {"age": ["[goal:blocked]"], "charlson": ["[goal:complete]"]}
    fake_pool.final_status = {"age": "BLOCKED_REPRESENTATION"}

    code = run_pool(
        ["age", "charlson"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=2,
        run_dir=root / "run",
    )
    assert code == 1
    assert fake_pool.opened == ["age"]  # charlson never opened

    ledger = json.loads((root / "run" / "ledger.json").read_text())
    charlson = next(r for r in ledger["runs"] if r["concept"] == "charlson")
    assert charlson["phase"] == "skipped"
    assert charlson["outcome"] == "dependency"
    assert "age" in charlson["error"]


def test_a_dependency_outside_the_run_set_is_left_to_the_controller(
    root, ctrl, fake_pool
):
    """``replay`` and ``start`` already refuse an unsatisfied dependency.

    Re-checking it here would stall a wave whose dependency legitimately landed
    in an earlier wave.
    """
    _complete(ctrl, "age")
    _complete(ctrl, "charlson")
    fake_pool.replies = {"charlson": ["[goal:complete]"]}
    fake_pool.final_status = {"charlson": "COMPLETED"}

    code = run_pool(
        ["charlson"],  # age is a dependency but is not in the run set
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        run_dir=root / "run",
    )
    assert code == 0
    assert fake_pool.opened == ["charlson"]


# ---------------------------------------------------------------------------
# outcome classification
# ---------------------------------------------------------------------------


def test_the_state_file_decides_the_outcome_not_the_marker(root, ctrl, fake_pool):
    _complete(ctrl, "age")
    fake_pool.replies = {"age": ["[goal:complete-with-divergence] ... [goal:complete]"]}
    fake_pool.final_status = {"age": "COMPLETED_WITH_DIVERGENCE"}

    code = run_pool(
        ["age"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        run_dir=root / "run",
    )
    assert code == 0

    ledger = json.loads((root / "run" / "ledger.json").read_text())
    age = next(r for r in ledger["runs"] if r["concept"] == "age")
    assert age["outcome"] == "complete_with_divergence"
    assert age["status"] == "COMPLETED_WITH_DIVERGENCE"


def test_a_marker_with_no_terminal_status_is_reported_unfinished(root, ctrl, fake_pool):
    """The agent said it finished and the controller disagrees.

    That is exactly the case a driver must not paper over: it means the loop
    stopped somewhere the state machine still considers open.
    """
    _complete(ctrl, "age")
    fake_pool.replies = {"age": ["[goal:complete]"]}
    fake_pool.final_status = {"age": "VALIDATING_FULL"}

    code = run_pool(
        ["age"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        run_dir=root / "run",
    )
    assert code == 1


def test_a_session_with_no_marker_is_continued_then_given_up_on(root, ctrl, fake_pool):
    _complete(ctrl, "age")
    fake_pool.replies = {"age": ["working", "still working", "and again"]}
    fake_pool.final_status = {"age": "VALIDATING_FULL"}

    code = run_pool(
        ["age"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        run_dir=root / "run",
        max_turns=3,
    )
    assert code == 1

    ledger = json.loads((root / "run" / "ledger.json").read_text())
    age = next(r for r in ledger["runs"] if r["concept"] == "age")
    assert age["turns"] == 3
    assert age["outcome"] == "exhausted"

    # The first turn is the bare stem -- exactly what `/goal <concept>` sends.
    assert fake_pool.turns[0][-1] == "age"
    # Every later turn continues that same session rather than starting a new one.
    for argv in fake_pool.turns[1:]:
        assert "--session" in argv
        assert "--agent" not in argv


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


def test_a_resumed_pool_leaves_a_finished_concept_alone(root, ctrl, fake_pool):
    _complete(ctrl, "age")
    ledger_path = root / "run" / "ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "wave": "w",
                "reason": "r",
                "runs": [
                    {
                        "concept": "age",
                        "phase": "terminal",
                        "outcome": "complete",
                        "status": "COMPLETED",
                    }
                ],
            }
        )
    )

    code = run_pool(
        ["age"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        ledger_path=ledger_path,
        run_dir=root / "run",
    )
    assert code == 0
    assert fake_pool.opened == []  # not reopened, not re-run
    assert fake_pool.turns == []


def test_a_resumed_pool_continues_a_recorded_session(root, ctrl, fake_pool):
    """Restarting instead would re-enter the loop and spend a second HPC run."""
    _complete(ctrl, "age")
    ledger_path = root / "run" / "ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "wave": "w",
                "reason": "r",
                "runs": [
                    {
                        "concept": "age",
                        "phase": "running",
                        "session_id": "ses_age",
                        "turns": 2,
                    }
                ],
            }
        )
    )
    fake_pool.replies = {"age": ["[goal:complete]"]}
    fake_pool.final_status = {"age": "COMPLETED"}

    run_pool(
        ["age"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=1,
        ledger_path=ledger_path,
        run_dir=root / "run",
    )
    assert fake_pool.opened == []  # already opened by the interrupted pool
    assert "--session" in fake_pool.turns[0]
    assert fake_pool.turns[0][fake_pool.turns[0].index("--session") + 1] == "ses_age"


def test_a_corrupt_ledger_is_refused_not_reset(root):
    path = root / "run" / "ledger.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json")
    with pytest.raises(SystemExit, match="unreadable"):
        GoalLedger(path, wave="w", reason="r")


# ---------------------------------------------------------------------------
# dry run
# ---------------------------------------------------------------------------


def test_a_dry_run_shells_out_to_nothing_and_writes_no_ledger(
    root, ctrl, monkeypatch
):
    """Deliberately not using ``fake_pool``.

    Both subprocess boundaries are booby-trapped instead, so this exercises the
    real ``_open_concept`` and the real turn loop: a dry run that reopened a
    concept would spend the reopen it was previewing, and a dry run that
    persisted a ledger would tell the real wave the work was already done.
    """
    _complete(ctrl, "age")
    _complete(ctrl, "charlson")

    def explode(*_args, **_kwargs):
        raise AssertionError("a dry run must not shell out")

    monkeypatch.setattr(goal_pool.subprocess, "run", explode)

    code = run_pool(
        ["age", "charlson"],
        reason="warehouse rebuilt",
        artifact_root=str(root),
        parallel=2,
        run_dir=root / "run",
        dry_run=True,
    )
    assert code == 0
    assert not (root / "run" / "ledger.json").exists()
    # and the state files are untouched: still the verdict they held going in
    assert ctrl._read_state("age").status == "COMPLETED"
    assert ctrl._read_state("charlson").status == "COMPLETED"


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------


def test_the_cli_mode_choices_match_the_module(root):
    # The CLI duplicates MODES to keep the parser cheap; this is the check that
    # keeps the duplicate honest.
    assert tuple(_GOAL_MODES) == MODES


def test_invalidate_stage_only_applies_to_a_reopen(root):
    with pytest.raises(SystemExit, match="only applies to --mode reopen"):
        run_pool(
            ["age"],
            reason="r",
            artifact_root=str(root),
            mode="replay",
            invalidate_stage="fhir-prober",
        )


def test_a_wave_list_is_read_from_the_wave_file(tmp_path):
    d = tmp_path / "mimic-iv" / "concepts_fhir" / "replay"
    d.mkdir(parents=True)
    (d / "wave7.txt").write_text("alpha beta\ngamma\n")
    assert wave_concepts("7", root=tmp_path) == ["alpha", "beta", "gamma"]

    with pytest.raises(SystemExit, match="No wave list"):
        wave_concepts("8", root=tmp_path)


def test_a_run_is_only_terminal_once_it_stops(root):
    run = GoalRun(concept="age")
    assert not run.is_terminal
    run.phase = "running"
    assert not run.is_terminal
    run.phase, run.status = "terminal", "COMPLETED"
    assert run.is_terminal and run.succeeded
    run.status = "FAILED"
    assert not run.succeeded
