from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import sys
from pathlib import Path

from mimic_utils.compare_concepts import compare_concepts
from mimic_utils.compare_port_results import (
    EXIT_FAIL,
    EXIT_PASS,
    EXIT_UNSURE,
    compare_full,
    compare_shape,
    write_comparison,
)
import mimic_utils.compare_port_results as _cpr
import mimic_utils.oracle_manifest as _oracle_manifest_module
from mimic_utils.concept_dag import concept_dag_check, concept_dag_generate
from mimic_utils.conversion_cli import register_commands as _register_conversion_commands
from mimic_utils.demo_runner import format_demo_report, run_demo
from mimic_utils.duckdb_oracle import ENV_KEY as DUCKDB_ENV_KEY
from mimic_utils.export_oracle import export_oracle
from mimic_utils.transpile import transpile_file, transpile_folder


#: Kept in step with mimic_utils.goal_pool.MODES, which is asserted by the tests.
#: Duplicated rather than imported so building the parser does not pull in the
#: pool's threading/subprocess machinery on every CLI invocation.
_GOAL_MODES = ("replay", "reopen", "none")


def _parse_schema_map(value: str) -> dict:
    """Parse ``old=new,old2=new2`` into a dict for schema renaming."""
    schema_map = {}
    for pair in value.split(","):
        pair = pair.strip()
        if not pair:
            continue
        old, sep, new = pair.partition("=")
        if not sep or not old or not new:
            raise ValueError(f"Invalid schema mapping: {pair!r} (expected old=new)")
        schema_map[old.strip()] = new.strip()
    return schema_map


def _add_transpile_options(parser):
    parser.add_argument(
        "--derived_schema", default="mimiciv_derived",
        help="Schema in which the derived concept tables are created (e.g. mimiciii_derived)."
    )
    parser.add_argument(
        "--schema_map", type=_parse_schema_map, default=None, metavar="OLD=NEW[,OLD=NEW...]",
        help="Rename source schemas, e.g. mimiciii_clinical=mimiciii,mimiciii_notes=mimiciii."
    )


def _concept_dag_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils concept_dag``."""
    concepts_dir = kwargs.get("concepts_dir")
    output_dir = kwargs.get("output_dir")
    check = kwargs.get("check", False)

    if check:
        ok = concept_dag_check(concepts_dir, output_dir)
        return 0 if ok else 1
    else:
        concept_dag_generate(concepts_dir, output_dir)
        return 0


def _export_oracle_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils export-oracle``."""
    import logging
    try:
        out = export_oracle(
            concept=kwargs["concept"],
            output_path=kwargs["output"],
            duckdb_path=kwargs.get("duckdb"),
            dataset=kwargs.get("dataset", "demo"),
        )
        logging.info("Oracle artifact written: %s", out)
        return 0
    except Exception as exc:
        logging.error("export-oracle failed: %s", exc)
        return 1


