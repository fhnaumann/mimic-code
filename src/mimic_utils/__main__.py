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


def _compare_port_results_command(**kwargs) -> int:
    """Dispatch for ``mimic_utils compare-port-results``.

    Exit codes: 0 pass, 1 fail, 2 unsure (demo shape gate with 0 rows -- neither
    a pass nor a failure; proceed to full data).
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

    verdict = result.get("verdict")
    if verdict in ("match", "shape_ok"):
        logging.info("Comparison: %s", verdict.upper())
        return EXIT_PASS
    if verdict == "unsure":
        logging.warning("Comparison: UNSURE — %s", result.get("note", ""))
        return EXIT_UNSURE

    logging.warning("Comparison: %s", str(verdict).upper())
    for line in result.get("diagnostics", []) or []:
        logging.warning("  %s", line)
    if result.get("error"):
        logging.warning("  error: %s", result["error"])
    schema = result.get("schema") or {}
    for field in ("missing_columns", "extra_columns", "incompatible_types"):
        if schema.get(field):
            logging.warning("  %s: %s", field, schema[field])
    return EXIT_FAIL


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
