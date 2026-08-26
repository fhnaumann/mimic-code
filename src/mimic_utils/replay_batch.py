"""Drive a wave of replays with no agent in the loop.

A defect reopen needs an orchestrator because a human judgement -- what is wrong
with this SQL, what should replace it -- sits in the middle of it.  A replay does
not.  Every stage between the carried-forward port and the verdict is already a
deterministic CLI call, and the one stage that genuinely needs a model, the
equivalence judge, is only reached when the comparator returns ``review``.  So
for a wave of 40-odd concepts the honest architecture is a loop, not a fleet of
sessions: run the deterministic stages here, promote the concepts that come back
``match``, and hand out ``/goal`` sessions only for the ones that still have
something to argue about.

Stages, per concept::

    replay   mimic_utils replay <c> --reason "..."      (reopen + carry the port)
    demo     mimic_utils validate-demo <c>              (lints the carried SQL)
             mimic_utils run-demo <c>                   (0 shape_ok, 2 unsure -> both fine)
    launch   mimic_utils validate-full <c>
             mimic_utils hpc-launch <c>
    poll     mimic_utils hpc-poll <c>                   (fetches comparison.full.json)
    promote  match -> mimic_utils done <c>
             review/mismatch -> left alone, reported as needing a /goal session

``launch`` is run for the whole wave before any ``poll``, because the jobs queue
concurrently: polling each concept to completion before submitting the next would
serialise a wave that the cluster is happy to run in parallel.

Every result is written to a ledger under
``mimic-iv/concepts_fhir/replay/<wave>.json`` after each stage, so an interrupted
wave resumes instead of restarting -- and so a concept that already has a live
job is never launched twice.  ``hpc_job.json`` is write-once; a second launch on
the same attempt abandons a live job and spends one of the ten runs the contract
allots.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

__all__ = ["STAGES", "WaveLedger", "run_wave"]

#: In order. A concept at stage N has completed N and everything before it.
STAGES: Tuple[str, ...] = ("replay", "demo", "launch", "poll", "promote")

DEFAULT_LEDGER_DIR = "mimic-iv/concepts_fhir/replay"
COMPARISON_NAME = "comparison.full.json"

#: run-demo: 0 shape_ok, 2 unsure. Both earn permission to spend an HPC run --
#: "0 demo rows is unsure, never fail" is in the loop contract, and the demo
#: cohort legitimately contains nothing for some concepts.
DEMO_OK = (0, 2)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ConceptRun:
    concept: str
    stage: Optional[str] = None
    verdict: Optional[str] = None
    tier: Optional[str] = None
    error: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def done_stages(self) -> int:
        return STAGES.index(self.stage) + 1 if self.stage in STAGES else 0

    def record(self, stage: str, argv: Sequence[str], code: int) -> None:
        self.history.append(
            {"stage": stage, "at": _utcnow(), "argv": list(argv), "exit": code}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "stage": self.stage,
            "verdict": self.verdict,
            "tier": self.tier,
            "error": self.error,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ConceptRun":
        return cls(
            concept=raw["concept"],
            stage=raw.get("stage"),
            verdict=raw.get("verdict"),
            tier=raw.get("tier"),
            error=raw.get("error"),
            history=list(raw.get("history") or []),
        )


class WaveLedger:
    """Per-concept progress, flushed after every stage."""

    def __init__(self, path: Path, *, wave: str, reason: str, dry_run: bool = False) -> None:
        self.path = path
        self.wave = wave
        self.reason = reason
        # A dry run must not persist progress. Every stage "succeeds" without
        # running, so a flushed ledger would tell the real wave that everything
        # was already done -- the dry run would consume the wave it previewed.
        self.dry_run = dry_run
        self.runs: Dict[str, ConceptRun] = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                for entry in raw.get("runs") or []:
                    self.runs[entry["concept"]] = ConceptRun.from_dict(entry)
            except (OSError, json.JSONDecodeError, KeyError):
                # A corrupt ledger must not silently reset a wave's progress:
                # refuse rather than re-launch jobs that are already queued.
                raise SystemExit(
                    f"Ledger {path} is unreadable. Fix or move it before "
                    f"continuing -- treating it as empty would re-launch live jobs."
                )

    def get(self, concept: str) -> ConceptRun:
        return self.runs.setdefault(concept, ConceptRun(concept=concept))

    def flush(self) -> None:
        if self.dry_run:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "wave": self.wave,
            "reason": self.reason,
            "updated_at": _utcnow(),
            "runs": [r.to_dict() for r in self.runs.values()],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def _run(argv: Sequence[str], *, dry_run: bool) -> int:
    # argv is [python, -m, mimic_utils, ...]; show it the way a human would type it
    print("    $ mimic_utils " + " ".join(argv[3:]), flush=True)
    if dry_run:
        return 0
    return subprocess.run(list(argv)).returncode


def _cli(*args: str, artifact_root: Optional[str] = None) -> List[str]:
    argv = [sys.executable, "-m", "mimic_utils", *args]
    if artifact_root:
        argv += ["--artifact-root", artifact_root]
    return argv


def _read_verdict(
    concept: str, artifact_root: Optional[Union[str, Path]]
) -> Tuple[Optional[str], Optional[str]]:
    """``(verdict, tier)`` from the current attempt's comparison artifact."""
    from .conversion_state import ConversionController

    ctrl = ConversionController(artifact_root=artifact_root)
    attempt_dir = ctrl.attempt_dir(concept)
    if attempt_dir is None:
        return None, None
    path = Path(attempt_dir) / COMPARISON_NAME
    if not path.is_file():
        return None, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    return raw.get("verdict"), ((raw.get("divergence") or {}).get("tier"))