def _register_derived_concepts_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils register-derived-concepts``.

    Imports inside the function so that the whole CLI keeps working on a machine
    with none of the ``upload`` extras installed -- the same reason the embedded
    Pathling runner is gated.  Exit codes: 2 for anything that stops the run
    before it starts, 1 for a failed write or a read-back mismatch, 0 otherwise.
    """
    import logging

    try:
        from mimic_utils.artifact_upload import (
            RegistrationError,
            register_derived_concepts,
        )
        from mimic_utils.pathling_config import ConfigError
    except ImportError as exc:
        logging.error(
            "register-derived-concepts needs the upload extras: "
            "pip install -e '.[upload]' (%s)", exc,
        )
        return 2

    concepts = kwargs.get("concepts") or ()
    every = kwargs.get("every", False)
    if not concepts and not every:
        logging.error("name at least one concept, or pass --all")
        return 2
    if concepts and every:
        logging.error("--all registers everything; do not also name concepts")
        return 2

    try:
        return register_derived_concepts(
            concepts,
            every=every,
            env_name=kwargs.get("env_name"),
            config_path=kwargs.get("config_path"),
            artifact_root=kwargs.get("artifact_root"),
            dry_run=kwargs.get("dry_run", False),
        )
    except ConfigError as exc:
        logging.error("cannot reach a Pathling server: %s", exc)
        return 2
    except RegistrationError as exc:
        logging.error("registration failed: %s", exc)
        return 1


def _compare_port_results_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils compare-port-results``.

    Exit codes: 0 pass, 1 fail, 2 neither -- covering both `unsure` (demo shape
    gate with 0 rows) and `review` (full data, any tier). A `review` is the
    judge's to decide and must not read as a failure.
    """
    import logging

    mode = kwargs["mode"]
    try:
        declaration = kwargs.get("unrepresentable")
        declared = _cpr.load_unrepresentable(declaration) if declaration else None
        if mode == "shape":
            if declared:
                logging.error("--unrepresentable applies to mode 'full' only")
                return EXIT_FAIL
            result = compare_shape(
                kwargs["concept"], kwargs["manifest"], kwargs["candidate"]
            )
        else:
            if not kwargs.get("oracle"):
                logging.error("--oracle is required for mode 'full'")
                return EXIT_FAIL
            result = compare_full(
                kwargs["concept"],
                kwargs["manifest"],
                kwargs["oracle"],
                kwargs["candidate"],
                schema=kwargs.get("schema") or "mimiciv_derived",
                rtol=kwargs.get("rtol", _cpr.DEFAULT_RTOL),
                atol=kwargs.get("atol", _cpr.DEFAULT_ATOL),
                sample_limit=kwargs.get("sample_limit", _cpr.DEFAULT_SAMPLE_LIMIT),
                unrepresentable=declared,
            )
    except Exception as exc:  # noqa: BLE001
        logging.error("compare-port-results failed: %s", exc)
        return EXIT_FAIL

    out = write_comparison(result, kwargs["output"])
    logging.info("Comparison artifact written: %s", out)
    # Shared with `compare_port_results_cli` rather than reimplemented. The copy
    # that used to live here had no `review` branch, so every `review` fell
    # through to EXIT_FAIL.
    return _cpr.report_verdict(result)


def _replay_run_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils replay-run`` (a whole wave, no agent)."""
    from mimic_utils.replay_batch import STAGES, run_wave

    concepts = list(kwargs.get("concepts") or ())
    if not concepts:
        logging.error("name at least one concept")
        return 2
    return run_wave(
        concepts,
        reason=kwargs["reason"],
        wave=kwargs.get("wave") or "wave",
        artifact_root=kwargs.get("artifact_root"),
        ledger_path=kwargs.get("ledger"),
        stages=kwargs.get("stages") or STAGES,
        dry_run=kwargs.get("dry_run", False),
    )


def _goal_run_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils goal-run`` (a wave of real sessions, k at a time)."""
    from mimic_utils.goal_pool import DEFAULT_AGENT, run_pool, wave_concepts

    wave = kwargs.get("wave")
    concepts = list(kwargs.get("concepts") or ())
    if concepts and wave:
        logging.error("name concepts or pass --wave, not both")
        return 2
    if wave:
        concepts = wave_concepts(wave, root=kwargs.get("artifact_root"))
    if not concepts:
        logging.error("name at least one concept, or pass --wave")
        return 2

    return run_pool(
        concepts,
        reason=kwargs["reason"],
        # Names the ledger and its directory, so it must read well: a
        # wave-less run over the combined list is "all", not "goalrun.goalrun".
        # --name lets a caller that had to pass concepts explicitly keep the
        # wave's bookkeeping anyway.
        wave=kwargs.get("name") or wave or "all",
        mode=kwargs.get("mode") or "replay",
        parallel=kwargs.get("parallel") or 4,
        artifact_root=kwargs.get("artifact_root"),
        agent=kwargs.get("agent") or DEFAULT_AGENT,
        model=kwargs.get("model"),
        ledger_path=kwargs.get("ledger"),
        run_dir=kwargs.get("run_dir"),
        spark_lock=kwargs.get("spark_lock"),
        max_turns=kwargs.get("max_turns") or 30,
        turn_timeout=kwargs.get("turn_timeout") or 3600.0,
        concept_budget=kwargs.get("concept_budget") or 6 * 3600.0,
        invalidate_stage=kwargs.get("invalidate_stage"),
        dry_run=kwargs.get("dry_run", False),
    )


