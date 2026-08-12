"""Resume a concept port where it left off.

Re-running ``/goal <concept>`` used to mean one of two bad outcomes.  If the
concept sat in an active status the state machine refused to start it at all
(``RUNNING`` is unreachable from ``VALIDATING_DEMO``), so the run died at
phase 2.  If it did start, the analysis agents -- source analyst, FHIR prober
-- ran again from scratch, regenerating work that was already correct and had
nothing to do with why the attempt failed.

This module answers both, and keeps them separate because they fail
differently:

``CarryoverStore``
    Concept-level analysis that outlives an attempt.  A ViewDefinition is
    attempt-scoped and immutable; "which coding system does this itemid use"
    is neither -- it is a fact about the dataset that stays true across
    attempts.  Storing it per concept lets a retry skip straight to the
    implementer.

``resume_plan``
    Reads state plus the newest attempt's artifacts and says which phase to
    re-enter, and what transition (if any) has to happen first.  It reports;
    ``apply=True`` is what performs the transition.

    At the HPC boundary the plan is determinate rather than hedged: it reads
    ``hpc_job.json`` and says *poll job <id>* or *launch*, never "unlaunched or
    unfinished".  ``write_job_record`` is write-once, so a loop that guesses
    wrong is told its attempt is spent, and obeying that abandons a live job.

``apply=True`` is refused by the CLI on a concept that still looks live -- see
``conversion_cli._refuse_if_live``.  Waves are composed by hand, so two
terminals can hold the same concept, and applying a ``fail``/``start`` under
another session throws away work in progress.

The invalidation rule is the load-bearing part.  Reuse is only safe while the
analysis is *right*: if a diagnosis traces a failure back to the mapping, then
reusing that mapping forever is how the loop burns ten attempts converging on
nothing.  So carryover is reusable by default and invalidated by name, and a
diagnosis that blames a stage must say so.
"""

from __future__ import annotations

import json
import os
import tempfile
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .conversion_state import ConversionController, StateError

__all__ = [
    "CARRYOVER_STAGES",
    "CarryoverStore",
    "ResumePlan",
    "StageStatus",
    "resume_plan",
]

#: The analysis stages whose output survives an attempt, in loop order.  The
#: implementer is deliberately absent: its output *is* the attempt, and reusing
#: it across attempts would defeat the write-once contract.
CARRYOVER_STAGES: tuple[str, ...] = (
    "source-analyst",
    "fhir-prober",
)

DEFAULT_CARRYOVER_BASE = "mimic-iv/concepts_fhir/carryover"
LEDGER_FILENAME = "carryover.json"

