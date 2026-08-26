"""Conversion-loop CLI for ``mimic_utils``.  Handlers return int exit codes.

Wire into ``__main__.py``::

    from mimic_utils.conversion_cli import register_commands
    register_commands(subparsers)

All expected domain exceptions (StateError, DAGError, DependencyError,
TransitionError) are caught in handlers and produce concise messages with
nonzero exit codes -- no tracebacks.

Commands
--------
  export-mappings [--artifact-root DIR]
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
  reopen CONCEPT --reason MSG [--by human] [--force] [--artifact-root DIR]
  cast-probe CONCEPT --variant-sql PATH [--baseline-sql PATH] [--json]
  resume CONCEPT [--apply] [--json] [--artifact-root DIR] [--force]
  carryover CONCEPT [--json] [--artifact-root DIR]
  carryover-record CONCEPT --stage S [--artifact-root DIR]
  carryover-invalidate CONCEPT --stage S --reason MSG [--artifact-root DIR]
  depcheck CONCEPT [--artifact-root DIR]
  metrics-finalize [--artifact-root DIR]            (bare: rebuild SQL export)
  metrics-finalize CONCEPT --run N --session-id ID [--session-id ID ...]
                  [--artifact-root DIR] [--opencode-db PATH]
  metrics-report [--out PATH] [--rates PATH] [--artifact-root DIR]
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
from mimic_utils.export_mappings import export_mappings
from mimic_utils.replay import check_replay, replay
from mimic_utils.resume import (
    CARRYOVER_STAGES,
    CarryoverStore,
    resume_plan,
)
from mimic_utils.conversion_metrics import finalize_conversion_metrics
from mimic_utils.metrics_report import generate_metrics_report

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


def cmd_reopen(
    concept: str,
    *,
    reason: str,
    decided_by: str = "human",
    artifact_root: Optional[str] = None,
    force: bool = False,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    _refuse_if_live(ctrl, concept, force=force, action="reopen")
    previous = ctrl._read_state(concept)  # noqa: SLF001 -- same package
    superseded = previous.status if previous else "?"
    st = ctrl.reopen(concept, reason=reason, decided_by=decided_by)
    return (
        f"Reopened '{st.concept_name}' from {superseded} -> {st.status} "
        f"(attempt {st.attempt}, reopen #{st.reopen_count})\n"
        f"  attempt dir: {ctrl.attempt_dir(concept)}\n"
        f"  reason: {reason}\n"
        f"  NOTE: the superseded verdict is kept in reopen_history and cleared "
        f"from the live fields. This concept now has no verdict and must earn a "
        f"new one on full data.\n"
        f"  NOTE: metrics for this run are scoped to attempts > "
        f"{st.run_baseline['attempt']}; the previous run's artifact stands."
    ), 0


def cmd_replay(
    concept: str,
    *,
    reason: Optional[str] = None,
    decided_by: str = "human",
    artifact_root: Optional[str] = None,
    force: bool = False,
    check_only: bool = False,
    as_json: bool = False,
) -> tuple[str, int]:
    """Reopen a finished port and carry its SQL forward unchanged.

    ``--check`` is the read-only half and is what a wave should run first: every
    refusal it reports costs nothing, while the same refusal discovered after the
    reopen has already spent the verdict.
    """
    ctrl = ConversionController(artifact_root=artifact_root)
    if check_only:
        check = check_replay(concept, controller=ctrl)
        if as_json:
            import json as _json

            return _json.dumps(check.to_dict(), indent=2, sort_keys=True), (
                0 if check.replayable else 5
            )
        return check.format(), (0 if check.replayable else 5)

    _refuse_if_live(ctrl, concept, force=force, action="replay")
    if not (reason or "").strip():
        return (
            "ERROR: replay requires --reason: which upstream fix is being "
            "measured, and against which rebuilt warehouse."
        ), 4
    result = replay(concept, reason=reason, decided_by=decided_by, controller=ctrl)
    if as_json:
        import json as _json

        return _json.dumps(
            {
                "concept": result.concept,
                "attempt": result.attempt,
                "attempt_dir": str(result.attempt_dir),
                "source_attempt_dir": str(result.source_attempt_dir),
                "carried": result.carried,
                "cleared": result.cleared,
                "warnings": result.warnings,
            },
            indent=2,
            sort_keys=True,
        ), 0
    return result.format(), 0


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
        #
        # ...but gate it on whether `--apply` would actually DO anything. The
        # guard exists to stop a second terminal failing a live attempt and
        # opening a new one, i.e. throwing away work in progress. When the plan
        # lists no transitions, `--apply` performs none, so there is nothing to
        # seize and refusing protects nothing.
        #
        # This is not hypothetical: `reopen` stamps `updated_at` and leaves the
        # concept RUNNING with an empty attempt, and RUNNING goes stale after 45
        # minutes -- so every reopen blocked the very `/goal` it exists to set
        # up, for 45 minutes, on an attempt that by construction held no work.
        preview = resume_plan(concept, artifact_root=artifact_root, apply=False)
        if preview.transitions:
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


def _h_cast_probe(
    concept: str,
    variant_sql: str,
    baseline_sql: Optional[str] = None,
    artifact_root: Optional[str] = None,
    scratch_dir: Optional[str] = None,
    warehouse: Optional[str] = None,
    json: bool = False,
) -> _Ec:
    from mimic_utils.cast_probe import cmd_cast_probe

    msg, code = _safe_run(
        cmd_cast_probe, concept, variant_sql=variant_sql, baseline_sql=baseline_sql,
        artifact_root=artifact_root, scratch_dir=scratch_dir, warehouse=warehouse,
        as_json=json,
    )
    print(msg)
    return code


def _h_reopen(
    concept: str,
    reason: str,
    by: str = "human",
    artifact_root: Optional[str] = None,
    force: bool = False,
) -> _Ec:
    msg, code = _safe_run(
        cmd_reopen, concept, reason=reason, decided_by=by,
        artifact_root=artifact_root, force=force,
    )
    print(msg)
    return code


def _h_replay(
    concept: str,
    reason: Optional[str] = None,
    by: str = "human",
    artifact_root: Optional[str] = None,
    force: bool = False,
    check: bool = False,
    json: bool = False,
) -> _Ec:
    msg, code = _safe_run(
        cmd_replay, concept, reason=reason, decided_by=by,
        artifact_root=artifact_root, force=force, check_only=check,
        as_json=json,
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


def _h_validate_demo(
    concept: str,
    artifact_root: Optional[str] = None,
    counter: str = "engineering",
    skip_lint: bool = False,
    error: Optional[str] = None,
) -> _Ec:
    """Lint the attempt's SQL, then transition to VALIDATING_DEMO.

    The lint gates *this* transition rather than `run-demo` because this is the
    one that freezes the implementation artifacts. Gating the freeze means a
    resume that re-enters at the full-data leg cannot route around the check:
    the SQL it would run was already vetted on the way in.
    """
    from mimic_utils.sql_lint import format_findings, lint_attempt

    if not skip_lint:
        sql_path, findings = lint_attempt(concept, artifact_root=artifact_root)
        if findings:
            print(format_findings(concept, sql_path, findings))
            print()
            print(
                "REFUSED: not transitioning to VALIDATING_DEMO. Fix the SQL in this\n"
                "attempt, then run validate-demo again. A human may override with\n"
                "--skip-lint; no agent does."
            )
            return 1

    msg, code = _safe_run(
        cmd_transition, concept, "VALIDATING_DEMO",
        artifact_root=artifact_root,
        error_message=error,
        counter=counter,
    )
    print(msg)
    return code


def _h_lint_sql(concept: Optional[str] = None, artifact_root: Optional[str] = None) -> _Ec:
    """Report lint violations. Changes nothing; exits 1 if anything was found."""
    from mimic_utils.sql_lint import format_findings, lint_attempt
    from mimic_utils.conversion_state import ConversionController

    if concept:
        concepts = [concept]
    else:
        controller = ConversionController(artifact_root=artifact_root)
        concepts = sorted(controller.dag_concepts)

    total = 0
    for name in concepts:
        sql_path, findings = lint_attempt(name, artifact_root=artifact_root)
        if sql_path is None:
            continue
        total += len(findings)
        if findings or concept:
            print(format_findings(name, sql_path, findings))
    if not concept:
        print()
        print(f"sql-lint: {total} violation(s) across {len(concepts)} concept(s).")
    return 1 if total else 0


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
    concept: Optional[str] = None,
    run: Optional[int] = None,
    session_id: Optional[list[str]] = None,
    artifact_root: Optional[str] = None,
    opencode_db: Optional[str] = None,
) -> _Ec:
    """Finalize the terminal conversion metrics artifact.

    Bare (no CONCEPT): rebuild the canonical SQL export, wholesale overwriting
    the artifact directory -- the common case that needs no per-run scoping.
    """
    if concept is None:
        if run is not None or session_id:
            print("ERROR: --run/--session-id require a CONCEPT argument")
            return 2
        return _h_export_mappings(artifact_root=artifact_root)
    if run is None or not session_id:
        print("ERROR: CONCEPT requires --run N and at least one --session-id ID")
        return 2
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


def _h_metrics_report(
    out: Optional[str] = None,
    rates: Optional[str] = None,
    artifact_root: Optional[str] = None,
) -> _Ec:
    """Regenerate the self-contained HTML rollup of every metrics artifact."""
    try:
        path = generate_metrics_report(out=out, rates_path=rates, artifact_root=artifact_root)
        print(f"Wrote metrics report: {path}")
        return 0
    except (StateError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 4


def _h_export_mappings(artifact_root: Optional[str] = None) -> _Ec:
    """Rebuild the canonical-layout export of finalized concept bundles."""
    try:
        for line in export_mappings(artifact_root=artifact_root).summary():
            print(line)
        return 0
    except (StateError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 4


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_commands(subparsers: _SubParsersAction) -> None:
    """Register conversion-loop sub-commands on an existing subparsers."""

    ar = dict(default=None, help="Artifact root directory (default: auto-detect from CWD).")

    # --- finalized mapping export --------------------------------------------
    p = subparsers.add_parser(
        "export-mappings",
        help="Rebuild finalized concept SQL in the canonical concept layout.",
    )
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_export_mappings)

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
    p = subparsers.add_parser(
        "validate-demo",
        help="-> VALIDATING_DEMO (refuses on a concept.sql lint violation).",
    )
    p.add_argument("concept")
    p.add_argument("--counter", default="engineering",
                   choices=["semantic", "engineering", "hpc"])
    p.add_argument("--skip-lint", action="store_true",
                   help="Transition despite a lint violation. Human escape hatch; "
                        "no agent runs this.")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_validate_demo)

    # --- lint-sql -------------------------------------------------------------
    p = subparsers.add_parser(
        "lint-sql",
        help="Check attempt concept.sql for known defect classes (no state change).",
    )
    p.add_argument("concept", nargs="?",
                   help="Omit to sweep every concept's current attempt.")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_lint_sql)

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
             "clear a BLOCKED_REPRESENTATION -- the judge already returned "
             "blocked and is not called again to reconsider its own ruling. "
             "Reported separately in `status`.",
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

    # --- reopen ---------------------------------------------------------------
    # Separate from `retry` for the same reason `accept-divergence` is separate
    # from `done`: they are different acts. `retry` resumes an unfinished port;
    # this sets aside a finished one, and the flag that made it a one-keystroke
    # difference is exactly the flag that would get used by accident.
    p = subparsers.add_parser(
        "reopen",
        help="Set aside a COMPLETED / COMPLETED_WITH_DIVERGENCE / "
             "BLOCKED_REPRESENTATION verdict and start a new attempt "
             "(human only, reason required).",
    )
    p.add_argument("concept")
    p.add_argument(
        "--reason", required=True,
        help="What is wrong with the shipped SQL -- the construction being "
             "replaced and why it changes what the query means; or, on a "
             "BLOCKED_REPRESENTATION, what is wrong with the ruling. Recorded "
             "in reopen_history beside the verdict being superseded.",
    )
    p.add_argument(
        "--by", default="human", choices=["human"],
        help="Only a human reopens a recorded verdict. The choice is fixed and "
             "explicit so the record says who decided rather than leaving it "
             "to be inferred from a default.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Proceed even though the concept still looks live.",
    )
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_reopen)

    # --- replay ---------------------------------------------------------------
    # Separate from `reopen` because the two answer different questions and
    # `resume` gives them opposite instructions. `reopen` says "the SQL this port
    # shipped is defective, author a new one"; `replay` says "the SQL is fine,
    # the data under it was rebuilt, do not touch it". Collapsing them into one
    # verb with a flag would put the whole distinction in prose, and prose has
    # already failed at this once -- see `sql_lint`.
    p = subparsers.add_parser(
        "replay",
        help="Reopen a finished port and carry its concept.sql and "
             "ViewDefinitions forward byte-identical, to measure an upstream "
             "fix. No analysis, no implementer; re-enter at the demo gate.",
    )
    p.add_argument("concept")
    p.add_argument(
        "--reason", default=None,
        help="Which upstream fix is being measured and against which rebuilt "
             "warehouse. Recorded in reopen_history behind a "
             "'[replay:data_rebuild]' marker so a reader -- and `resume` -- can "
             "tell it from a defect reopen without parsing prose.",
    )
    p.add_argument(
        "--by", default="human", choices=["human"],
        help="Only a human sets aside a recorded verdict. A replay is a cheaper "
             "reopen, not a weaker one.",
    )
    p.add_argument(
        "--check", action="store_true",
        help="Report whether the concept is replayable and what would be "
             "carried, and change nothing. Exit 5 if it is not replayable. Run "
             "this over a whole wave first: a refusal found after the reopen has "
             "already spent the verdict.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Proceed even though the concept still looks live.",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_replay)

    # --- cast-probe -----------------------------------------------------------
    p = subparsers.add_parser(
        "cast-probe",
        help="Run two versions of a concept's SQL on demo data and report what "
             "the edit changed. Touches no state and consumes no attempt.",
    )
    p.add_argument("concept")
    p.add_argument(
        "--variant-sql", required=True,
        help="The proposed SQL. Compared against the current attempt's "
             "concept.sql unless --baseline-sql is given.",
    )
    p.add_argument("--baseline-sql", default=None)
    p.add_argument(
        "--scratch-dir", default=None,
        help="Where to stage the two throwaway attempt copies "
             "(default: <concept>/.cast_probe).",
    )
    p.add_argument("--warehouse", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_cast_probe)

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
        help="Bare: rebuild the SQL artifact export. With CONCEPT --run/"
             "--session-id: write the write-once conversion metrics artifact.",
    )
    p.add_argument("concept", nargs="?", default=None)
    p.add_argument("--run", type=int, default=None, metavar="N")
    p.add_argument(
        "--session-id", action="append", metavar="ID",
        help="Root OpenCode session id; repeat for resumed/root session trees.",
    )
    p.add_argument("--artifact-root", **ar)
    p.add_argument(
        "--opencode-db", default=None,
        help="OpenCode SQLite database (default: ~/.local/share/opencode/opencode.db).",
    )
    p.set_defaults(func=_h_metrics_finalize)

    # --- metrics rollup report ------------------------------------------------
    p = subparsers.add_parser(
        "metrics-report",
        help="Regenerate the self-contained HTML rollup of every metrics artifact.",
    )
    p.add_argument(
        "--out", default=None, metavar="PATH",
        help="Output HTML file (default: <artifact-root>/mimic-iv/concepts_fhir/metrics/index.html).",
    )
    p.add_argument(
        "--rates", default=None, metavar="PATH",
        help="Pricing table (default: <artifact-root>/mimic-iv/concepts_fhir/metrics/rates.json). "
             "Cost columns are omitted when it is missing or unreadable.",
    )
    p.add_argument("--artifact-root", **ar)
    p.set_defaults(func=_h_metrics_report)