def _run_demo_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils run-demo`` (the demo shape gate).

    Exit codes: 0 shape_ok, 1 shape_fail/error, 2 unsure (0 rows -- neither a
    pass nor a failure; proceed to full data).
    """
    import logging
    try:
        result = run_demo(
            concept=kwargs["concept"],
            attempt_dir=kwargs.get("attempt_dir"),
            manifest_path=kwargs.get("manifest"),
            artifact_root=kwargs.get("artifact_root"),
            attempt=kwargs.get("attempt"),
            skip_compare=kwargs.get("skip_compare", False),
            warehouse=kwargs.get("warehouse"),
        )
        print(format_demo_report(result, color=not kwargs.get("no_color", False)))
        if result.blocked:
            return 1
        if result.verdict == "unsure":
            return EXIT_UNSURE
        return 0 if result.may_proceed_to_full else 1
    except Exception as exc:
        logging.error("run-demo failed: %s", exc)
        return 1


def _run_full_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils run-full`` (the full-data correctness gate).

    Exit codes: 0 match, 1 mismatch or error. Unlike the demo gate there is no
    'unsure': full data decides.
    """
    import logging
    from mimic_utils.full_runner import format_full_report, run_full

    try:
        result = run_full(
            concept=kwargs["concept"],
            attempt_dir=kwargs.get("attempt_dir"),
            attempt=kwargs.get("attempt"),
            warehouse=kwargs.get("warehouse"),
            oracle=kwargs.get("oracle"),
            manifest_path=kwargs.get("manifest"),
            artifact_root=kwargs.get("artifact_root"),
            schema=kwargs.get("schema") or "mimiciv_derived",
            rtol=kwargs.get("rtol", 0.001),
            atol=kwargs.get("atol", 1e-9),
            sample_limit=kwargs.get("sample_limit", 20),
        )
        print(format_full_report(result, color=not kwargs.get("no_color", False)))
        return 0 if result.matched else 1
    except Exception as exc:
        logging.error("run-full failed: %s", exc)
        return 1


def _hpc_launch_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils hpc-launch``."""
    from mimic_utils.hpc import hpc_launch_cli

    argv = [kwargs["concept"]]
    for flag in ("attempt_dir", "artifact_root", "walltime"):
        value = kwargs.get(flag)
        if value:
            argv += [f"--{flag.replace('_', '-')}", str(value)]
    if kwargs.get("attempt") is not None:
        argv += ["--attempt", str(kwargs["attempt"])]
    if kwargs.get("skip_smoke"):
        argv.append("--skip-smoke")
    return hpc_launch_cli(argv)


def _hpc_poll_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils hpc-poll``."""
    from mimic_utils.hpc import hpc_poll_cli

    argv = [kwargs["concept"]]
    for flag in ("attempt_dir", "artifact_root", "job_id"):
        value = kwargs.get(flag)
        if value:
            argv += [f"--{flag.replace('_', '-')}", str(value)]
    if kwargs.get("attempt") is not None:
        argv += ["--attempt", str(kwargs["attempt"])]
    if kwargs.get("interval") is not None:
        argv += ["--interval", str(kwargs["interval"])]
    if kwargs.get("max_polls") is not None:
        argv += ["--max-polls", str(kwargs["max_polls"])]
    return hpc_poll_cli(argv)


