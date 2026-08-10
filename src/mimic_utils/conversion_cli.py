"""Conversion-loop CLI for ``mimic_utils``.  Handlers return int exit codes.

Wire into ``__main__.py``::

    from mimic_utils.conversion_cli import register_commands
    register_commands(subparsers)

All expected domain exceptions (StateError, DAGError, DependencyError,
TransitionError) are caught in handlers and produce concise messages with
nonzero exit codes -- no tracebacks.

Commands
--------
  init CONCEPT [--artifact-root DIR]
  status [--artifact-root DIR] [--no-color] [--stale]
  start CONCEPT [--artifact-root DIR]
  validate-demo CONCEPT [--artifact-root DIR] [--counter C]
  validate-full CONCEPT [--artifact-root DIR] [--counter C]
  done CONCEPT [--artifact-root DIR] [--counter C]
  fail CONCEPT --error MSG [--artifact-root DIR] [--counter C]
  block CONCEPT --error MSG [--artifact-root DIR]
  accept-divergence CONCEPT --justification MSG [--by judge|human]
  skip CONCEPT [--artifact-root DIR] [--counter C]
  retry CONCEPT [--artifact-root DIR] [--force]
  resume CONCEPT [--apply] [--json] [--artifact-root DIR] [--force]
  carryover CONCEPT [--json] [--artifact-root DIR]
  carryover-record CONCEPT --stage S [--artifact-root DIR]
  carryover-invalidate CONCEPT --stage S --reason MSG [--artifact-root DIR]
  depcheck CONCEPT [--artifact-root DIR]
  metrics-finalize CONCEPT --run N --session-id ID [--session-id ID ...]
                  [--artifact-root DIR] [--opencode-db PATH]
  preflight [--duckdb PATH] [--no-color]
"""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Optional

from mimic_utils.conversion_state import (
    ConversionController,
    DAGError,
    DependencyError,
    StateError,
    TransitionError,
    format_age,
)
from mimic_utils.db_preflight import (
    format_report,
    run_preflight,
)
from mimic_utils.duckdb_oracle import (
    ENV_KEY as DUCKDB_ENV_KEY,
    resolve_duckdb_path,
)
from mimic_utils.resume import (
    CARRYOVER_STAGES,
    CarryoverStore,
    resume_plan,
)
from mimic_utils.conversion_metrics import finalize_conversion_metrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_run(func, *args, **kwargs):
    """Call *func* and return (message, exit_code).  Catch domain exceptions."""
    try:
        return func(*args, **kwargs)
    except TransitionError as e:
        return f"ERROR: {e}", 3
    except DependencyError as e:
        return f"ERROR: {e}", 2
    except DAGError as e:
        return f"ERROR: {e}", 2
    except StateError as e:
        return f"ERROR: {e}", 4


def _refuse_if_live(
    ctrl: ConversionController, concept: str, *, force: bool, action: str
) -> None:
    """Stop *action* from seizing a concept another terminal is still porting.

    Waves are composed by hand, so two sessions can hold the same concept name.
    `resume --apply` and `retry` are the two commands that would then fail a
    live attempt and open a new one, throwing away work in progress. Staleness
    is advisory everywhere else; this is the single place it decides something.
    """
    live = ctrl.liveness(concept)
    if live is None or force or live["stale"]:
        return
    raise StateError(
        f"Refusing to {action} '{concept}': it is {live['status']} and was "
        f"updated {format_age(live['age_seconds'])} ago, so another goal is "
        f"probably still porting it. Wait, or pass --force if you KNOW that "
        f"session is dead. --force is not for an error you have not diagnosed."
    )


# ---------------------------------------------------------------------------
# Command handlers -> (message: str, exit_code: int)
# ---------------------------------------------------------------------------


def cmd_init(concept: str, *, artifact_root: Optional[str] = None) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    st = ctrl.initialize(concept)
    return f"Initialised '{st.concept_name}' -> {st.status}", 0


