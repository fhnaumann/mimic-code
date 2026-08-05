"""Build the full MIMIC-IV 2.2 DuckDB oracle (raw tables + derived concepts).

Replaces ``mimic-iv/buildmimic/duckdb/import_duckdb.sh`` for unattended
(Slurm) execution.  The shell script cannot be used in a batch job: it
requires a ``duckdb`` CLI binary on PATH, resolves ``../postgres/create.sql``
relative to the process working directory, prompts on stdin when the output
file already exists, and offers no way to set ``temp_directory`` or
``memory_limit`` -- all four are fatal on a compute node.

The three schema fixups applied here are byte-for-byte the same regexes the
shell script documents, so the resulting schema matches the demo oracle:

1. ``TIMESTAMP(n)`` -> ``TIMESTAMP``          (DuckDB rejects the precision arg)
2. drop ``NOT NULL`` on ``microbiologyevents.spec_type_desc``
3. drop ``NOT NULL`` on ``prescriptions.drug``

(2) and (3) exist because DuckDB's CSV reader reads zero-length strings as
NULL, so rows PostgreSQL accepts would violate ``NOT NULL`` here.

``create.sql`` opens with ``DROP SCHEMA IF EXISTS ... CASCADE`` for all three
schemas, so ``--phase raw`` is idempotent by destruction: re-running it wipes
and reloads rather than double-loading.  It also drops ``mimiciv_derived``,
so ``raw`` must precede ``concepts``.

Usage
-----
    python -m mimic_utils build-full-oracle --phase all \
        --data /scratch3/nau025/original-mimic-iv/mimic-iv-2.2 \
        --db   /scratch3/nau025/oracle/mimic4-full.db \
        --temp-dir /scratch3/nau025/oracle/duckdb_tmp
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Iterator

# The three fixups from buildmimic/duckdb/import_duckdb.sh, in that order.
_SCHEMA_FIXUPS: tuple[tuple[str, str], ...] = (
    (r"TIMESTAMP\([0-9]+\)", "TIMESTAMP"),
    (r"spec_type_desc(.+)NOT NULL", r"spec_type_desc\1"),
    (r"drug +(VARCHAR.+)NOT NULL", r"drug \1"),
)

# import_duckdb.sh loads only these; a sibling mimic-iv-ed download would
# otherwise produce tables that do not exist in the schema.
_DATA_DIRS = ("hosp", "icu")


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _apply_schema_fixups(create_sql: str) -> str:
    out = create_sql
    for pattern, repl in _SCHEMA_FIXUPS:
        out = re.sub(pattern, repl, out)
    return out


def _csv_files(data_dir: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(table_name, path)`` for each loadable CSV, in stable order.

    Mirrors the shell script's ``find -name '*.csv???' | sort``, but also
    accepts plain ``.csv`` -- the shell glob silently matches nothing for
    uncompressed files, which fails by loading zero rows rather than erroring.
    """
    for sub in _DATA_DIRS:
        subdir = data_dir / sub
        if not subdir.is_dir():
            _log(f"WARNING: {subdir} missing, skipping")
            continue
        paths = sorted(
            p
            for p in subdir.iterdir()
            if p.is_file() and (p.name.endswith(".csv.gz") or p.name.endswith(".csv"))
        )
        for path in paths:
            table = path.name.split(".")[0]
            yield f"mimiciv_{sub}.{table}", path


def _concept_files(concepts_dir: Path) -> list[Path]:
    """Parse ``duckdb.sql``'s ordered ``.read`` directives.

    ``.read`` is a CLI dot-command, not SQL, so it cannot be executed through
    the Python client.  Dependency order is encoded purely by position in this
    file and must be preserved exactly.
    """
    driver = concepts_dir / "duckdb.sql"
    if not driver.is_file():
        raise SystemExit(f"concepts driver not found: {driver}")
    files: list[Path] = []
    for line in driver.read_text().splitlines():
        line = line.strip()
        if not line.startswith(".read "):
            continue
        rel = line[len(".read ") :].strip()
        path = concepts_dir / rel
        if not path.is_file():
            raise SystemExit(f"concept SQL referenced but missing: {path}")
        files.append(path)
    if not files:
        raise SystemExit(f"no .read directives found in {driver}")
    return files


