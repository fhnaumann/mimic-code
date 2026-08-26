"""Drive a pool of ``/goal`` sessions -- k concepts at a time, in DAG order.

``replay_batch`` exists because most of a replay needs no model at all.  This
module is for the other shape: a wave where the orchestrator loop really does
have to run -- a re-implement, or a replay whose ``review`` verdict needs a judge
-- and where doing it by hand means one terminal per concept, one ``opencode
--auto``, one ``/goal <concept>``, and a human watching for it to finish.

What the human does by hand, this does in a loop::

    mimic_utils replay <c> --by human --reason "..."   # or reopen, per --mode
    opencode run --agent concept-port-orchestrator --auto <c>
    ... and keeps sending the session a continuation until it emits a
        terminal marker, because in headless mode nothing else will (below)

k of those run at once.  When one finishes, the next eligible concept starts --
"eligible" meaning every dependency of it that is *also in this run set* has
reached ``COMPLETED`` or ``COMPLETED_WITH_DIVERGENCE``.  That is not a
convenience: ``replay`` and ``start`` both refuse a concept whose dependency is
not satisfied, and both runners preprocess a dependency's own attempt output, so
a dependent opened while its dependency is mid-run would either be refused or
measured against a candidate that is about to change.

Why this drives the turns itself
--------------------------------

The ``/goal`` command is backed by ``opencode-goal-plugin``, which auto-continues
an idle session until a terminal marker appears.  Under ``opencode run`` it does
not: the command's ``$ARGUMENTS`` reaches the model as an ordinary chat turn (a
documented limitation of the plugin's ``command.execute.before`` hook on this
OpenCode line), the plugin reads that as "a new human message arrived, the latest
instruction wins", and pauses the goal it just created.  Verified on OpenCode
1.18.19: the goal lands in the state file with ``stopReason: "user
intervention"`` and the process exits after one assistant turn.

So the continuation engine is here instead, which is the better place for it
anyway -- the stop condition is a marker in the transcript, and every turn
boundary is a place to record progress and re-check the budget.

Two further consequences of running several OpenCode processes at once:

* The goal plugin holds an **exclusive** lease on its state file for the
  lifetime of the plugin instance and refuses a second writer.  Every worker
  therefore gets its own ``OPENCODE_GOAL_STATE_PATH``.  Without that, workers
  2..k would fail plugin init and the human's own ``.opencode/goals/state.json``
  would be in the middle of it.
* Only one local Spark may run at a time, so ``$MIMIC_SPARK_LOCK`` is set in
  every child.  Parallel ``run-demo`` calls then queue on the ``flock`` instead
  of colliding -- including with a ``/goal`` a human is running in another
  terminal, as long as it uses the same lock path.

The marker stops the loop; the state file decides the outcome
-------------------------------------------------------------

``[goal:complete]`` is what the orchestrator *says*.  What actually happened is
in ``state/<concept>/state.json``, and on a divergence accept the orchestrator
emits ``[goal:complete-with-divergence]`` and then a ``[goal:complete]`` pair, so
reading the last marker alone would report an exact match that never happened.
Markers are treated as the stop signal only; the controller status is the result.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

__all__ = ["MODES", "GoalLedger", "GoalRun", "run_pool", "wave_concepts"]

#: How a concept is opened before its session starts.
#:   replay -- carry the port forward byte-identical (a data rebuild)
#:   reopen -- open for re-implementation (the mapping itself must change)
#:   none   -- already open; go straight to the session
MODES: Tuple[str, ...] = ("replay", "reopen", "none")

DEFAULT_RUN_DIR = "mimic-iv/concepts_fhir/replay"
DEFAULT_AGENT = "concept-port-orchestrator"
DEFAULT_SPARK_LOCK = "~/.mimic-spark.lock"

#: The controller's own definition of a satisfied dependency.
SUCCESS_STATUSES = frozenset({"COMPLETED", "COMPLETED_WITH_DIVERGENCE"})
TERMINAL_STATUSES = SUCCESS_STATUSES | frozenset({"FAILED", "BLOCKED_REPRESENTATION"})

#: Checked in this order.  `blocked` beats everything; the divergence marker must
#: be checked before the bare `[goal:complete]` that the orchestrator emits after
#: it, or an accepted divergence would be recorded as an exact match.
MARKER_ORDER: Tuple[Tuple[str, str], ...] = (
    ("[goal:blocked]", "blocked"),
    ("[goal:complete-with-divergence]", "complete_with_divergence"),
    ("[goal:complete]", "complete"),
)

#: Sent when a turn ends with no terminal marker.  Deliberately thin: `resume` is
#: the orchestrator's own re-orientation tool, so the nudge points at it instead
#: of restating the loop and risking a restarted phase.
CONTINUE_PROMPT = (
    "Continue the port loop for {concept}. Do not redo a phase that already has "
    "an artifact on disk -- run `mimic_utils resume {concept}` first if you need "
    "to re-establish where you are. When you reach a terminal state, finalize "
    "metrics, commit if the outcome permits it, and emit the required "
    "[goal:...] marker."
)

_print_lock = threading.Lock()


def _say(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def wave_concepts(wave: str, *, root: Optional[Union[str, Path]] = None) -> List[str]:
    """Concept stems from ``replay/wave<N>.txt`` -- one source of truth for order.

    The wave files are already the DAG-ordered lists the rerun plan was built
    from; re-deriving the order here would just be a second place to be wrong.
    """
    path = Path(root or ".") / DEFAULT_RUN_DIR / f"wave{wave}.txt"
    if not path.is_file():
        raise SystemExit(f"No wave list at {path}")
    return path.read_text(encoding="utf-8").split()


@dataclass
class GoalRun:
    """One concept's trip through the pool."""

    concept: str
    mode: str = "replay"
    phase: str = "queued"  # queued | opened | running | terminal | skipped
    session_id: Optional[str] = None
    turns: int = 0
    outcome: Optional[str] = None  # complete | complete_with_divergence | blocked
    #                                | exhausted | timeout | error | dependency
    status: Optional[str] = None  # controller status when the session stopped
    error: Optional[str] = None
    seconds: float = 0.0
    history: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.phase in ("terminal", "skipped")

    @property
    def succeeded(self) -> bool:
        return self.status in SUCCESS_STATUSES

    def record(self, event: str, **fields: Any) -> None:
        self.history.append({"event": event, "at": _utcnow(), **fields})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "mode": self.mode,
            "phase": self.phase,
            "session_id": self.session_id,
            "turns": self.turns,
            "outcome": self.outcome,
            "status": self.status,
            "error": self.error,
            "seconds": round(self.seconds, 1),
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "GoalRun":
        return cls(
            concept=raw["concept"],
            mode=raw.get("mode") or "replay",
            phase=raw.get("phase") or "queued",
            session_id=raw.get("session_id"),
            turns=int(raw.get("turns") or 0),
            outcome=raw.get("outcome"),
            status=raw.get("status"),
            error=raw.get("error"),
            seconds=float(raw.get("seconds") or 0.0),
            history=list(raw.get("history") or []),
        )