def cmd_status(
    *,
    artifact_root: Optional[str] = None,
    no_color: bool = False,
    stale: bool = False,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    report = ctrl.status_report()
    return report.format(color=not no_color, stale_only=stale), 0


def cmd_start(
    concept: str,
    *,
    artifact_root: Optional[str] = None,
    force: bool = False,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    _refuse_if_live(ctrl, concept, force=force, action="start")
    st = ctrl.start(concept)
    return (
        f"Started '{st.concept_name}' (attempt {st.attempt}) "
        f"-> {st.status}\n"
        f"  attempt dir: {ctrl.attempt_dir(concept)}"
    ), 0


def cmd_transition(
    concept: str,
    target: str,
    *,
    artifact_root: Optional[str] = None,
    error_message: Optional[str] = None,
    justification: Optional[str] = None,
    decided_by: str = "judge",
    counter: Optional[str] = None,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    st = ctrl.transition(
        concept, target,
        error_message=error_message,
        justification=justification,
        decided_by=decided_by,
        counter=counter,
    )
    extras = []
    if counter:
        extras.append(f"{counter}_counter={getattr(st, f'{counter}_counter')}")
    msg = f"'{st.concept_name}' -> {st.status}"
    if extras:
        msg += f" ({', '.join(extras)})"
    if st.status == "COMPLETED_WITH_DIVERGENCE":
        msg += (
            f"\n  accepted by: {st.divergence_decided_by}"
            f"\n  accepted divergence: {st.divergence_justification}"
            f"\n  NOTE: this is not an exact match. Report it separately from "
            f"COMPLETED."
        )
        if st.divergence_decided_by == "human":
            msg += (
                "\n  NOTE: decided outside the loop. Report manual overrides "
                "separately from judge-accepted divergences too."
            )
    return msg, 0


def cmd_resume(
    concept: str,
    *,
    artifact_root: Optional[str] = None,
    apply: bool = False,
    as_json: bool = False,
    force: bool = False,
) -> tuple[str, int]:
    if apply:
        # Only `--apply` is gated. A read-only `resume` on a live concept is
        # exactly how a second terminal finds out it is a second terminal.
        _refuse_if_live(
            ConversionController(artifact_root=artifact_root),
            concept, force=force, action="resume --apply",
        )
    plan = resume_plan(concept, artifact_root=artifact_root, apply=apply)
    if as_json:
        import json as _json

        return _json.dumps(plan.to_dict(), indent=2, sort_keys=True), 0
    return plan.format(), 0


def cmd_carryover(
    concept: str,
    *,
    artifact_root: Optional[str] = None,
    as_json: bool = False,
) -> tuple[str, int]:
    store = CarryoverStore(artifact_root=artifact_root)
    rows = store.status(concept)
    if as_json:
        import json as _json

        return _json.dumps([r.to_dict() for r in rows], indent=2, sort_keys=True), 0
    lines = [f"Carryover for '{concept}' ({store.concept_dir(concept)})"]
    for r in rows:
        if r.fresh:
            mark = "reuse "
            detail = f"attempt {r.written_at_attempt}" if r.written_at_attempt else "unrecorded"
        elif r.present:
            mark = "RERUN "
            detail = f"invalidated: {r.invalidated_reason}"
        else:
            mark = "RERUN "
            detail = "absent"
        lines.append(f"  [{mark}] {r.stage:<22} {detail}")
    return "\n".join(lines), 0


def cmd_carryover_record(
    concept: str,
    *,
    stage: str,
    artifact_root: Optional[str] = None,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    state = ctrl._read_state(concept)  # noqa: SLF001 -- same package
    attempt = state.attempt if state else 0
    store = CarryoverStore(artifact_root=artifact_root)
    path = store.record(concept, stage, attempt)
    return f"Recorded carryover '{concept}/{stage}' (attempt {attempt}) -> {path}", 0


def cmd_carryover_invalidate(
    concept: str,
    *,
    stage: str,
    reason: str,
    artifact_root: Optional[str] = None,
) -> tuple[str, int]:
    store = CarryoverStore(artifact_root=artifact_root)
    store.invalidate(concept, stage, reason)
    return (
        f"Invalidated carryover '{concept}/{stage}'; it will re-run on the next "
        f"attempt.\n  reason: {reason}"
    ), 0


def cmd_depcheck(
    concept: str,
    *,
    artifact_root: Optional[str] = None,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    ready, missing = ctrl.dependency_ready(concept)
    if ready:
        return f"'{concept}' dependencies are met.", 0
    else:
        return f"'{concept}' has unmet dependencies: {missing}", 1


def cmd_preflight_runner(
    duckdb: Optional[str] = None,
    no_color: bool = False,
) -> tuple[str, int]:
    resolved = resolve_duckdb_path(duckdb)
    prefix = f"Opening {resolved} read-only ...\n"
    result = run_preflight(resolved)
    report = prefix + format_report(result, color=not no_color)
    return report, 0 if result.passed else 1


# ---------------------------------------------------------------------------
# Argparse handlers (print -> return exit code)
# ---------------------------------------------------------------------------

_Ec = int


def _h_init(concept: str, artifact_root: Optional[str] = None) -> _Ec:
    msg, code = _safe_run(cmd_init, concept, artifact_root=artifact_root)
    print(msg)
    return code


def _h_status(
    artifact_root: Optional[str] = None,
    no_color: bool = False,
    stale: bool = False,
) -> _Ec:
    msg, code = _safe_run(
        cmd_status, artifact_root=artifact_root, no_color=no_color, stale=stale
    )
    print(msg)
    return code


def _h_start(
    concept: str, artifact_root: Optional[str] = None, force: bool = False
) -> _Ec:
    msg, code = _safe_run(
        cmd_start, concept, artifact_root=artifact_root, force=force,
    )
    print(msg)
    return code


def _h_transition(target: str, default_counter: str = "engineering"):
    def handler(
        concept: str,
        artifact_root: Optional[str] = None,
        error: Optional[str] = None,
        justification: Optional[str] = None,
        by: str = "judge",
        counter: str = default_counter,
    ) -> _Ec:
        msg, code = _safe_run(
            cmd_transition, concept, target,
            artifact_root=artifact_root,
            error_message=error,
            justification=justification,
            decided_by=by,
            counter=counter,
        )
        print(msg)
        return code
    return handler


def _h_resume(
    concept: str,
    artifact_root: Optional[str] = None,
    apply: bool = False,
    json: bool = False,
    force: bool = False,
) -> _Ec:
    msg, code = _safe_run(
        cmd_resume, concept, artifact_root=artifact_root, apply=apply,
        as_json=json, force=force,
    )
    print(msg)
    return code


def _h_carryover(
    concept: str, artifact_root: Optional[str] = None, json: bool = False
) -> _Ec:
    msg, code = _safe_run(
        cmd_carryover, concept, artifact_root=artifact_root, as_json=json
    )
    print(msg)
    return code


def _h_carryover_record(
    concept: str, stage: str = "", artifact_root: Optional[str] = None
) -> _Ec:
    msg, code = _safe_run(
        cmd_carryover_record, concept, stage=stage, artifact_root=artifact_root
    )
    print(msg)
    return code


def _h_carryover_invalidate(
    concept: str,
    stage: str = "",
    reason: str = "",
    artifact_root: Optional[str] = None,
) -> _Ec:
    msg, code = _safe_run(
        cmd_carryover_invalidate, concept,
        stage=stage, reason=reason, artifact_root=artifact_root,
    )
    print(msg)
    return code


def _h_depcheck(concept: str, artifact_root: Optional[str] = None) -> _Ec:
    msg, code = _safe_run(cmd_depcheck, concept, artifact_root=artifact_root)
    print(msg)
    return code


def _h_preflight(duckdb: Optional[str] = None, no_color: bool = False) -> _Ec:
    msg, code = cmd_preflight_runner(duckdb=duckdb, no_color=no_color)
    print(msg)
    return code


def _h_metrics_finalize(
    concept: str,
    run: int,
    session_id: Optional[list[str]] = None,
    artifact_root: Optional[str] = None,
    opencode_db: Optional[str] = None,
) -> _Ec:
    """Finalize the terminal conversion metrics artifact."""
    try:
        path = finalize_conversion_metrics(
            concept,
            run=run,
            session_ids=session_id or [],
            artifact_root=artifact_root,
            opencode_db=opencode_db,
        )
        print(f"Wrote conversion metrics: {path}")
        return 0
    except (StateError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 4


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_commands(subparsers: _SubParsersAction) -> None:
    """Register conversion-loop sub-commands on an existing subparsers."""

    ar = dict(default=None, help="Artifact root directory (default: auto-detect from CWD).")

    # --- init -----------------------------------------------------------------
    p = subparsers.add_parser("init", help="Initialise a concept (DAG-validated).")
    p.add_argument("concept")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_init)

    # --- status ---------------------------------------------------------------
    p = subparsers.add_parser("status", help="Full DAG-wide conversion status.")
    p.add_argument("--artifact-root", **ar)
    p.add_argument("--no-color", action="store_true")
    p.add_argument(
        "--stale", action="store_true",
        help="List only active concepts past their staleness threshold — the "
             "loops that probably died and are silently blocking dependents.",
    )
    p.set_defaults(func=_h_status)

    # --- start ----------------------------------------------------------------
    p = subparsers.add_parser("start", help="Start a concept -> RUNNING.")
    p.add_argument("concept")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_start)

    # --- validate-demo --------------------------------------------------------
    p = subparsers.add_parser("validate-demo", help="-> VALIDATING_DEMO.")
    p.add_argument("concept")
    p.add_argument("--counter", default="engineering",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("VALIDATING_DEMO"))

    # --- validate-full --------------------------------------------------------
    p = subparsers.add_parser("validate-full", help="-> VALIDATING_FULL.")
    p.add_argument("concept")
    p.add_argument("--counter", default="hpc",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("VALIDATING_FULL"))

    # --- done -----------------------------------------------------------------
    p = subparsers.add_parser("done", help="-> COMPLETED.")
    p.add_argument("concept")
    p.add_argument("--counter", default="engineering",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("COMPLETED"))

    # --- accept-divergence ----------------------------------------------------
    # Separate command rather than `done --with-divergence`: the two are
    # different results, and a flag on `done` would be one keystroke away from
    # quietly promoting a divergent port to an exact match.
    p = subparsers.add_parser(
        "accept-divergence",
        help="-> COMPLETED_WITH_DIVERGENCE (a judge or a human accepted the "
             "divergence).",
    )
    p.add_argument("concept")
    p.add_argument(
        "--justification", required=True,
        help="The cited reason: the FHIR element or path that is missing, or "
             "the upstream mimic-fhir ETL statement that rewrote the value, "
             "and the divergence classes it explains.",
    )
    p.add_argument(
        "--by", default="judge", choices=["judge", "human"],
        help="Who decided. 'human' is a manual override and is the ONLY way to "
             "clear a BLOCKED_REPRESENTATION -- the judge is never called on a "
             "blocked concept, so recording that decision as the judge's would "
             "misattribute it. Reported separately in `status`.",
    )
    p.add_argument("--counter", default="semantic",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("COMPLETED_WITH_DIVERGENCE", "semantic"))

    # --- fail -----------------------------------------------------------------
    p = subparsers.add_parser("fail", help="-> FAILED.")
    p.add_argument("concept")
    p.add_argument("--error", default=None)
    p.add_argument("--counter", default="engineering",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("FAILED"))

    # --- blocked representability --------------------------------------------
    p = subparsers.add_parser(
        "block", help="-> BLOCKED_REPRESENTATION (human review required)."
    )
    p.add_argument("concept")
    p.add_argument("--error", required=True, help="Representability reason.")
    p.add_argument("--counter", default="semantic",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("BLOCKED_REPRESENTATION", "semantic"))

    # --- skip -----------------------------------------------------------------
    p = subparsers.add_parser("skip", help="-> SKIPPED (from PENDING only).")
    p.add_argument("concept")
    p.add_argument("--counter", default="engineering",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_transition("SKIPPED"))

    # --- retry ----------------------------------------------------------------
    p = subparsers.add_parser("retry", help="Retry a concept -> RUNNING.")
    p.add_argument("concept")
    p.add_argument("--artifact-root", **ar)
    p.add_argument(
        "--force", action="store_true",
        help="Proceed even though the concept still looks live. Only for a "
             "session you KNOW is dead — never for an undiagnosed error.",
    )
    p.set_defaults(func=_h_start)

    # --- resume ---------------------------------------------------------------
    p = subparsers.add_parser(
        "resume",
        help="Say which loop phase to re-enter; --apply performs the transitions.",
    )
    p.add_argument("concept")
    p.add_argument("--apply", action="store_true",
                   help="Perform the planned fail/start transitions.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--artifact-root", **ar)
    p.add_argument(
        "--force", action="store_true",
        help="Apply even though the concept still looks live. Only for a "
             "session you KNOW is dead — never for an undiagnosed error.",
    )
    p.set_defaults(func=_h_resume)

    # --- carryover ------------------------------------------------------------
    p = subparsers.add_parser(
        "carryover", help="Which analysis stages can be reused on the next attempt."
    )
    p.add_argument("concept")
    p.add_argument("--json", action="store_true")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_carryover)

    p = subparsers.add_parser(
        "carryover-record", help="Mark a written stage file as reusable."
    )
    p.add_argument("concept")
    p.add_argument("--stage", required=True, choices=list(CARRYOVER_STAGES))
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_carryover_record)

    p = subparsers.add_parser(
        "carryover-invalidate", help="Force a stage to re-run on the next attempt."
    )
    p.add_argument("concept")
    p.add_argument("--stage", required=True, choices=list(CARRYOVER_STAGES))
    p.add_argument("--reason", required=True,
                   help="Why the analysis was not trusted (recorded in the ledger).")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_carryover_invalidate)

    # --- depcheck -------------------------------------------------------------
    p = subparsers.add_parser("depcheck", help="Check dependency readiness.")
    p.add_argument("concept")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_depcheck)

    # --- preflight ------------------------------------------------------------
    p = subparsers.add_parser(
        "preflight", help="MIMIC-IV 2.2 demo DuckDB oracle preflight (read-only)."
    )
    p.add_argument("--duckdb", default=None,
                   help=f"DuckDB oracle path (default from ${DUCKDB_ENV_KEY}).")
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(func=_h_preflight)

    # --- deterministic conversion metrics ------------------------------------
    p = subparsers.add_parser(
        "metrics-finalize",
        help="Write the write-once terminal conversion metrics artifact.",
    )
    p.add_argument("concept")
    p.add_argument("--run", type=int, required=True, metavar="N")
    p.add_argument(
        "--session-id", action="append", required=True, metavar="ID",
        help="Root OpenCode session id; repeat for resumed/root session trees.",
    )
    p.add_argument("--artifact-root", **ar)
    p.add_argument(
        "--opencode-db", default=None,
        help="OpenCode SQLite database (default: ~/.local/share/opencode/opencode.db).",
    )
    p.set_defaults(func=_h_metrics_finalize)