def _oracle_manifest_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils oracle-manifest``."""
    argv = [
        "--db", str(kwargs["db"]),
        "--output", str(kwargs["output"]),
        "--schema", kwargs.get("schema") or "mimiciv_derived",
        "--dataset", kwargs["dataset"],
        "--max-key-cols", str(kwargs.get("max_key_cols", 3)),
        "--threads", str(kwargs.get("threads", 8)),
        "--memory-limit", kwargs.get("memory_limit") or "16GB",
    ]
    if kwargs.get("skip_hash"):
        argv.append("--skip-hash")
    if kwargs.get("force"):
        argv.append("--force")
    return _oracle_manifest_module.main(argv)


def main():
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO
    )
    parser = ArgumentParser(description="Convert SQL to different dialects.")
    subparsers = parser.add_subparsers()

    file_parser = subparsers.add_parser('convert_file', help='Transpile a single SQL file.')
    file_parser.add_argument("source_file", help="Source file.")
    file_parser.add_argument("destination_file", help="Destination file.")
    file_parser.add_argument("--source_dialect", choices=["bigquery", "postgres", "duckdb"], default='bigquery', help="SQL dialect to transpile.")
    file_parser.add_argument("--destination_dialect", choices=["bigquery", "postgres", "duckdb"], default='postgres', help="SQL dialect to transpile.")
    _add_transpile_options(file_parser)
    file_parser.set_defaults(func=transpile_file)

    folder_parser = subparsers.add_parser('convert_folder', help='Transpile all SQL files in a folder.')
    folder_parser.add_argument("source_folder", help="Source folder.")
    folder_parser.add_argument("destination_folder", help="Destination folder.")
    folder_parser.add_argument("--source_dialect", choices=["bigquery", "postgres", "duckdb"], default='bigquery', help="SQL dialect to transpile.")
    folder_parser.add_argument("--destination_dialect", choices=["bigquery", "postgres", "duckdb"], default="postgres", help="SQL dialect to transpile.")
    _add_transpile_options(folder_parser)
    folder_parser.add_argument(
        "--exclude", nargs="*", default=None, metavar="SUBFOLDER",
        help="Sub-folder names to skip (e.g. cookbook other-languages)."
    )
    folder_parser.set_defaults(func=transpile_folder)

    compare_parser = subparsers.add_parser(
        'compare_concepts',
        help='Compare derived concepts across PostgreSQL and DuckDB.',
        description=compare_concepts.__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    compare_parser.add_argument("--pg", required=True, help="libpq connection string for PostgreSQL")
    compare_parser.add_argument("--duckdb", dest="duckdb_path", required=True, help="path to the DuckDB database file")
    compare_parser.add_argument("--schema", default="mimiciv_derived")
    compare_parser.add_argument("--rtol", type=float, default=1e-6, help="relative tolerance for numeric comparison")
    compare_parser.add_argument("--atol", type=float, default=1e-9, help="absolute tolerance for numeric comparison")
    compare_parser.add_argument("--ignore", default="", help="comma-separated tables to skip")
    compare_parser.set_defaults(func=compare_concepts)

    dag_parser = subparsers.add_parser(
        "concept_dag",
        help="Generate / check the deterministic static concept DAG.",
        description=(
            "Recursively discover canonical mimic-iv/concepts SQL, parse "
            "BigQuery dependencies via sqlglot, and emit a deterministic DAG "
            "as JSON and Markdown."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    dag_parser.add_argument(
        "--concepts-dir",
        default=None,
        help="Path to concepts directory (default: mimic-iv/concepts).",
    )
    dag_parser.add_argument(
        "--output-dir",
        default=None,
        help="Path to output directory for artifacts (default: mimic-iv/concept_dag).",
    )
    dag_parser.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Verify generated DAG against stored artifact; exit non-zero on mismatch.",
    )
    dag_parser.set_defaults(func=_concept_dag_command)

    # -- concept-port oracle export / comparison commands --
    export_parser = subparsers.add_parser(
        "export-oracle",
        help="Export a mimiciv_derived concept table to a deterministic JSON oracle artifact.",
        description=export_oracle.__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    export_parser.add_argument(
        "concept",
        help="Concept stem (e.g. acei). Must be in the concept DAG.",
    )
    export_parser.add_argument(
        "--output", required=True, metavar="PATH",
        help="JSON artifact output path (must not exist — write-once).",
    )
    export_parser.add_argument(
        "--duckdb", default=None,
        help=(
            f"DuckDB oracle path (default: ${DUCKDB_ENV_KEY} or built-in). "
            "Always opened read-only."
        ),
    )
    export_parser.add_argument(
        "--dataset", default="demo",
        help="Human-readable dataset label recorded in the artifact (default: demo).",
    )
    export_parser.set_defaults(func=_export_oracle_command)

    compare_port_parser = subparsers.add_parser(
        "compare-port-results",
        help="Compare a candidate port against the oracle (shape gate or keyed diff).",
        description=_cpr.__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    compare_port_parser.add_argument(
        "mode", choices=("shape", "full"),
        help="shape = demo gate (columns/types only, row count not gated); "
             "full = correctness gate (schema identity + classified keyed "
             "diff; row count reported, not gated).",
    )
    compare_port_parser.add_argument(
        "--concept", required=True, metavar="NAME",
        help="Concept stem, e.g. 'age'.",
    )
    compare_port_parser.add_argument(
        "--manifest", required=True, metavar="PATH",
        help="Oracle manifest JSON (mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json).",
    )
    compare_port_parser.add_argument(
        "--candidate", required=True, metavar="PATH",
        help="Candidate result. Both runners write Parquet, so this is normally "
             "a '<dir>/*.parquet' glob over the Spark part-files; .ndjson and "
             ".csv are accepted but have their types inferred, not carried.",
    )
    compare_port_parser.add_argument(
        "--output", required=True, metavar="PATH",
        help="Comparison JSON output path (must not exist — write-once).",
    )
    compare_port_parser.add_argument(
        "--oracle", metavar="PATH",
        help="Oracle DuckDB file. Required for mode 'full'; opened read-only.",
    )
    compare_port_parser.add_argument(
        "--unrepresentable", metavar="PATH",
        help=f"Attempt's {_cpr.UNREPRESENTABLE_FILENAME}: a JSON object mapping "
             "column name to a justification, for columns MIMIC-on-FHIR cannot "
             "represent at all. Each is verified to be 100%% NULL in the "
             "candidate; a declared column that holds values is a blocking "
             "failure. Mode 'full' only.",
    )
    compare_port_parser.add_argument(
        "--schema", default="mimiciv_derived",
        help="Oracle schema holding the derived concepts (default: mimiciv_derived).",
    )
    compare_port_parser.add_argument(
        "--rtol", type=float, default=_cpr.DEFAULT_RTOL,
        help="Relative tolerance for floating-point VALUES (default: 0.001 = 0.1%%). "
             "Never applies to row count.",
    )
    compare_port_parser.add_argument(
        "--atol", type=float, default=_cpr.DEFAULT_ATOL,
        help="Absolute tolerance for near-zero floating-point values.",
    )
    compare_port_parser.add_argument(
        "--sample-limit", type=int, default=_cpr.DEFAULT_SAMPLE_LIMIT,
        help="Rows of each mismatch class to sample (default: 20; 0 disables).",
    )
    compare_port_parser.set_defaults(func=_compare_port_results_command)

    run_demo_parser = subparsers.add_parser(
        "run-demo",
        help="Execute a concept-port attempt on local Pathling and check its SHAPE.",
        description=(
            "Execute the attempt's ViewDefinitions and concept.sql over the "
            "local demo Delta warehouse via embedded Pathling on Spark — the "
            "same engine the HPC full run uses — and check the result's SHAPE "
            "against the oracle manifest.\n\n"
            "This is a cheap gate, not a correctness gate: it catches execution "
            "failure, wrong column names and incompatible types. Row count is NOT "
            "gated, and 0 rows yields 'unsure' (exit 2) rather than a failure -- "
            "the demo cohort legitimately contains nothing for some concepts.\n\n"
            "Exit codes: 0 shape_ok, 1 shape_fail/error, 2 unsure."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    run_demo_parser.add_argument("concept", help="Concept stem (e.g. age).")
    run_demo_parser.add_argument(
        "--attempt-dir", default=None,
        help="Attempt directory (default: the concept's current attempt).",
    )
    run_demo_parser.add_argument(
        "--attempt", type=int, default=None,
        help="Explicit attempt number instead of the current one.",
    )
    run_demo_parser.add_argument(
        "--manifest", default=None,
        help="Oracle manifest JSON (default: oracle_manifest.full.json).",
    )
    run_demo_parser.add_argument(
        "--artifact-root", default=None, help="Artifact root directory.",
    )
    run_demo_parser.add_argument(
        "--skip-compare", action="store_true",
        help="Write the candidate result only; do not run the shape gate.",
    )
    run_demo_parser.add_argument(
        "--warehouse", default=None,
        help="Demo Delta warehouse (env: MIMIC_FHIR_WAREHOUSE).",
    )
    run_demo_parser.add_argument("--no-color", action="store_true")
    run_demo_parser.set_defaults(func=_run_demo_command)

    run_full_parser = subparsers.add_parser(
        "run-full",
        help="Execute a concept-port attempt on FULL data and run the keyed diff.",
        description=(
            "Execute the attempt on full MIMIC-on-FHIR via embedded Pathling "
            "and compare it against the immutable full oracle. This is the "
            "correctness gate: column schema identity and the classified keyed "
            "row-level diff. Row count is reported, never gated.\n\n"
            "Normally invoked by the Slurm job on an HPC compute node, where "
            "the warehouse and the oracle are both node-local.\n\n"
            "Exit codes: 0 match, 1 mismatch or error, 2 review (the judge "
            "decides). Never read a non-zero exit as failure: 2 means the run "
            "succeeded and the port may well be correct."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    run_full_parser.add_argument("concept", help="Concept stem (e.g. age).")
    run_full_parser.add_argument(
        "--attempt-dir", default=None,
        help="Attempt directory (default: the concept's current attempt).",
    )
    run_full_parser.add_argument(
        "--attempt", type=int, default=None,
        help="Explicit attempt number instead of the current one.",
    )
    run_full_parser.add_argument(
        "--warehouse", default=None,
        help="Full Delta warehouse path (env: MIMIC_FHIR_WAREHOUSE).",
    )
    run_full_parser.add_argument(
        "--oracle", default=None,
        help="Full oracle DuckDB file, opened read-only (env: MIMIC_FULL_ORACLE).",
    )
    run_full_parser.add_argument(
        "--manifest", default=None,
        help="Oracle manifest JSON (default: oracle_manifest.full.json).",
    )
    run_full_parser.add_argument(
        "--artifact-root", default=None, help="Artifact root directory.",
    )
    run_full_parser.add_argument("--schema", default="mimiciv_derived")
    run_full_parser.add_argument(
        "--rtol", type=float, default=0.001,
        help="Relative tolerance for floating-point VALUES (never row count).",
    )
    run_full_parser.add_argument("--atol", type=float, default=1e-9)
    run_full_parser.add_argument("--sample-limit", type=int, default=20)
    run_full_parser.add_argument("--no-color", action="store_true")
    run_full_parser.set_defaults(func=_run_full_command)

    replay_run_parser = subparsers.add_parser(
        "replay-run",
        help="Run a wave of replays end to end with no agent in the loop.",
        description=(
            "For each named concept: replay (reopen + carry the port forward "
            "byte-identical), validate-demo, run-demo, validate-full, "
            "hpc-launch. The whole wave is queued before any polling, then each "
            "job is polled and every `match` is promoted to COMPLETED.\n\n"
            "Concepts that come back `review` or `mismatch` are left exactly "
            "where they are and listed at the end as needing a `/goal` session: "
            "the judge is the only stage in a replay that needs a model.\n\n"
            "Progress is written to a ledger after every stage, so an "
            "interrupted wave resumes. A concept whose ledger says its job was "
            "launched is never launched again -- hpc_job.json is write-once, and "
            "a second launch abandons a live job.\n\n"
            "Exit codes: 0 no errors, 1 at least one concept errored. A wave in "
            "which every concept needs a judge is still exit 0."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    replay_run_parser.add_argument("concepts", nargs="+", help="Concept stems, in DAG order.")
    replay_run_parser.add_argument(
        "--reason", required=True,
        help="Recorded on every concept's reopen: which upstream fix is being "
             "measured and against which rebuilt warehouse.",
    )
    replay_run_parser.add_argument(
        "--wave", default="wave", help="Ledger name (default: wave)."
    )
    replay_run_parser.add_argument(
        "--stages", nargs="+", default=None,
        metavar="STAGE",
        help="Subset of replay demo launch poll promote (default: all). Stages "
             "are cumulative and resumable, so --stages poll promote finishes a "
             "wave that was launched earlier.",
    )
    replay_run_parser.add_argument("--ledger", default=None, help="Explicit ledger path.")
    replay_run_parser.add_argument("--artifact-root", dest="artifact_root", default=None)
    replay_run_parser.add_argument(
        "--dry-run", dest="dry_run", action="store_true",
        help="Print every command that would run, and run none of them.",
    )
    replay_run_parser.set_defaults(func=_replay_run_command)

    goal_run_parser = subparsers.add_parser(
        "goal-run",
        help="Run a wave of full orchestrator sessions, k concepts in parallel.",
        description=(
            "Automates the by-hand loop: reopen/replay the concept, start an "
            "`opencode run --agent concept-port-orchestrator --auto` session on "
            "it, and keep sending that session a continuation until it emits a "
            "terminal [goal:...] marker. K of those run at once; when one "
            "finishes the next eligible concept starts.\n\n"
            "Concepts are processed in the order given, but a concept whose "
            "dependency is also in the run set waits for it to reach COMPLETED "
            "or COMPLETED_WITH_DIVERGENCE. That is forced, not polite: `replay` "
            "and `start` both refuse an unsatisfied dependency, and both runners "
            "preprocess a dependency's own attempt output.\n\n"
            "Each worker gets its own OPENCODE_GOAL_STATE_PATH -- the goal "
            "plugin's lease is exclusive and would refuse workers 2..k -- and "
            "MIMIC_SPARK_LOCK is set in every child so parallel demo runs queue "
            "on the flock instead of colliding.\n\n"
            "Progress is flushed to a ledger on every turn, so an interrupted "
            "pool resumes: a concept with a recorded session id is continued, "
            "not restarted, and a concept already terminal is left alone.\n\n"
            "Use `replay-run` instead when the concepts only need the "
            "deterministic stages -- it needs no model at all. This command is "
            "for waves that genuinely need the loop: a re-implement, or replays "
            "whose verdicts will need a judge.\n\n"
            "Exit codes: 0 every concept reached a success status, 1 otherwise."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    goal_run_parser.add_argument(
        "concepts", nargs="*",
        help="Concept stems, in DAG order. Omit when using --wave.",
    )
    goal_run_parser.add_argument(
        "--wave", default=None,
        help="Read the concept list from mimic-iv/concepts_fhir/replay/wave<N>.txt "
             "and name the ledger after it.",
    )
    goal_run_parser.add_argument(
        "--reason", required=True,
        help="Recorded on every concept's reopen: which upstream fix is being "
             "measured and against which rebuilt warehouse.",
    )
    goal_run_parser.add_argument(
        "--name", default=None,
        help="Label for this pool, used in the ledger and the default run "
             "directory. Defaults to the --wave value, or \"all\".",
    )
    goal_run_parser.add_argument(
        "-k", "--parallel", type=int, default=4,
        help="How many concepts run at once (default: 4).",
    )
    goal_run_parser.add_argument(
        "--mode", choices=list(_GOAL_MODES), default="replay",
        help="How each concept is opened: replay carries the port forward "
             "byte-identical, reopen opens it for re-implementation, none "
             "assumes it is already open (default: replay).",
    )
    goal_run_parser.add_argument(
        "--invalidate-stage", dest="invalidate_stage", default=None,
        help="With --mode reopen, also run carryover-invalidate for this stage "
             "(e.g. fhir-prober when upstream now serves a new element).",
    )
    goal_run_parser.add_argument(
        "--agent", default=None,
        help="OpenCode agent to drive (default: concept-port-orchestrator).",
    )
    goal_run_parser.add_argument(
        "--model", default=None,
        help="provider/model override. Omit to use the agent's own model.",
    )
    goal_run_parser.add_argument(
        "--max-turns", dest="max_turns", type=int, default=30,
        help="Continuations per concept before giving up (default: 30).",
    )
    goal_run_parser.add_argument(
        "--turn-timeout", dest="turn_timeout", type=float, default=3600.0,
        help="Seconds one `opencode run` invocation may take (default: 3600).",
    )
    goal_run_parser.add_argument(
        "--concept-budget", dest="concept_budget", type=float, default=6 * 3600.0,
        help="Seconds one concept may take in total (default: 21600).",
    )
    goal_run_parser.add_argument(
        "--spark-lock", dest="spark_lock", default=None,
        help="Path passed as MIMIC_SPARK_LOCK to every worker "
             "(default: ~/.mimic-spark.lock).",
    )
    goal_run_parser.add_argument("--ledger", default=None, help="Explicit ledger path.")
    goal_run_parser.add_argument(
        "--run-dir", dest="run_dir", default=None,
        help="Where per-worker goal state and session transcripts are written.",
    )
    goal_run_parser.add_argument("--artifact-root", dest="artifact_root", default=None)
    goal_run_parser.add_argument(
        "--dry-run", dest="dry_run", action="store_true",
        help="Print the plan and the command that would be run for each concept, "
             "open nothing, and start no session.",
    )
    goal_run_parser.set_defaults(func=_goal_run_command)

    hpc_launch_parser = subparsers.add_parser(
        "hpc-launch",
        help="Stage an attempt to the HPC, smoke-test it, and submit the full run.",
        description=(
            "rsync the attempt, this repo's mimic_utils source and the oracle "
            "manifest to Petrichor, run a cheap login-node smoke test, then "
            "sbatch the full-data job and record its id in hpc_job.json.\n\n"
            "A failed smoke test aborts before sbatch: a broken job still costs "
            "a queue slot."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    hpc_launch_parser.add_argument("concept", help="Concept stem (e.g. age).")
    hpc_launch_parser.add_argument("--attempt-dir", default=None)
    hpc_launch_parser.add_argument("--attempt", type=int, default=None)
    hpc_launch_parser.add_argument("--artifact-root", default=None)
    hpc_launch_parser.add_argument("--walltime", default=None)
    hpc_launch_parser.add_argument(
        "--skip-smoke", action="store_true",
        help="Submit without the login-node check (not recommended).",
    )
    hpc_launch_parser.set_defaults(func=_hpc_launch_command)

    hpc_poll_parser = subparsers.add_parser(
        "hpc-poll",
        help="Poll a submitted full run and fetch its verdict back.",
        description=(
            "Poll squeue every 5 minutes until the job leaves the queue or a "
            "fatal marker appears in its log, then fetch comparison.full.json "
            "and run_meta.full.json into the attempt directory. The large "
            "candidate Parquet stays on scratch.\n\n"
            "Leaving the queue is not success: only a fetched comparison "
            "artifact is.\n\n"
            "Exit codes: 0 match, 1 mismatch, crash or timeout."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    hpc_poll_parser.add_argument("concept", help="Concept stem (e.g. age).")
    hpc_poll_parser.add_argument("--attempt-dir", default=None)
    hpc_poll_parser.add_argument("--attempt", type=int, default=None)
    hpc_poll_parser.add_argument("--artifact-root", default=None)
    hpc_poll_parser.add_argument("--job-id", default=None)
    hpc_poll_parser.add_argument(
        "--interval", type=int, default=None,
        help="Seconds between polls (default 300; do not go lower).",
    )
    hpc_poll_parser.add_argument("--max-polls", type=int, default=288)
    hpc_poll_parser.set_defaults(func=_hpc_poll_command)

    manifest_parser = subparsers.add_parser(
        "oracle-manifest",
        help="Generate the per-concept oracle manifest (shape, key, content hash).",
        description=_oracle_manifest_module.__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    manifest_parser.add_argument("--db", required=True, help="Oracle DuckDB file (read-only).")
    manifest_parser.add_argument("--output", required=True, help="Manifest JSON path.")
    manifest_parser.add_argument("--schema", default="mimiciv_derived")
    manifest_parser.add_argument(
        "--dataset", required=True, choices=("full", "demo"),
        help="Which oracle this manifest describes.",
    )
    manifest_parser.add_argument("--max-key-cols", type=int, default=3)
    manifest_parser.add_argument("--skip-hash", action="store_true")
    manifest_parser.add_argument("--force", action="store_true")
    manifest_parser.add_argument("--threads", type=int, default=8)
    manifest_parser.add_argument("--memory-limit", default="16GB")
    manifest_parser.set_defaults(func=_oracle_manifest_command)

    register_parser = subparsers.add_parser(
        "register-derived-concepts",
        help="Upload exported concept artifacts to a Pathling server so they can be "
             "referenced by name.",
        description=(
            "Register exported concept bundles (ViewDefinitions + Library) on a "
            "SQL-on-FHIR server.\n\n"
            "Only concepts present in the artifact directory can be registered; "
            "export-mappings withholds any port that still projects a MIMIC "
            "identifier. Dependencies are pulled in and uploaded first.\n\n"
            "Writes are idempotent PUTs by id, so re-running is always safe. Every "
            "resource is read back and compared; a mismatch is fatal. Each concept is "
            "then smoke-tested, and a smoke failure is reported loudly but does NOT "
            "fail the command -- registering a view and executing one are different "
            "things, and two known upstream Pathling bugs currently break execution "
            "for some correctly-registered concepts."
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    register_parser.add_argument(
        "concepts", nargs="*", metavar="CONCEPT",
        help="Concept stems to register (e.g. age charlson). Dependencies are added "
             "automatically. Omit and pass --all to register everything ready.",
    )
    register_parser.add_argument(
        "--all", dest="every", action="store_true", default=False,
        help="Register every concept in the artifact directory.",
    )
    register_parser.add_argument(
        "--env", dest="env_name", default=None, metavar="NAME",
        help="Environment from pathling_config.yaml (e.g. local, prod). Overrides "
             "ACTIVE_PATHLING_ENV and the file's active_environment.",
    )
    register_parser.add_argument(
        "--config", dest="config_path", default=None, metavar="PATH",
        help="Pathling config path (default: mimic-iv/concepts_fhir/pathling_config.yaml).",
    )
    register_parser.add_argument(
        "--artifact-root", dest="artifact_root", default=None, metavar="DIR",
        help="Artifact directory (default: mimic-iv/concepts_fhir/artifacts).",
    )
    register_parser.add_argument(
        "--dry-run", dest="dry_run", action="store_true", default=False,
        help="Print the resolved target and the resources that would be sent, then "
             "stop. Writes nothing and requests no token.",
    )
    register_parser.set_defaults(func=_register_derived_concepts_command)

    # -- conversion-loop commands (concept state machine + DB preflight) ----
    _register_conversion_commands(subparsers)

    args = parser.parse_args()
    # pop func from args
    args = vars(args)
    func = args.pop("func", None)
    if func is None:
        parser.print_help()
        sys.exit(2)
    

    # if writing just to one file, log the file name
    if "destination_file" in args:
        logging.info("Writing to: %s", args["destination_file"])

    # func may return a process exit code (e.g. compare_concepts)
    # transpile helpers return None, which maps to a successful exit.
    sys.exit(func(**args) or 0)


if __name__ == '__main__':
    main()