class GoalLedger:
    """Per-concept progress, flushed on every transition, safe across threads."""

    def __init__(
        self, path: Path, *, wave: str, reason: str, dry_run: bool = False
    ) -> None:
        self.path = path
        self.wave = wave
        self.reason = reason
        # A dry run must not persist: every step "succeeds" without running, so a
        # flushed ledger would tell the real wave the work was already done.
        self.dry_run = dry_run
        self.runs: Dict[str, GoalRun] = {}
        self._lock = threading.Lock()
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                for entry in raw.get("runs") or []:
                    self.runs[entry["concept"]] = GoalRun.from_dict(entry)
            except (OSError, json.JSONDecodeError, KeyError):
                # Treating a corrupt ledger as empty would re-open concepts that
                # are already running and spend their reopens twice.
                raise SystemExit(
                    f"Ledger {path} is unreadable. Fix or move it before "
                    f"continuing -- treating it as empty would restart concepts "
                    f"that may already be running."
                )

    def get(self, concept: str) -> GoalRun:
        with self._lock:
            return self.runs.setdefault(concept, GoalRun(concept=concept))

    def flush(self) -> None:
        if self.dry_run:
            return
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "wave": self.wave,
                "reason": self.reason,
                "updated_at": _utcnow(),
                "runs": [r.to_dict() for r in self.runs.values()],
            }
            tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
            tmp.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            tmp.replace(self.path)