SHAPE_NAME = "shape.demo.json"
COMPARISON_NAME = "comparison.full.json"
SQL_NAME = "concept.sql"
JOB_RECORD_NAME = "hpc_job.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe(name: str) -> str:
    return name.strip().replace("/", "_").replace("\\", "_").replace("..", "")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Parse *path*, or ``None`` if it is absent or unreadable.

    A half-written artifact is treated as absent rather than fatal: the caller
    is deciding which phase to re-enter, and "cannot read the verdict" and "no
    verdict yet" lead to the same place.
    """
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True)
    fd, tmpname = tempfile.mkstemp(dir=str(path.parent), prefix=".carryover_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmpname, str(path))
    except Exception:
        if os.path.exists(tmpname):
            os.unlink(tmpname)
        raise


@dataclass
class StageStatus:
    """Whether one analysis stage can be reused on the next attempt."""

    stage: str
    present: bool
    fresh: bool
    path: Optional[Path] = None
    written_at_attempt: Optional[int] = None
    invalidated_at: Optional[str] = None
    invalidated_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "present": self.present,
            "fresh": self.fresh,
            "path": str(self.path) if self.path else None,
            "written_at_attempt": self.written_at_attempt,
            "invalidated_at": self.invalidated_at,
            "invalidated_reason": self.invalidated_reason,
        }


class CarryoverStore:
    """Per-concept analysis that survives across attempts.

    Layout::

        carryover/<concept>/source-analyst.md
        carryover/<concept>/fhir-prober.md
        carryover/<concept>/carryover.json     <- the ledger

    The markdown files are what agents read and write.  The ledger records
    which attempt produced each one and whether it has since been invalidated;
    invalidation is tracked rather than performed by deletion so the trail of
    "this mapping was wrong, here is who said so" stays readable.
    """

    def __init__(
        self,
        artifact_root: Optional[Union[str, Path]] = None,
        carryover_base: Optional[Union[str, Path]] = None,
    ) -> None:
        root = Path(artifact_root).resolve() if artifact_root else Path.cwd()
        if carryover_base is None:
            self.base = root / DEFAULT_CARRYOVER_BASE
        else:
            self.base = Path(carryover_base)
            if not self.base.is_absolute():
                self.base = root / self.base

    # -- paths ----------------------------------------------------------------

    def concept_dir(self, concept: str) -> Path:
        return self.base / _safe(concept)

    def stage_path(self, concept: str, stage: str) -> Path:
        if stage not in CARRYOVER_STAGES:
            raise StateError(
                f"Unknown carryover stage {stage!r}; expected one of {list(CARRYOVER_STAGES)}"
            )
        return self.concept_dir(concept) / f"{stage}.md"

    def _ledger_path(self, concept: str) -> Path:
        return self.concept_dir(concept) / LEDGER_FILENAME

    # -- ledger ---------------------------------------------------------------

    def _read_ledger(self, concept: str) -> Dict[str, Any]:
        return _read_json(self._ledger_path(concept)) or {"stages": {}}

    def _write_ledger(self, concept: str, ledger: Dict[str, Any]) -> None:
        _write_json_atomic(self._ledger_path(concept), ledger)

    # -- api ------------------------------------------------------------------

    def record(self, concept: str, stage: str, attempt: int) -> Path:
        """Mark *stage* as freshly written by *attempt*, clearing invalidation.

        The agent writes the markdown itself; this records that it did.  A
        stage recorded after being invalidated becomes fresh again -- that is
        the whole point of re-running it.
        """
        path = self.stage_path(concept, stage)
        if not path.is_file():
            raise StateError(
                f"Cannot record carryover for {concept}/{stage}: {path} does not exist. "
                f"Write the stage file first."
            )
        ledger = self._read_ledger(concept)
        ledger.setdefault("stages", {})[stage] = {
            "written_at": _utcnow(),
            "written_at_attempt": attempt,
            "invalidated_at": None,
            "invalidated_reason": None,
        }
        self._write_ledger(concept, ledger)
        return path

    def invalidate(self, concept: str, stage: str, reason: str) -> None:
        """Force *stage* to re-run on the next attempt.

        Called when a diagnosis traces a failure to this stage's output.  The
        markdown is left in place: the next run overwrites it, and until then
        it is evidence of what the wrong analysis actually said.
        """
        if stage not in CARRYOVER_STAGES:
            raise StateError(
                f"Unknown carryover stage {stage!r}; expected one of {list(CARRYOVER_STAGES)}"
            )
        if not reason or not reason.strip():
            raise StateError(
                "Invalidating carryover requires a reason -- it is the record of why "
                "the analysis was not trusted."
            )
        ledger = self._read_ledger(concept)
        entry = ledger.setdefault("stages", {}).setdefault(stage, {})
        entry["invalidated_at"] = _utcnow()
        entry["invalidated_reason"] = reason.strip()
        self._write_ledger(concept, ledger)

    def status(self, concept: str) -> List[StageStatus]:
        """Freshness of every stage, in loop order."""
        ledger = self._read_ledger(concept)
        stages = ledger.get("stages", {})
        out: List[StageStatus] = []
        for stage in CARRYOVER_STAGES:
            path = self.stage_path(concept, stage)
            present = path.is_file()
            entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
            invalidated_at = entry.get("invalidated_at")
            out.append(
                StageStatus(
                    stage=stage,
                    present=present,
                    # An unrecorded-but-present file counts as fresh: a stage
                    # written before this ledger existed is still good analysis,
                    # and refusing it would re-run every concept once for nothing.
                    fresh=present and not invalidated_at,
                    path=path if present else None,
                    written_at_attempt=entry.get("written_at_attempt"),
                    invalidated_at=invalidated_at,
                    invalidated_reason=entry.get("invalidated_reason"),
                )
            )
        return out

    def fresh_stages(self, concept: str) -> List[str]:
        return [s.stage for s in self.status(concept) if s.fresh]

    def stale_stages(self, concept: str) -> List[str]:
        return [s.stage for s in self.status(concept) if not s.fresh]


# ---------------------------------------------------------------------------
# Resume planning
# ---------------------------------------------------------------------------


@dataclass
class ResumePlan:
    """Where the loop should re-enter, and what must happen first."""

    concept: str
    status: str
    attempt: int
    action: str
    phase: Optional[str]
    reason: str
    attempt_dir: Optional[Path] = None
    transitions: List[str] = field(default_factory=list)
    fresh_stages: List[str] = field(default_factory=list)
    stale_stages: List[str] = field(default_factory=list)
    applied: bool = False
    #: Whether ``--apply`` was passed, regardless of whether anything needed
    #: doing. Without this the plan printed "pass --apply to perform the
    #: transitions" to a caller that had just passed it, which reads as "you did
    #: not do the thing" and invites a retry loop.
    apply_requested: bool = False
    new_attempt_dir: Optional[Path] = None
    #: The newest ``reopen_history`` entry, when this concept was reopened. It
    #: names the defect in the SQL the previous run shipped, so it is the
    #: instruction set for the attempt about to be authored -- not history.
    reopen_reason: Optional[str] = None
    reopen_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "status": self.status,
            "attempt": self.attempt,
            "action": self.action,
            "phase": self.phase,
            "reason": self.reason,
            "attempt_dir": str(self.attempt_dir) if self.attempt_dir else None,
            "transitions": list(self.transitions),
            "fresh_stages": list(self.fresh_stages),
            "stale_stages": list(self.stale_stages),
            "applied": self.applied,
            "apply_requested": self.apply_requested,
            "new_attempt_dir": str(self.new_attempt_dir) if self.new_attempt_dir else None,
            "reopen_reason": self.reopen_reason,
            "reopen_count": self.reopen_count,
        }

    def format(self) -> str:
        lines = [
            f"Resume plan for '{self.concept}'",
            f"  status:        {self.status} (attempt {self.attempt})",
            f"  action:        {self.action}",
            f"  re-enter at:   {self.phase or '-'}",
            f"  because:       {self.reason}",
        ]
        if self.attempt_dir:
            lines.append(f"  latest attempt: {self.attempt_dir}")
        if self.transitions:
            lines.append(f"  transitions:   {' -> '.join(self.transitions)}")
        if self.fresh_stages:
            lines.append(f"  reuse (skip):  {', '.join(self.fresh_stages)}")
        if self.stale_stages:
            lines.append(f"  must re-run:   {', '.join(self.stale_stages)}")
        if self.reopen_reason:
            # Printed loudly and last-but-one because it is the one thing on this
            # plan that the implementer must act on. It used to live only in
            # state.json: crrt's first reopen said "replace every datetime
            # mapping with a bare TRY_CAST", nothing surfaced it, and the next
            # attempt shipped the same defect twice and was marked COMPLETED.
            lines.append("")
            lines.append(
                f"  REOPENED (x{self.reopen_count}) -- this is the instruction set for "
                f"this attempt,"
            )
            lines.append("  not background. The previous run's SQL was defective:")
            lines.append("")
            for line in textwrap.wrap(self.reopen_reason, width=76):
                lines.append(f"      {line}")
            lines.append("")
            lines.append(
                "  Pass this verbatim to the implementer. Do not reproduce the "
                "superseded"
            )
            lines.append(
                "  justification as your own -- the SQL it argued about is not the "
                "SQL being"
            )
            lines.append("  judged now.")
            lines.append("")
        if self.applied:
            lines.append("  APPLIED: transitions performed.")
            if self.new_attempt_dir:
                lines.append(f"  new attempt:   {self.new_attempt_dir}")
        elif self.apply_requested:
            lines.append(
                "  --apply requested, but this plan needs no transitions. Nothing to\n"
                "  do here: proceed to the phase named above."
            )
        else:
            lines.append("  (nothing changed -- pass --apply to perform the transitions)")
        return "\n".join(lines)


def _latest_attempt_dir(ctrl: ConversionController, concept: str, attempt: int) -> Optional[Path]:
    if attempt <= 0:
        return None
    path = ctrl._attempt_dir(concept, attempt)  # noqa: SLF001 -- same package
    return path if path.exists() else None


def _demo_phase(attempt_dir: Optional[Path]) -> tuple[str, str, Optional[str]]:
    """Read the newest attempt's demo artifacts.

    Returns ``(situation, reason, verdict)`` where situation is one of
    ``no_artifacts``, ``no_shape``, ``shape_fail``, ``shape_pass``.
    """
    if attempt_dir is None:
        return "no_artifacts", "no attempt directory on disk", None
    if not (attempt_dir / SQL_NAME).is_file():
        return "no_artifacts", f"{SQL_NAME} was never written", None
    shape = _read_json(attempt_dir / SHAPE_NAME)
    if shape is None:
        return "no_shape", f"{SQL_NAME} exists but {SHAPE_NAME} does not", None
    verdict = shape.get("verdict")
    if verdict == "shape_fail":
        return "shape_fail", f"demo shape gate returned {verdict}", verdict
    return "shape_pass", f"demo shape gate returned {verdict}", verdict


def resume_plan(
    concept: str,
    *,
    artifact_root: Optional[Union[str, Path]] = None,
    carryover_base: Optional[Union[str, Path]] = None,
    apply: bool = False,
    controller: Optional[ConversionController] = None,
) -> ResumePlan:
    """Decide where to re-enter the loop for *concept*.

    With ``apply=False`` this only reads.  With ``apply=True`` it performs the
    transitions it named -- and only those: it never runs an agent, never
    writes into an attempt, and never touches carryover.
    """
    ctrl = controller or ConversionController(artifact_root=artifact_root)
    store = CarryoverStore(
        artifact_root=artifact_root or ctrl.artifact_root,
        carryover_base=carryover_base,
    )

    state = ctrl._read_state(concept)  # noqa: SLF001 -- same package
    if state is None:
        raise StateError(
            f"Concept '{concept}' has not been initialised; run `mimic_utils init {concept}` first"
        )

    attempt_dir = _latest_attempt_dir(ctrl, concept, state.attempt)
    fresh = store.fresh_stages(concept)
    stale = store.stale_stages(concept)

    # The newest reopen entry, if any. Surfaced on every plan rather than only
    # on the reopened-and-unstarted one: a reopened concept can be resumed many
    # times before its new SQL is written, and the defect being fixed stays
    # relevant for every one of them.
    reopen_history = list(state.reopen_history or [])
    reopen_reason = reopen_history[-1].get("reason") if reopen_history else None

    def plan(action: str, phase: Optional[str], reason: str, transitions: Sequence[str] = ()) -> ResumePlan:
        return ResumePlan(
            concept=concept,
            status=state.status,
            attempt=state.attempt,
            action=action,
            phase=phase,
            reason=reason,
            attempt_dir=attempt_dir,
            transitions=list(transitions),
            fresh_stages=fresh,
            stale_stages=stale,
            reopen_reason=reopen_reason,
            reopen_count=len(reopen_history),
        )

    status = state.status

    if status in ("COMPLETED", "COMPLETED_WITH_DIVERGENCE"):
        result = plan(
            "nothing_to_do",
            None,
            f"concept is {status}; the port is finished. If the SQL it shipped "
            f"is defective, that is not a resume -- it discards a recorded "
            f"verdict, so it goes through `reopen <concept> --by human "
            f"--reason \"...\"`, which costs a fresh attempt and a full run.",
        )
    elif status == "BLOCKED_REPRESENTATION":
        result = plan(
            "blocked",
            None,
            "blocked on representability -- a human decides this, not a rerun. "
            "They can send it back with `retry`, or accept it with "
            "`accept-divergence --by human --justification \"...\"`",
        )
    elif status in ("PENDING", "FAILED", "SKIPPED"):
        result = plan(
            "start_new_attempt",
            "3 (analysis -> implementer)",
            f"status {status} is startable; a new attempt directory is next",
            transitions=["start"],
        )
    elif status == "RUNNING":
        situation, reason, _ = _demo_phase(attempt_dir)
        if situation == "no_artifacts":
            result = plan(
                "continue_attempt",
                "3 (analysis -> implementer)",
                f"attempt {state.attempt} is open and unwritten: {reason}",
            )
        elif situation == "no_shape":
            result = plan(
                "continue_attempt", "4 (demo shape gate)",
                f"attempt {state.attempt} has SQL but no demo verdict: {reason}",
            )
        elif situation == "shape_fail":
            result = plan(
                "start_new_attempt", "5 (mismatch resolution)",
                f"attempt {state.attempt} already failed the demo gate: {reason}",
                transitions=["fail", "start"],
            )
        else:
            result = plan(
                "continue_attempt", "6 (full-data run)",
                f"attempt {state.attempt} cleared the demo gate: {reason}",
                transitions=["validate-full"],
            )
    elif status == "VALIDATING_DEMO":
        situation, reason, _ = _demo_phase(attempt_dir)
        if situation == "shape_fail":
            result = plan(
                "start_new_attempt", "5 (mismatch resolution)",
                f"{reason}; RUNNING is unreachable from VALIDATING_DEMO, so a "
                f"`fail` must precede the retry",
                transitions=["fail", "start"],
            )
        elif situation == "shape_pass":
            result = plan(
                "continue_attempt", "6 (full-data run)",
                f"{reason}; the demo gate is already satisfied",
                transitions=["validate-full"],
            )
        else:
            # No verdict on disk, yet the state machine says the gate was
            # entered. The gate is cheap, so re-running it beats guessing.
            result = plan(
                "start_new_attempt", "4 (demo shape gate)",
                f"status is VALIDATING_DEMO but {reason}; the attempt cannot be "
                f"resumed in place, so a `fail` must precede the retry",
                transitions=["fail", "start"],
            )
    elif status == "VALIDATING_FULL":
        comparison = _read_json(attempt_dir / COMPARISON_NAME) if attempt_dir else None
        if comparison is None:
            # "Unlaunched or unfinished" is the one thing this plan must not
            # say. `write_job_record` is write-once, so a resumed loop that
            # guesses "launch" hits *"hpc_job.json already exists"*, and
            # complying with that error abandons a live cluster job, burns the
            # attempt, and spends one of the ten runs the contract allots.
            # hpc_job.json settles it: present means poll, absent means launch.
            record = _read_json(attempt_dir / JOB_RECORD_NAME) if attempt_dir else None
            if record and record.get("job_id"):
                submitted = record.get("submitted_at") or "an unrecorded time"
                result = plan(
                    "continue_attempt", "6 (full-data run)",
                    f"no {COMPARISON_NAME} yet, but {JOB_RECORD_NAME} records job "
                    f"{record['job_id']} submitted at {submitted}: the job is "
                    f"live or already finished. Poll it — do NOT launch, the "
                    f"job record is write-once and a second run needs a new "
                    f"attempt",
                )
            else:
                result = plan(
                    "continue_attempt", "6 (full-data run)",
                    f"no {COMPARISON_NAME} and no {JOB_RECORD_NAME}: nothing was "
                    f"ever submitted for this attempt. Launch",
                )
        else:
            verdict = comparison.get("verdict")
            tier = (comparison.get("divergence") or {}).get("tier")
            if verdict == "mismatch":
                result = plan(
                    "start_new_attempt", "5 (mismatch resolution)",
                    f"full comparison returned {verdict}: a contradiction the "
                    f"judge cannot weigh needs a new attempt",
                    transitions=["fail", "start"],
                )
            elif verdict == "review" and tier == "contested":
                # Phase 5 WITHOUT a retry transition: the diagnostician decides
                # whether this is a bug (retry) or upstream ETL loss (judge).
                # Pre-emptively failing the attempt would throw away a result
                # that may need no fix at all.
                result = plan(
                    "continue_attempt", "5 (diagnose the conflict), then 7",
                    "full comparison returned review/contested: a value "
                    "conflict, which is either a port bug or upstream ETL "
                    "transformation loss. Diagnose before retrying or judging",
                )
            elif verdict == "review":
                result = plan(
                    "continue_attempt", "7 (equivalence judge)",
                    f"full comparison returned {verdict}/{tier}: only "
                    f"gap-shaped divergence remains",
                )
            else:
                result = plan(
                    "continue_attempt", "8 (promote)",
                    f"full comparison returned {verdict}",
                )
    else:  # pragma: no cover -- STATUS_VALUES is closed
        raise StateError(f"Unhandled status {status!r} for '{concept}'")

    result.apply_requested = apply
    if apply and result.transitions:
        _apply(ctrl, concept, result)

    return result


def _apply(ctrl: ConversionController, concept: str, plan_: ResumePlan) -> None:
    """Perform the planned transitions. Only `fail` and `start` are automated.

    `validate-full` is deliberately not applied: it is the gate that authorises
    spending an HPC run, and nothing that calls itself `resume` should spend one
    as a side effect.
    """
    for step in plan_.transitions:
        if step == "fail":
            ctrl.transition(
                concept,
                "FAILED",
                error_message=f"auto-failed by resume: {plan_.reason}",
                counter="engineering",
            )
        elif step == "start":
            ctrl.start(concept)
        else:
            plan_.reason += (
                f" (transition '{step}' left for the orchestrator: resume does not "
                f"authorise it)"
            )
            continue
    plan_.applied = True
    plan_.new_attempt_dir = ctrl.attempt_dir(concept)
