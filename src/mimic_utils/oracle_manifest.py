"""Generate the oracle manifest: the port loop's contract for every concept.

For each table in ``mimiciv_derived`` this records the target shape a
MIMIC-on-FHIR port must reproduce:

* ``row_count``    -- exact, the primary hard gate
* ``columns``      -- names and DuckDB types, in physical order
* ``key``          -- smallest empirically-unique column set, or ``null``
* ``content_hash`` -- order-independent hash of the full table contents

The manifest is small (a few hundred KB for all 65 concepts) and is the
artifact that travels from HPC back to the laptop.  It lets a porting agent
know exactly what to hit without reading the 14 GB oracle, and it pins the
oracle's identity so a later comparison cannot silently run against a
different build.

Why the key is discovered empirically rather than parsed out of the concept
SQL: the SQL says what was *intended*, the data says what is *true*.  A key
that is not actually unique would make the keyed diff join fan out and report
nonsense, so uniqueness is verified with ``count(*) = count(DISTINCT ...)``
against the real oracle.

The smallest unique key is preferred deliberately.  If a port gets
``subject_id`` wrong but ``hadm_id`` right, keying on ``hadm_id`` alone reports
a value mismatch in a named column; keying on both instead reports
"row missing from oracle" plus "extra row in candidate", which localises
nothing.  Smaller keys give better diagnostics.

``key: null`` means no unique key up to ``--max-key-cols`` was found; that
concept must be compared as a full-tuple multiset instead of by join.

Usage
-----
    python -m mimic_utils.oracle_manifest \
        --db /scratch3/nau025/oracle/mimic4-full.db \
        --output mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json \
        --dataset full
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence

# Identity and time columns that plausibly participate in a concept's grain,
# in rough preference order.  Anything not listed here is still reachable via
# the full-tuple fallback, but is never proposed as a key component.
_ID_COLS = (
    "subject_id",
    "hadm_id",
    "stay_id",
    "icustay_id",
    "transfer_id",
    "pharmacy_id",
    "emar_id",
    "poe_id",
    "order_id",
    "linkorderid",
    "orderid",
    "itemid",
    "micro_specimen_id",
    "specimen_id",
)
_GRAIN_COLS = (
    "charttime",
    "starttime",
    "endtime",
    "storetime",
    "admittime",
    "dischtime",
    "hr",
    "seq_num",
    "hadm_num",
    "icu_intime",
    "intime",
    "outtime",
    "ab_id",
    "antibiotic_time",
    "culture_time",
    "label",
    "test_name",
    "org_name",
)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _q(col: str) -> str:
    return '"' + col.replace('"', '""') + '"'


def _key_candidates(columns: Sequence[str], max_cols: int) -> list[tuple[str, ...]]:
    """Candidate key column sets, ordered by size then preference.

    Only columns from the identity/grain vocabulary are considered, so the
    search stays small: a handful of probes per concept rather than the full
    power set of up to 29 columns.

    Every candidate must be **anchored** by at least one identity column when
    the table has one.  Without that rule a bare timestamp wins on small data
    -- on the 100-patient demo, ``charttime`` alone is unique for
    ``oxygen_delivery`` and ``starttime`` alone is unique for ``ventilation``,
    both of which are false at full scale.  Uniqueness in a sample is not
    evidence of a key; a MIMIC concept row is identified by *whose* it is plus
    *when*, never by *when* alone.
    """
    present = set(columns)
    ids = [c for c in _ID_COLS if c in present]
    grains = [c for c in _GRAIN_COLS if c in present]
    pool = ids + grains
    rank = {c: i for i, c in enumerate(pool)}
    id_set = set(ids)

    out: list[tuple[str, ...]] = []
    for size in range(1, max_cols + 1):
        combos = [
            combo
            for combo in itertools.combinations(pool, size)
            # anchor requirement; skipped only when the table has no id column
            if not id_set or id_set.intersection(combo)
        ]
        combos.sort(key=lambda combo: tuple(rank[c] for c in combo))
        out.extend(combos)
    return out


def _find_key(
    con, table: str, schema: str, columns: Sequence[str], n_rows: int, max_cols: int
) -> tuple[list[str] | None, int]:
    """Return the smallest empirically-unique key, and how many probes it took."""
    if n_rows == 0:
        return None, 0

    fq = f"{schema}.{_q(table)}"
    probes = 0
    for combo in _key_candidates(columns, max_cols):
        probes += 1
        cols = ", ".join(_q(c) for c in combo)
        # count(DISTINCT ...) ignores rows where any listed column is NULL, so
        # a NULL-bearing candidate must also be rejected: compare against the
        # count of rows in which the whole candidate is non-NULL.
        row = con.execute(
            f"SELECT count(DISTINCT ({cols})), "
            f"       count(*) FILTER (WHERE {' AND '.join(f'{_q(c)} IS NOT NULL' for c in combo)}) "
            f"FROM {fq}"
        ).fetchone()
        distinct, non_null = row[0], row[1]
        if distinct == n_rows and non_null == n_rows:
            return list(combo), probes
    return None, probes


def _content_hash(con, table: str, schema: str, columns: Sequence[str]) -> str:
    """Order-independent hash of the entire table.

    ``sum`` rather than ``bit_xor``: XOR cancels identical row pairs, so two
    duplicate rows would hash the same as zero rows.
    """
    args = ", ".join(_q(c) for c in columns)
    val = con.execute(
        f"SELECT sum(hash({args})::HUGEINT) FROM {schema}.{_q(table)}"
    ).fetchone()[0]
    return "0" if val is None else str(val)


def build_manifest(
    db: Path,
    schema: str,
    dataset: str,
    max_key_cols: int,
    skip_hash: bool,
    threads: int,
    memory_limit: str,
) -> dict[str, Any]:
    import duckdb

    # Deliberately modest defaults: this is designed to run on a shared login
    # node, where saturating 64 cores would be antisocial and may be killed.
    con = duckdb.connect(
        str(db),
        read_only=True,
        config={"threads": threads, "memory_limit": memory_limit},
    )
    tables = [
        r[0]
        for r in con.execute(
            "SELECT table_name FROM duckdb_tables() WHERE schema_name = ? ORDER BY table_name",
            [schema],
        ).fetchall()
    ]
    if not tables:
        raise SystemExit(f"no tables found in {schema} of {db}")
    _log(f"{len(tables)} tables in {schema} of {db}")

    stat = db.stat()
    manifest: dict[str, Any] = {
        "format_version": "1.0",
        "dataset": dataset,
        "schema": schema,
        "oracle": {
            "path": str(db),
            "size_bytes": stat.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(stat.st_mtime)),
            "duckdb_version": duckdb.__version__,
        },
        "concepts": {},
    }

    unkeyed: list[str] = []
    for i, table in enumerate(tables, 1):
        started = time.time()
        desc = con.execute(f"DESCRIBE {schema}.{_q(table)}").fetchall()
        columns = [c[0] for c in desc]
        n_rows = con.execute(f"SELECT count(*) FROM {schema}.{_q(table)}").fetchone()[0]

        key, probes = _find_key(con, table, schema, columns, n_rows, max_key_cols)
        if key is None:
            unkeyed.append(table)

        entry: dict[str, Any] = {
            "row_count": n_rows,
            "columns": [{"name": c[0], "type": c[1]} for c in desc],
            "key": key,
            "key_probes": probes,
            "comparison": "keyed_join" if key else "full_tuple_multiset",
        }
        if not skip_hash:
            entry["content_hash"] = _content_hash(con, table, schema, columns)
        manifest["concepts"][table] = entry

        keytxt = "+".join(key) if key else "NONE (full-tuple)"
        _log(
            f"  [{i:>2}/{len(tables)}] {table}: {n_rows:,} rows, "
            f"{len(columns)} cols, key={keytxt} ({probes} probes, {time.time() - started:.1f}s)"
        )

    con.close()
    manifest["summary"] = {
        "concept_count": len(tables),
        "total_rows": sum(c["row_count"] for c in manifest["concepts"].values()),
        "unkeyed_concepts": unkeyed,
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="oracle-manifest",
        description="Generate the per-concept oracle manifest (shape, key, content hash).",
    )
    ap.add_argument("--db", required=True, type=Path, help="oracle DuckDB file (read-only)")
    ap.add_argument("--output", required=True, type=Path, help="manifest JSON path")
    ap.add_argument("--schema", default="mimiciv_derived")
    ap.add_argument(
        "--dataset",
        required=True,
        choices=("full", "demo"),
        help="which oracle this describes",
    )
    ap.add_argument(
        "--max-key-cols",
        type=int,
        default=3,
        help="largest key size to search before falling back to full-tuple (default 3)",
    )
    ap.add_argument(
        "--skip-hash",
        action="store_true",
        help="omit content hashes (faster; loses the oracle-identity guarantee)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing manifest",
    )
    ap.add_argument(
        "--threads",
        type=int,
        default=8,
        help="DuckDB threads (default 8 -- safe for a shared login node)",
    )
    ap.add_argument("--memory-limit", default="16GB")
    args = ap.parse_args(argv)

    if not args.db.is_file():
        raise SystemExit(f"oracle not found: {args.db}")
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.output} (pass --force)")

    started = time.time()
    manifest = build_manifest(
        args.db,
        args.schema,
        args.dataset,
        args.max_key_cols,
        args.skip_hash,
        args.threads,
        args.memory_limit,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    s = manifest["summary"]
    _log(f"wrote {args.output} ({args.output.stat().st_size / 1024:.0f} KB)")
    _log(
        f"{s['concept_count']} concepts, {s['total_rows']:,} rows, "
        f"{len(s['unkeyed_concepts'])} without a unique key "
        f"in {(time.time() - started) / 60:.1f} min"
    )
    if s["unkeyed_concepts"]:
        _log(f"  needs review: {', '.join(s['unkeyed_concepts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