# --------------------------------------------------------------------------- #
# controller access
# --------------------------------------------------------------------------- #


def _controller(artifact_root: Optional[str]):
    from .conversion_state import ConversionController

    return ConversionController(artifact_root=artifact_root)


def _status_of(concept: str, artifact_root: Optional[str]) -> Optional[str]:
    """The controller's recorded status, or ``None`` if the concept has no state.

    Read fresh every time rather than cached: the whole point of a pool is that
    another worker changed this while we were not looking.
    """
    state = _controller(artifact_root)._read_state(concept)  # noqa: SLF001
    return state.status if state is not None else None


def _dependencies(
    concepts: Sequence[str], artifact_root: Optional[str]
) -> Dict[str, Set[str]]:
    """``{concept: deps within this run set}``."""
    ctrl = _controller(artifact_root)
    in_set = set(concepts)
    dag = ctrl.dag
    return {c: set(dag.get(c, set())) & in_set for c in concepts}


# --------------------------------------------------------------------------- #
# one concept
# --------------------------------------------------------------------------- #


def _cli(*args: str, artifact_root: Optional[str] = None) -> List[str]:
    argv = [sys.executable, "-m", "mimic_utils", *args]
    if artifact_root:
        argv += ["--artifact-root", artifact_root]
    return argv


def _shown(argv: Sequence[str]) -> str:
    """The command as a human would have to type it -- quoted, so it is runnable.

    A reason string containing ``#`` echoed unquoted turns the rest of the line
    into a shell comment, which is a trap for anyone copying it out of the log.
    """
    return shlex.join(list(argv)[3:])


def _child_env(goal_state: Path, spark_lock: str) -> Dict[str, str]:
    env = dict(os.environ)
    # One state file per worker: the goal plugin's lease is exclusive for the
    # plugin instance's lifetime and refuses a second writer outright.
    env["OPENCODE_GOAL_STATE_PATH"] = str(goal_state)
    env.setdefault("MIMIC_SPARK_LOCK", spark_lock)
    return env


@dataclass
class _TurnResult:
    session_id: Optional[str]
    text: str
    returncode: int
    timed_out: bool = False