def run_wave(
    concepts: Sequence[str],
    *,
    reason: str,
    wave: str = "wave",
    artifact_root: Optional[str] = None,
    ledger_path: Optional[Union[str, Path]] = None,
    stages: Sequence[str] = STAGES,
    dry_run: bool = False,
) -> int:
    """Run *concepts* through *stages*.  Returns a process exit code.

    Stages are cumulative and resumable: a concept whose ledger entry already
    records ``launch`` is not launched again, whatever is passed here.
    """
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        raise SystemExit(f"Unknown stage(s) {unknown}; expected any of {list(STAGES)}")
    wanted = [s for s in STAGES if s in stages]

    ledger = WaveLedger(
        Path(ledger_path) if ledger_path else Path(artifact_root or ".") / DEFAULT_LEDGER_DIR / f"{wave}.json",
        wave=wave,
        reason=reason,
        dry_run=dry_run,
    )

    def stage_needed(run: ConceptRun, stage: str) -> bool:
        if run.error:
            return False
        return run.done_stages <= STAGES.index(stage)

    def advance(
        run: ConceptRun,
        stage: str,
        argv: Sequence[str],
        ok: Sequence[int] = (0,),
        set_stage: bool = True,
    ) -> bool:
        """Run one command; mark *stage* reached only when it is really reached.

        ``set_stage=False`` is for the first of a two-command stage: marking the
        stage after ``validate-full`` but before ``hpc-launch`` would let a
        resumed wave believe a job was submitted when none was.
        """
        code = _run(argv, dry_run=dry_run)
        run.record(stage, argv, code)
        if code not in ok:
            run.error = f"{' '.join(argv[3:5])} exited {code}"
            ledger.flush()
            print(f"  !! {run.concept}: {run.error}", flush=True)
            return False
        if set_stage:
            run.stage = stage
        ledger.flush()
        return True

    # --- local stages, concept by concept -----------------------------------
    for concept in concepts:
        run = ledger.get(concept)
        if run.error:
            print(f"  -- {concept}: skipped, previously errored ({run.error})", flush=True)
            continue
        print(f"  {concept} (at stage {run.stage or 'none'})", flush=True)

        if "replay" in wanted and stage_needed(run, "replay"):
            if not advance(
                run, "replay", _cli("replay", concept, "--reason", reason, artifact_root=artifact_root)
            ):
                continue

        if "demo" in wanted and stage_needed(run, "demo"):
            # validate-demo is where the lint runs, and it is the transition that
            # freezes the implementation artifacts -- on a replay that is the one
            # gate proving the carried SQL is still legal.
            if not advance(
                run, "demo",
                _cli("validate-demo", concept, artifact_root=artifact_root),
                set_stage=False,
            ):
                continue
            # run-demo completes the same stage: a gate that was entered but not
            # executed leaves the concept in VALIDATING_DEMO with nothing on disk,
            # which `resume` can only resolve by failing the attempt.
            if not advance(
                run, "demo",
                _cli("run-demo", concept, artifact_root=artifact_root),
                ok=DEMO_OK,
            ):
                continue

        if "launch" in wanted and stage_needed(run, "launch"):
            if not advance(
                run, "launch",
                _cli("validate-full", concept, artifact_root=artifact_root),
                set_stage=False,
            ):
                continue
            if not advance(
                run, "launch", _cli("hpc-launch", concept, artifact_root=artifact_root)
            ):
                continue

    # --- poll, after the whole wave is queued -------------------------------
    if "poll" in wanted:
        print("\n  polling submitted jobs\n", flush=True)
        for concept in concepts:
            run = ledger.get(concept)
            if run.error or not stage_needed(run, "poll"):
                continue
            if run.done_stages < STAGES.index("launch") + 1:
                continue  # never launched; nothing to poll
            # hpc-poll exits 1 on mismatch, which is a verdict rather than a
            # failure of the poll, so the artifact -- not the exit code --
            # decides. 0/1/2 all mean "the comparison came back".
            advance(
                run, "poll",
                _cli("hpc-poll", concept, artifact_root=artifact_root),
                ok=(0, 1, 2),
            )

    # --- promote ------------------------------------------------------------
    needs_judge: List[ConceptRun] = []
    if "promote" in wanted:
        print("\n  promoting exact matches\n", flush=True)
        for concept in concepts:
            run = ledger.get(concept)
            if run.error or run.done_stages < STAGES.index("poll") + 1:
                continue
            if dry_run:
                # There is no verdict to read: nothing ran. Say what the rule is
                # rather than inventing a result for it.
                print(
                    f"    {concept}: would read comparison.full.json -- "
                    f"`match` promotes to COMPLETED, anything else waits for a "
                    f"/goal judge session",
                    flush=True,
                )
                continue
            run.verdict, run.tier = _read_verdict(concept, artifact_root)
            if run.verdict == "match":
                advance(
                    run, "promote",
                    _cli("done", concept, artifact_root=artifact_root),
                )
            elif run.verdict is None:
                run.error = "polled but no comparison.full.json verdict on disk"
                ledger.flush()
            else:
                run.stage = "poll"
                needs_judge.append(run)
                ledger.flush()

    # --- report -------------------------------------------------------------
    matched = [r for r in ledger.runs.values() if r.verdict == "match" and not r.error]
    errored = [r for r in ledger.runs.values() if r.error]
    print("\n" + "=" * 72)
    print(f"replay wave '{wave}': {len(concepts)} concept(s)")
    print(f"  match, promoted to COMPLETED: {len(matched)}")
    if matched:
        print("    " + " ".join(r.concept for r in matched))
    if needs_judge:
        print(f"  needs a judge session ({len(needs_judge)}):")
        for r in needs_judge:
            print(f"    /goal {r.concept}    # {r.verdict}/{r.tier}")
    if errored:
        print(f"  errored ({len(errored)}):")
        for r in errored:
            print(f"    {r.concept}: {r.error}")
    print(f"  ledger: {ledger.path}")
    print("=" * 72)
    return 1 if errored else 0
