"""Conversion-loop CLI for ``mimic_utils``.  Handlers return int exit codes.

Wire into ``__main__.py``::

    from mimic_utils.conversion_cli import register_commands
    register_commands(subparsers)

All expected domain exceptions (StateError, DAGError, DependencyError,
TransitionError, ConcurrencyError) are caught in handlers and produce
concise messages with nonzero exit codes -- no tracebacks.

Commands
--------
  init CONCEPT [--artifact-root DIR]
  status [--artifact-root DIR] [--no-color]
  start CONCEPT [--artifact-root DIR]
  validate-demo CONCEPT [--artifact-root DIR] [--counter C]
  validate-full CONCEPT [--artifact-root DIR] [--counter C]
  done CONCEPT [--artifact-root DIR] [--counter C]
  fail CONCEPT --error MSG [--artifact-root DIR] [--counter C]
  block CONCEPT --error MSG [--artifact-root DIR]
  skip CONCEPT [--artifact-root DIR] [--counter C]
  retry CONCEPT [--artifact-root DIR]
  depcheck CONCEPT [--artifact-root DIR]
  preflight [--duckdb PATH] [--no-color]
  preflight-fhir [--base-url URL] [--duckdb PATH] [--no-color]
"""

from __future__ import annotations

from argparse import _SubParsersAction
from typing import Optional

from mimic_utils.conversion_state import (
    ConcurrencyError,
    ConversionController,
    DAGError,
    DependencyError,
    StateError,
    TransitionError,
)
from mimic_utils.db_preflight import (
    format_report,
    run_preflight,
)
from mimic_utils.duckdb_oracle import (
    ENV_KEY as DUCKDB_ENV_KEY,
    resolve_duckdb_path,
)
from mimic_utils.pathling import BASE_URL_ENV_KEY
from mimic_utils.preflight_fhir import (
    format_fhir_report,
    run_preflight_fhir as _run_preflight_fhir,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_run(func, *args, **kwargs):
    """Call *func* and return (message, exit_code).  Catch domain exceptions."""
    try:
        return func(*args, **kwargs)
    except ConcurrencyError as e:
        return f"ERROR: {e}", 3
    except TransitionError as e:
        return f"ERROR: {e}", 3
    except DependencyError as e:
        return f"ERROR: {e}", 2
    except DAGError as e:
        return f"ERROR: {e}", 2
    except StateError as e:
        return f"ERROR: {e}", 4


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
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    report = ctrl.status_report()
    return report.format(color=not no_color), 0


def cmd_start(
    concept: str,
    *,
    artifact_root: Optional[str] = None,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
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
    counter: Optional[str] = None,
) -> tuple[str, int]:
    ctrl = ConversionController(artifact_root=artifact_root)
    st = ctrl.transition(concept, target, error_message=error_message, counter=counter)
    extras = []
    if counter:
        extras.append(f"{counter}_counter={getattr(st, f'{counter}_counter')}")
    msg = f"'{st.concept_name}' -> {st.status}"
    if extras:
        msg += f" ({', '.join(extras)})"
    return msg, 0


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


def _h_status(artifact_root: Optional[str] = None, no_color: bool = False) -> _Ec:
    msg, code = _safe_run(
        cmd_status, artifact_root=artifact_root, no_color=no_color
    )
    print(msg)
    return code


def _h_start(concept: str, artifact_root: Optional[str] = None) -> _Ec:
    msg, code = _safe_run(
        cmd_start, concept, artifact_root=artifact_root,
    )
    print(msg)
    return code


def _h_transition(target: str, default_counter: str = "engineering"):
    def handler(
        concept: str,
        artifact_root: Optional[str] = None,
        error: Optional[str] = None,
        counter: str = default_counter,
    ) -> _Ec:
        msg, code = _safe_run(
            cmd_transition, concept, target,
            artifact_root=artifact_root,
            error_message=error,
            counter=counter,
        )
        print(msg)
        return code
    return handler


def _h_depcheck(concept: str, artifact_root: Optional[str] = None) -> _Ec:
    msg, code = _safe_run(cmd_depcheck, concept, artifact_root=artifact_root)
    print(msg)
    return code


def _h_preflight(duckdb: Optional[str] = None, no_color: bool = False) -> _Ec:
    msg, code = cmd_preflight_runner(duckdb=duckdb, no_color=no_color)
    print(msg)
    return code


def _h_preflight_fhir(
    base_url: Optional[str] = None,
    duckdb: Optional[str] = None,
    no_color: bool = False,
) -> _Ec:
    """Handler for ``preflight-fhir``."""
    import logging
    try:
        result = _run_preflight_fhir(fhir_base_url=base_url, duckdb_path=duckdb)
        print(format_fhir_report(result, color=not no_color))
        return 0 if result.passed else 1
    except Exception as exc:
        logging.error("preflight-fhir failed: %s", exc)
        return 1


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
    p.set_defaults(func=_h_start)

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

    # --- preflight-fhir -------------------------------------------------------
    p = subparsers.add_parser(
        "preflight-fhir",
        help="MIMIC-on-FHIR / Pathling integration preflight.",
    )
    p.add_argument(
        "--base-url", default=None,
        help=f"Pathling FHIR server base URL (default from ${BASE_URL_ENV_KEY}).",
    )
    p.add_argument(
        "--duckdb", default=None,
        help=f"DuckDB oracle path (default from ${DUCKDB_ENV_KEY}).",
    )
    p.add_argument("--no-color", action="store_true")
    p.set_defaults(func=_h_preflight_fhir)