def _run_turn(
    argv: Sequence[str],
    *,
    env: Dict[str, str],
    cwd: Path,
    transcript: Optional[Path],
    timeout: float,
) -> _TurnResult:
    """One ``opencode run`` invocation; returns its session id and all its text."""
    try:
        proc = subprocess.run(
            list(argv),
            env=env,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        if isinstance(partial, bytes):  # pragma: no cover - text=True path
            partial = partial.decode("utf-8", "replace")
        return _TurnResult(
            session_id=_session_id_in(partial), text=partial, returncode=-1, timed_out=True
        )

    if transcript is not None:
        transcript.parent.mkdir(parents=True, exist_ok=True)
        with transcript.open("a", encoding="utf-8") as fh:
            fh.write(proc.stdout)
            if proc.stderr.strip():
                fh.write(
                    json.dumps({"type": "stderr", "text": proc.stderr}) + "\n"
                )
    return _TurnResult(
        session_id=_session_id_in(proc.stdout),
        text=_text_in(proc.stdout) + "\n" + proc.stderr,
        returncode=proc.returncode,
    )


def _events(stdout: str):
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _session_id_in(stdout: str) -> Optional[str]:
    for event in _events(stdout):
        sid = event.get("sessionID") or (event.get("part") or {}).get("sessionID")
        if sid:
            return sid
    return None


def _text_in(stdout: str) -> str:
    """Assistant text only.

    Tool arguments are excluded on purpose: a marker quoted inside a `grep` for
    it, or inside a file the agent wrote, is not the agent claiming completion.
    """
    chunks = []
    for event in _events(stdout):
        if event.get("type") != "text":
            continue
        text = (event.get("part") or {}).get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _marker_in(text: str) -> Optional[str]:
    for marker, outcome in MARKER_ORDER:
        if marker in text:
            return outcome
    return None


def _open_concept(
    run: GoalRun,
    *,
    reason: str,
    artifact_root: Optional[str],
    invalidate_stage: Optional[str],
    dry_run: bool,
) -> bool:
    """``replay`` / ``reopen`` the concept.  False means do not start a session."""
    if run.mode == "none":
        return True

    argv = _cli(
        run.mode, run.concept, "--by", "human", "--reason", reason,
        artifact_root=artifact_root,
    )
    _say(f"  [{run.concept}] $ mimic_utils {_shown(argv)}")
    code = 0 if dry_run else subprocess.run(list(argv)).returncode
    run.record(run.mode, exit=code)
    if code != 0:
        run.phase, run.outcome = "skipped", "error"
        run.error = f"{run.mode} exited {code}"
        return False

    if run.mode == "reopen" and invalidate_stage:
        argv = _cli(
            "carryover-invalidate", run.concept, "--stage", invalidate_stage,
            "--reason", reason, artifact_root=artifact_root,
        )
        _say(f"  [{run.concept}] $ mimic_utils {_shown(argv)}")
        code = 0 if dry_run else subprocess.run(list(argv)).returncode
        run.record("carryover-invalidate", stage=invalidate_stage, exit=code)
        if code != 0:
            run.phase, run.outcome = "skipped", "error"
            run.error = f"carryover-invalidate exited {code}"
            return False

    run.phase = "opened"
    return True


def _drive_concept(
    run: GoalRun,
    *,
    ledger: GoalLedger,
    reason: str,
    artifact_root: Optional[str],
    agent: str,
    model: Optional[str],
    run_dir: Path,
    project_dir: Path,
    spark_lock: str,
    max_turns: int,
    turn_timeout: float,
    concept_budget: float,
    invalidate_stage: Optional[str],
    dry_run: bool,
) -> GoalRun:
    """Open one concept, then drive its session until it is terminal."""
    started = time.monotonic()

    if run.phase == "queued":
        if not _open_concept(
            run,
            reason=reason,
            artifact_root=artifact_root,
            invalidate_stage=invalidate_stage,
            dry_run=dry_run,
        ):
            ledger.flush()
            _say(f"  [{run.concept}] !! {run.error}")
            return run
        ledger.flush()

    goal_state = run_dir / "goalstate" / run.concept / "state.json"
    transcript = run_dir / "sessions" / f"{run.concept}.jsonl"
    env = _child_env(goal_state, spark_lock)
    run.phase = "running"
    ledger.flush()

    def turn_argv() -> List[str]:
        argv = ["opencode", "run", "--auto", "--format", "json"]
        if run.session_id:
            argv += ["--session", run.session_id]
        else:
            argv += ["--agent", agent]
        if model:
            argv += ["--model", model]
        # The first turn reproduces `/goal <concept>` exactly: the command's
        # template is `$ARGUMENTS`, and it takes the bare concept stem and
        # nothing else -- prose alongside it is rejected. Situation for the agent
        # travels in the reopen reason instead, which `resume` prints back to it.
        argv.append(
            run.concept
            if run.turns == 0
            else CONTINUE_PROMPT.format(concept=run.concept)
        )
        return argv

    if dry_run:
        _say(
            f"  [{run.concept}] $ {shlex.join(turn_argv())}"
            f"   # then continued until a [goal:...] marker, max {max_turns} turns"
        )
        run.phase, run.outcome, run.status = "terminal", "dry_run", None
        run.seconds = time.monotonic() - started
        ledger.flush()
        return run

    while True:
        if run.turns >= max_turns:
            run.outcome = "exhausted"
            run.error = f"no terminal marker after {run.turns} turn(s)"
            break
        if time.monotonic() - started > concept_budget:
            run.outcome = "timeout"
            run.error = f"exceeded the {concept_budget:.0f}s budget for one concept"
            break

        result = _run_turn(
            turn_argv(),
            env=env,
            cwd=project_dir,
            transcript=transcript,
            timeout=turn_timeout,
        )
        run.turns += 1
        if result.session_id and not run.session_id:
            run.session_id = result.session_id
        marker = _marker_in(result.text)
        run.record(
            "turn",
            turn=run.turns,
            exit=result.returncode,
            timed_out=result.timed_out,
            marker=marker,
        )
        ledger.flush()
        _say(
            f"  [{run.concept}] turn {run.turns}: exit {result.returncode}"
            + (f", marker {marker}" if marker else "")
            + (", TIMED OUT" if result.timed_out else "")
        )

        if result.timed_out:
            run.outcome = "timeout"
            run.error = f"turn {run.turns} exceeded {turn_timeout:.0f}s"
            break
        if marker:
            run.outcome = marker
            break
        if result.returncode != 0 and not run.session_id:
            # It never got a session: a bad agent name, a provider failure, a
            # config error. Continuing would only repeat it.
            run.outcome = "error"
            run.error = f"opencode run exited {result.returncode} with no session"
            break

    # The marker is what the orchestrator says; the state file is what happened.
    run.status = _status_of(run.concept, artifact_root)
    run.phase = "terminal"
    run.seconds = time.monotonic() - started
    ledger.flush()
    _say(
        f"  [{run.concept}] done: outcome={run.outcome} status={run.status} "
        f"turns={run.turns} ({run.seconds / 60:.1f} min)"
    )
    return run


# --------------------------------------------------------------------------- #
# the pool
# --------------------------------------------------------------------------- #


def run_pool(
    concepts: Sequence[str],
    *,
    reason: str,
    wave: str = "wave",
    mode: str = "replay",
    parallel: int = 4,
    artifact_root: Optional[str] = None,
    agent: str = DEFAULT_AGENT,
    model: Optional[str] = None,
    ledger_path: Optional[Union[str, Path]] = None,
    run_dir: Optional[Union[str, Path]] = None,
    spark_lock: Optional[str] = None,
    max_turns: int = 30,
    turn_timeout: float = 3600.0,
    concept_budget: float = 6 * 3600.0,
    invalidate_stage: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """Run *concepts* through the orchestrator loop, *parallel* at a time.

    Returns a process exit code: 0 when every concept reached a success status,
    1 otherwise.
    """
    if mode not in MODES:
        raise SystemExit(f"Unknown mode {mode!r}; expected one of {list(MODES)}")
    if parallel < 1:
        raise SystemExit("--parallel must be at least 1")
    if invalidate_stage and mode != "reopen":
        raise SystemExit("--invalidate-stage only applies to --mode reopen")

    project = Path(artifact_root or ".").resolve()
    base = Path(run_dir) if run_dir else project / DEFAULT_RUN_DIR / f"{wave}.goalrun"
    ledger = GoalLedger(
        Path(ledger_path) if ledger_path else base / "ledger.json",
        wave=wave,
        reason=reason,
        dry_run=dry_run,
    )
    lock_path = str(Path(os.path.expanduser(spark_lock or DEFAULT_SPARK_LOCK)))

    for concept in concepts:
        run = ledger.get(concept)
        if run.phase == "queued":
            run.mode = mode

    deps = _dependencies(concepts, artifact_root)

    _say("=" * 72)
    _say(f"goal pool '{wave}': {len(concepts)} concept(s), {parallel} at a time")
    _say(f"  mode        {mode}")
    _say(f"  agent       {agent}{' / ' + model if model else ' (agent default model)'}")
    _say(f"  run dir     {base}")
    _say(f"  ledger      {ledger.path}")
    _say(f"  spark lock  {lock_path}")
    if dry_run:
        _say("  DRY RUN -- nothing is opened, no session is started, no ledger written")
    _say("=" * 72)

    remaining = [c for c in concepts if not ledger.get(c).is_terminal]
    already = [c for c in concepts if ledger.get(c).is_terminal]
    if already:
        _say(f"  resuming: {len(already)} concept(s) already terminal in the ledger")

    def dependency_block(concept: str) -> Optional[str]:
        """The dependency that stops *concept* starting, if any.

        The test is "has this dependency finished *in this pool*", deliberately
        not "is it COMPLETED on disk right now".  Every concept in a replay wave
        is COMPLETED when the wave starts -- that is what makes it replayable --
        so a disk check would be vacuously true for all of them and a dependent
        would open before its dependency had been reopened at all.  It would then
        be measured against the dependency's *old* candidate, which is exactly
        the verdict the wave exists to invalidate.
        """
        for dep in sorted(deps.get(concept, ())):
            run = ledger.get(dep)
            if not run.is_terminal:
                return f"waiting for {dep}"
            if dry_run and run.outcome == "dry_run":
                continue
            if not run.succeeded:
                return f"{dep} did not succeed ({run.outcome}/{run.status})"
        return None

    running: Dict[Future, str] = {}
    exit_code = 0

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        while remaining or running:
            # Fill free slots with the earliest eligible concept.
            progressed = True
            while progressed and len(running) < parallel:
                progressed = False
                for concept in list(remaining):
                    blocker = dependency_block(concept)
                    if blocker is None:
                        remaining.remove(concept)
                        run = ledger.get(concept)
                        _say(f"  -> starting {concept}")
                        future = pool.submit(
                            _drive_concept,
                            run,
                            ledger=ledger,
                            reason=reason,
                            artifact_root=artifact_root,
                            agent=agent,
                            model=model,
                            run_dir=base,
                            project_dir=project,
                            spark_lock=lock_path,
                            max_turns=max_turns,
                            turn_timeout=turn_timeout,
                            concept_budget=concept_budget,
                            invalidate_stage=invalidate_stage,
                            dry_run=dry_run,
                        )
                        running[future] = concept
                        progressed = True
                        break

            if not running:
                # Nothing runs and nothing can start: everything left is waiting
                # on a dependency that will never land.
                for concept in remaining:
                    run = ledger.get(concept)
                    run.phase, run.outcome = "skipped", "dependency"
                    run.error = dependency_block(concept)
                    _say(f"  -- {concept}: skipped, {run.error}")
                ledger.flush()
                remaining = []
                break

            done, _pending = wait(list(running), return_when=FIRST_COMPLETED)
            for future in done:
                concept = running.pop(future)
                try:
                    future.result()
                except Exception as exc:  # a driver bug, not an agent outcome
                    run = ledger.get(concept)
                    run.phase, run.outcome = "terminal", "error"
                    run.error = f"driver error: {exc}"
                    ledger.flush()
                    _say(f"  [{concept}] !! driver error: {exc}")

    # --- report ------------------------------------------------------------ #
    rows = [ledger.get(c) for c in concepts]

    if dry_run:
        # No verdict exists, so say what the plan was rather than scoring it.
        started_order = [r.concept for r in rows if r.outcome == "dry_run"]
        never = [r for r in rows if r.outcome != "dry_run"]
        _say("\n" + "=" * 72)
        _say(f"DRY RUN of goal pool '{wave}': {len(rows)} concept(s) planned")
        _say(f"  would run, in this order: {' '.join(started_order)}")
        # Every dry worker finishes instantly, so this is the order concepts were
        # dispatched -- list order -- not a predicted schedule. In a real run a
        # dependent is held until its dependency reaches a success status.
        _say(
            "  (dispatch order, not a schedule: a real run holds a dependent "
            "until its dependency succeeds)"
        )
        if never:
            _say(f"  would NOT start ({len(never)}):")
            for r in never:
                _say(f"    {r.concept}: {r.error or r.outcome or 'blocked'}")
        _say(
            "  nothing was opened, no session ran, and no ledger was written -- "
            "drop --dry-run to run it"
        )
        _say("=" * 72)
        return 1 if never else 0

    ok = [r for r in rows if r.succeeded]
    blocked = [r for r in rows if r.status == "BLOCKED_REPRESENTATION"]
    failed = [r for r in rows if r.status == "FAILED"]
    unfinished = [r for r in rows if r.status not in TERMINAL_STATUSES]

    _say("\n" + "=" * 72)
    _say(f"goal pool '{wave}' finished: {len(rows)} concept(s)")
    _say(f"  succeeded ({len(ok)}): " + " ".join(r.concept for r in ok))
    if blocked:
        _say(f"  blocked ({len(blocked)}): " + " ".join(r.concept for r in blocked))
    if failed:
        _say(f"  FAILED ({len(failed)}): " + " ".join(r.concept for r in failed))
    if unfinished:
        _say(f"  not terminal ({len(unfinished)}) -- pick these up by hand:")
        for r in unfinished:
            _say(
                f"    /goal {r.concept}    # {r.outcome or 'never started'}"
                + (f": {r.error}" if r.error else "")
                + (f"  (session {r.session_id})" if r.session_id else "")
            )
        exit_code = 1
    if failed:
        exit_code = 1
    total = sum(r.seconds for r in rows)
    _say(f"  wall-clock across workers: {total / 3600:.1f} h of session time")
    _say(f"  ledger:     {ledger.path}")
    _say(f"  transcripts {base / 'sessions'}")
    _say("=" * 72)
    return exit_code