def _connect(db: Path, *, memory_limit: str, threads: int | None, temp_dir: Path | None):
    import duckdb

    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    con.execute(f"SET memory_limit='{memory_limit}'")
    if threads:
        con.execute(f"SET threads={threads}")
    if temp_dir:
        temp_dir.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory='{temp_dir}'")
    # Large COPY loads use markedly less memory when insertion order is not
    # preserved.  Derived concepts are compared as sets, so physical row
    # order is never part of the contract.
    con.execute("SET preserve_insertion_order=false")
    _log(f"duckdb {duckdb.__version__} -> {db}")
    return con


def _phase_raw(con, repo_root: Path, data_dir: Path) -> None:
    create_sql_path = repo_root / "mimic-iv" / "buildmimic" / "postgres" / "create.sql"
    if not create_sql_path.is_file():
        raise SystemExit(f"create.sql not found: {create_sql_path}")

    _log(f"applying schema from {create_sql_path} (3 DuckDB fixups)")
    con.execute(_apply_schema_fixups(create_sql_path.read_text()))

    files = list(_csv_files(data_dir))
    if not files:
        raise SystemExit(f"no CSV files found under {data_dir}/{{{','.join(_DATA_DIRS)}}}")
    _log(f"loading {len(files)} tables")

    for table, path in files:
        started = time.time()
        try:
            con.execute(
                f"COPY {table} FROM '{path}' "
                "(HEADER, DELIM ',', QUOTE '\"', ESCAPE '\"')"
            )
        except Exception as exc:  # noqa: BLE001 - reported verbatim, then fatal
            if "does not exist" in str(exc).lower():
                _log(f"  skipped {table} (not in schema)")
                continue
            raise SystemExit(f"failed loading {path} into {table}: {exc}") from exc
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        _log(f"  {table}: {n:,} rows in {time.time() - started:.1f}s")


def _phase_concepts(con, repo_root: Path) -> None:
    concepts_dir = repo_root / "mimic-iv" / "concepts_duckdb"
    files = _concept_files(concepts_dir)
    _log(f"building {len(files)} derived concepts in DAG order")

    con.execute("CREATE SCHEMA IF NOT EXISTS mimiciv_derived")
    for i, path in enumerate(files, 1):
        started = time.time()
        try:
            con.execute(path.read_text())
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"concept {path.relative_to(concepts_dir)} failed: {exc}"
            ) from exc
        stem = path.stem
        try:
            n = con.execute(f'SELECT count(*) FROM mimiciv_derived."{stem}"').fetchone()[0]
            rows = f"{n:,} rows"
        except Exception:  # noqa: BLE001 - a few scripts build helper tables
            rows = "built"
        _log(f"  [{i:>2}/{len(files)}] {stem}: {rows} in {time.time() - started:.1f}s")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="build-full-oracle",
        description="Build the full MIMIC-IV DuckDB oracle (raw + derived concepts).",
    )
    ap.add_argument(
        "--data",
        required=True,
        type=Path,
        help="MIMIC-IV directory containing hosp/ and icu/ (*.csv.gz)",
    )
    ap.add_argument("--db", required=True, type=Path, help="output DuckDB file")
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="mimic-code checkout root (default: inferred from this file)",
    )
    ap.add_argument(
        "--phase",
        choices=("raw", "concepts", "all"),
        default="all",
        help="raw wipes and reloads all three schemas; concepts rebuilds derived only",
    )
    ap.add_argument("--memory-limit", default="400GB")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument(
        "--temp-dir",
        type=Path,
        default=None,
        help="DuckDB spill directory -- set this to scratch, never the default",
    )
    args = ap.parse_args(argv)

    if not args.data.is_dir():
        raise SystemExit(f"data directory not found: {args.data}")

    if args.phase in ("concepts",) and not args.db.is_file():
        raise SystemExit(f"--phase concepts needs an existing db: {args.db}")

    started = time.time()
    con = _connect(
        args.db,
        memory_limit=args.memory_limit,
        threads=args.threads,
        temp_dir=args.temp_dir,
    )
    try:
        if args.phase in ("raw", "all"):
            _phase_raw(con, args.repo_root, args.data)
        if args.phase in ("concepts", "all"):
            _phase_concepts(con, args.repo_root)
    finally:
        con.close()

    _log(f"done in {(time.time() - started) / 60:.1f} min -> {args.db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
