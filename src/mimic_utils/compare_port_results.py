"""Deterministic comparator for a MIMIC-on-FHIR concept port.

Two *different* queries must produce the *same table*: the canonical MIMIC-IV
SQL over relational MIMIC-IV, and an agent-authored FHIR ViewDefinition + SQL
over MIMIC-on-FHIR.  There is no shared query, so this comparison **is** the
experimental claim.  ``mimic-iv/concepts_fhir/LOOP_CONTRACT.md`` is
authoritative on gate semantics; this module implements them.

Two modes, deliberately different strengths:

``shape``
    The **demo** gate.  Cheap, local, seconds.  Checks only that the candidate
    executed and returned the right column names and compatible types.  Row
    count is **not** gated, and zero rows yields ``unsure`` rather than
    ``fail`` -- the 100-patient demo cohort legitimately holds nothing for
    some concepts (``neuroblock`` has 0 demo rows and 14,174 on full data).
    A shape pass earns nothing but permission to spend an HPC run.

``full``
    The **correctness** gate.  Runs on HPC against the immutable oracle.
    Exact row count, schema identity, and a keyed row-level diff.

Everything is computed as SQL inside DuckDB; rows are never materialised into
Python.  ``vitalsign`` is 9.7M rows and ``rhythm`` 5.9M, so the previous
whole-table-JSON contract was not a tuning problem but the wrong shape.

Per-column min/max identity is deliberately *not* a gate.  A port that
computes every value correctly but attaches it to the wrong key satisfies row
count, schema, min and max simultaneously.  The keyed diff is what
substantiates equivalence, and it reports *which column* differs -- so a
diagnosis can say "``age`` differs on 1,204 rows" instead of "counts differ".
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DERIVED_SCHEMA = "mimiciv_derived"

# Tolerances apply to *values* only, never to row count.
DEFAULT_RTOL = 0.001  # 0.1 % relative
DEFAULT_ATOL = 1e-6
TIMESTAMP_TOL_SECONDS = 1.0

DEFAULT_SAMPLE_LIMIT = 20

# ---------------------------------------------------------------------------
# Type classification
#
# Spans DuckDB (oracle) and Spark/Pathling (candidate) type vocabularies, which
# name the same logical types differently -- BIGINT vs long, DOUBLE vs double,
# VARCHAR vs string.
# ---------------------------------------------------------------------------

_INTEGER_TYPES = frozenset(
    {
        "int2", "int4", "int8", "smallint", "integer", "bigint",
        "tinyint", "byte", "short", "int", "long",
        "hugeint", "uhugeint", "utinyint", "usmallint", "uinteger", "ubigint",
        "oid", "xid", "cid", "tid",
    }
)
_NUMERIC_TYPES = frozenset(
    {
        "float4", "float8", "float", "double", "numeric", "decimal",
        "real", "double precision", "money",
    }
)
_BOOLEAN_TYPES = frozenset({"bool", "boolean"})
_STRING_TYPES = frozenset(
    {"text", "string", "varchar", "char", "bpchar", "name", "citext", "uuid"}
)
_BINARY_TYPES = frozenset({"bytea", "blob", "binary", "varbinary"})
_DATETIME_TYPES = frozenset(
    {
        "timestamp", "timestamp_ntz", "timestamptz", "datetime",
        "timestamp without time zone", "timestamp with time zone",
        "timestamp_s", "timestamp_ms", "timestamp_ns",
    }
)
_DATE_TYPES = frozenset({"date"})
_TIME_TYPES = frozenset({"time", "timetz", "time without time zone", "time with time zone"})
_INTERVAL_TYPES = frozenset({"interval"})


def _normalise_type(type_name: str) -> str:
    """Strip precision/parameters and lowercase: ``DECIMAL(10,2)`` -> ``decimal``."""
    return type_name.lower().split("(")[0].strip()


def classify_logical_type(type_name: str) -> str:
    """Map a DuckDB or Spark type name onto a logical category."""
    t = _normalise_type(type_name)
    if t in _INTEGER_TYPES:
        return "integer"
    if t in _NUMERIC_TYPES:
        return "numeric"
    if t in _BOOLEAN_TYPES:
        return "boolean"
    if t in _DATETIME_TYPES:
        return "datetime"
    if t in _DATE_TYPES:
        return "date"
    if t in _TIME_TYPES:
        return "time"
    if t in _INTERVAL_TYPES:
        return "interval"
    if t in _STRING_TYPES:
        return "string"
    if t in _BINARY_TYPES:
        return "binary"
    if t.startswith(("struct", "map", "list", "array")) or t.endswith("[]"):
        return "nested"
    if t in ("json", "jsonb"):
        return "json"
    return "other"


def types_compatible(type_a: str, type_b: str) -> bool:
    """Logical compatibility across the DuckDB / Spark type vocabularies."""
    if _normalise_type(type_a) == _normalise_type(type_b):
        return True
    cat_a = classify_logical_type(type_a)
    cat_b = classify_logical_type(type_b)
    if cat_a == cat_b:
        return True
    # Numeric widening is acceptable; SMALLINT vs BIGINT vs DOUBLE all carry
    # the same values for these concepts.
    if {cat_a, cat_b} <= {"integer", "numeric"}:
        return True
    # Pathling frequently returns a timestamp where the oracle stores a date.
    if {cat_a, cat_b} <= {"datetime", "date"}:
        return True
    return False


# ---------------------------------------------------------------------------
# SQL construction
# ---------------------------------------------------------------------------


def _q(identifier: str) -> str:
    """Quote a SQL identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def _lit(value: str) -> str:
    """Quote a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def scan_expression(path: str | Path) -> str:
    """A DuckDB scan expression for a candidate result file.

    Pathling on HPC writes Parquet; the local demo runner may write NDJSON.
    Both are read natively, so nothing is loaded through Python.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return f"read_parquet({_lit(str(p))})"
    if suffix in (".ndjson", ".jsonl", ".json"):
        return f"read_json_auto({_lit(str(p))}, format='newline_delimited')"
    if suffix == ".csv":
        return f"read_csv_auto({_lit(str(p))})"
    raise ValueError(
        f"Unsupported candidate format {suffix!r}: expected .parquet, .ndjson, "
        f".jsonl, .json or .csv"
    )


def _column_equality_sql(column: str, type_name: str, rtol: float, atol: float) -> str:
    """SQL boolean: is this column equal between oracle ``o`` and candidate ``c``?

    NULL == NULL is true (``IS NOT DISTINCT FROM`` semantics), because a NULL
    in the oracle must be reproduced as a NULL, not as a value.
    """
    o, c = f"o.{_q(column)}", f"c.{_q(column)}"
    both_null = f"({o} IS NULL AND {c} IS NULL)"
    both_present = f"({o} IS NOT NULL AND {c} IS NOT NULL)"
    category = classify_logical_type(type_name)

    if category in ("numeric",):
        close = (
            f"abs({o} - {c}) <= greatest({rtol} * greatest(abs({o}), abs({c})), {atol})"
        )
        return f"({both_null} OR ({both_present} AND {close}))"

    if category == "datetime":
        close = (
            f"abs(epoch({o}) - epoch({c})) <= {TIMESTAMP_TOL_SECONDS}"
        )
        return f"({both_null} OR ({both_present} AND {close}))"

    # Integers, strings, booleans, dates, times, binary: exact.
    return f"({o} IS NOT DISTINCT FROM {c})"


# ---------------------------------------------------------------------------
# Manifest access
# ---------------------------------------------------------------------------


def load_manifest_entry(manifest_path: str | Path, concept: str) -> Dict[str, Any]:
    """Load one concept's entry from the oracle manifest."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    concepts = manifest.get("concepts", {})
    if concept not in concepts:
        raise ValueError(
            f"Concept {concept!r} not in manifest {manifest_path}. "
            f"Known: {sorted(concepts)[:8]}{'...' if len(concepts) > 8 else ''}"
        )
    entry = dict(concepts[concept])
    entry["_dataset"] = manifest.get("dataset", "")
    entry["_oracle"] = manifest.get("oracle", {})
    return entry


def _candidate_columns(con: Any, scan: str) -> Dict[str, str]:
    """``{column: type}`` for the candidate, in physical order."""
    rows = con.execute(f"DESCRIBE SELECT * FROM {scan}").fetchall()
    return {r[0]: r[1] for r in rows}


def _compare_schemas(
    expected: Sequence[Dict[str, str]], actual: Dict[str, str]
) -> Dict[str, Any]:
    """Column name and type comparison against the manifest."""
    expected_names = [c["name"] for c in expected]
    expected_types = {c["name"]: c["type"] for c in expected}

    missing = [n for n in expected_names if n not in actual]
    extra = [n for n in actual if n not in expected_types]

    incompatible = []
    for name in expected_names:
        if name in actual and not types_compatible(expected_types[name], actual[name]):
            incompatible.append(
                {"column": name, "expected": expected_types[name], "actual": actual[name]}
            )

    return {
        "expected_columns": expected_names,
        "actual_columns": list(actual),
        "missing_columns": missing,
        "extra_columns": extra,
        "incompatible_types": incompatible,
        "match": not missing and not extra and not incompatible,
    }


# ---------------------------------------------------------------------------
# Mode: shape (the demo gate)
# ---------------------------------------------------------------------------


def compare_shape(
    concept: str,
    manifest_path: str | Path,
    candidate_path: str | Path,
) -> Dict[str, Any]:
    """Demo shape gate: did it execute, and are the columns right?

    Returns a verdict of ``shape_ok``, ``shape_fail`` or ``unsure``.  Row count
    is reported but **never** gated, and zero rows is ``unsure`` -- see
    LOOP_CONTRACT.md.
    """
    import duckdb

    entry = load_manifest_entry(manifest_path, concept)
    result: Dict[str, Any] = {
        "format_version": "2.0",
        "mode": "shape",
        "concept": concept,
        "dataset": "demo",
        "candidate": str(candidate_path),
        "gated": ["execution", "column_names", "column_types"],
        "not_gated": ["row_count"],
    }

    con = duckdb.connect(":memory:")
    try:
        scan = scan_expression(candidate_path)
        try:
            actual = _candidate_columns(con, scan)
            row_count = con.execute(f"SELECT count(*) FROM {scan}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001 -- reported as the verdict
            result["executed"] = False
            result["error"] = str(exc)
            result["verdict"] = "shape_fail"
            return result

        result["executed"] = True
        result["schema"] = _compare_schemas(entry["columns"], actual)
        # Observation only. Demo agreement is not evidence of correctness and
        # demo disagreement on count is not proof of a bug.
        result["candidate_row_count"] = row_count
        result["oracle_full_row_count"] = entry["row_count"]

        if not result["schema"]["match"]:
            result["verdict"] = "shape_fail"
        elif row_count == 0:
            # Not a failure and not a pass: the demo cohort may legitimately
            # contain nothing for this concept. Proceed to full data.
            result["verdict"] = "unsure"
            result["note"] = (
                "0 demo rows: the 100-patient cohort may legitimately contain "
                "nothing for this concept. Not a failure. Proceed to full data."
            )
        else:
            result["verdict"] = "shape_ok"
            result["note"] = (
                "Shape is correct. This earns permission to spend an HPC run; "
                "it is not evidence of correctness."
            )
        return result
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Mode: full (the correctness gate)
# ---------------------------------------------------------------------------


def _keyed_diff(
    con: Any,
    oracle_ref: str,
    scan: str,
    key: Sequence[str],
    value_columns: Sequence[Dict[str, str]],
    rtol: float,
    atol: float,
    sample_limit: int,
) -> Dict[str, Any]:
    """Full outer join on the natural key, then per-column value comparison."""
    join_on = " AND ".join(f"o.{_q(k)} = c.{_q(k)}" for k in key)
    anchor = _q(key[0])
    both = f"o.{anchor} IS NOT NULL AND c.{anchor} IS NOT NULL"

    eq_by_column = {
        col["name"]: _column_equality_sql(col["name"], col["type"], rtol, atol)
        for col in value_columns
    }
    all_equal = " AND ".join(eq_by_column.values()) if eq_by_column else "TRUE"

    tallies = ",\n  ".join(
        f'count(*) FILTER (WHERE {both} AND NOT {expr}) AS {_q("d__" + name)}'
        for name, expr in eq_by_column.items()
    )
    tally_clause = (",\n  " + tallies) if tallies else ""

    sql = f"""
SELECT
  count(*) FILTER (WHERE c.{anchor} IS NULL)                       AS only_oracle,
  count(*) FILTER (WHERE o.{anchor} IS NULL)                       AS only_candidate,
  count(*) FILTER (WHERE {both} AND NOT ({all_equal}))             AS differing,
  count(*) FILTER (WHERE {both} AND ({all_equal}))                 AS identical{tally_clause}
FROM {oracle_ref} o
FULL OUTER JOIN {scan} c ON {join_on}
"""
    row = con.execute(sql).fetchone()
    columns = [d[0] for d in con.description]
    counts = dict(zip(columns, row))

    per_column = {
        name: counts.pop("d__" + name, 0)
        for name in eq_by_column
    }

    diff: Dict[str, Any] = {
        "key": list(key),
        "only_oracle": counts["only_oracle"],
        "only_candidate": counts["only_candidate"],
        "differing": counts["differing"],
        "identical": counts["identical"],
        # Only columns that actually differ, most-affected first: this is the
        # payload a diagnostician acts on.
        "columns_differing": dict(
            sorted(
                ((k, v) for k, v in per_column.items() if v),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
    }

    if sample_limit > 0:
        diff["samples"] = _keyed_samples(
            con, oracle_ref, scan, key, value_columns, all_equal, join_on,
            anchor, both, sample_limit,
        )
    return diff


def _keyed_samples(
    con, oracle_ref, scan, key, value_columns, all_equal, join_on,
    anchor, both, limit,
) -> Dict[str, List[Any]]:
    """A bounded sample of each mismatch class, for diagnosis."""
    key_select = ", ".join(f"coalesce(o.{_q(k)}, c.{_q(k)}) AS {_q(k)}" for k in key)

    def _rows(where: str, extra_select: str = "") -> List[Dict[str, Any]]:
        sql = f"""
SELECT {key_select}{extra_select}
FROM {oracle_ref} o
FULL OUTER JOIN {scan} c ON {join_on}
WHERE {where}
LIMIT {int(limit)}
"""
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    # For differing rows, show both sides of every value column so the
    # discrepancy is visible without a second round trip.
    pairs = "".join(
        f", o.{_q(c['name'])} AS {_q(c['name'] + '__oracle')}"
        f", c.{_q(c['name'])} AS {_q(c['name'] + '__candidate')}"
        for c in value_columns
    )
    return {
        "only_oracle": _rows(f"c.{anchor} IS NULL"),
        "only_candidate": _rows(f"o.{anchor} IS NULL"),
        "differing": _rows(f"{both} AND NOT ({all_equal})", pairs),
    }


def _multiset_diff(
    con: Any,
    oracle_ref: str,
    scan: str,
    columns: Sequence[Dict[str, str]],
    sample_limit: int,
) -> Dict[str, Any]:
    """Full-tuple multiset comparison, for concepts with no unique key.

    Complete as an equivalence check -- ``EXCEPT ALL`` respects duplicate
    multiplicity -- but it names no column, so diagnosis is harder than with a
    keyed diff.
    """
    names = [c["name"] for c in columns]
    o_proj = ", ".join(_q(n) for n in names)
    # Cast the candidate to the oracle's declared types so EXCEPT ALL does not
    # fail on a merely-cosmetic type difference (Spark long vs DuckDB BIGINT).
    c_proj = ", ".join(f"CAST({_q(c['name'])} AS {c['type']}) AS {_q(c['name'])}" for c in columns)

    only_oracle = con.execute(
        f"SELECT count(*) FROM (SELECT {o_proj} FROM {oracle_ref} "
        f"EXCEPT ALL SELECT {c_proj} FROM {scan})"
    ).fetchone()[0]
    only_candidate = con.execute(
        f"SELECT count(*) FROM (SELECT {c_proj} FROM {scan} "
        f"EXCEPT ALL SELECT {o_proj} FROM {oracle_ref})"
    ).fetchone()[0]

    diff: Dict[str, Any] = {
        "key": None,
        "only_oracle": only_oracle,
        "only_candidate": only_candidate,
        "differing": None,  # undefined without a key to align rows
        "identical": None,
    }
    if sample_limit > 0:
        cur = con.execute(
            f"SELECT {o_proj} FROM {oracle_ref} EXCEPT ALL SELECT {c_proj} FROM {scan} "
            f"LIMIT {int(sample_limit)}"
        )
        cols = [d[0] for d in cur.description]
        diff["samples"] = {
            "only_oracle": [dict(zip(cols, r)) for r in cur.fetchall()],
        }
        cur = con.execute(
            f"SELECT {c_proj} FROM {scan} EXCEPT ALL SELECT {o_proj} FROM {oracle_ref} "
            f"LIMIT {int(sample_limit)}"
        )
        diff["samples"]["only_candidate"] = [
            dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()
        ]
    return diff


def compare_full(
    concept: str,
    manifest_path: str | Path,
    oracle_db: str | Path,
    candidate_path: str | Path,
    *,
    schema: str = DERIVED_SCHEMA,
    rtol: float = DEFAULT_RTOL,
    atol: float = DEFAULT_ATOL,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> Dict[str, Any]:
    """Full-data correctness gate: row count, schema, and the keyed diff."""
    import duckdb

    entry = load_manifest_entry(manifest_path, concept)
    oracle_db = Path(oracle_db)
    if not oracle_db.is_file():
        raise FileNotFoundError(f"Oracle not found: {oracle_db}")

    result: Dict[str, Any] = {
        "format_version": "2.0",
        "mode": "full",
        "concept": concept,
        "dataset": "full",
        "candidate": str(candidate_path),
        "oracle": {
            "path": str(oracle_db),
            "table": f"{schema}.{concept}",
            "manifest_row_count": entry["row_count"],
            "manifest_content_hash": entry.get("content_hash"),
        },
        "tolerances": {
            "row_count": "none (exact)",
            "relative": rtol,
            "absolute": atol,
            "timestamp_seconds": TIMESTAMP_TOL_SECONDS,
        },
    }

    con = duckdb.connect(":memory:")
    try:
        # The oracle is read-only: a comparison must never be able to mutate
        # the ground truth it is comparing against.
        con.execute(f"ATTACH {_lit(str(oracle_db))} AS oracle (READ_ONLY)")
        oracle_ref = f"oracle.{schema}.{_q(concept)}"
        scan = scan_expression(candidate_path)

        try:
            actual = _candidate_columns(con, scan)
            candidate_rows = con.execute(f"SELECT count(*) FROM {scan}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            result["executed"] = False
            result["error"] = str(exc)
            result["match"] = False
            result["verdict"] = "mismatch"
            return result

        result["executed"] = True

        oracle_rows = con.execute(f"SELECT count(*) FROM {oracle_ref}").fetchone()[0]
        result["row_count"] = {
            "oracle": oracle_rows,
            "candidate": candidate_rows,
            "delta": candidate_rows - oracle_rows,
            "match": oracle_rows == candidate_rows,
        }
        if oracle_rows != entry["row_count"]:
            result.setdefault("warnings", []).append(
                f"Oracle table has {oracle_rows} rows but the manifest records "
                f"{entry['row_count']}: the manifest is stale relative to this oracle."
            )

        result["schema"] = _compare_schemas(entry["columns"], actual)

        # A keyed join across mismatched columns yields noise, not a diagnosis.
        if not result["schema"]["match"]:
            result["diff"] = None
            result["diff_skipped"] = "schema mismatch: fix columns before diffing rows"
            result["match"] = False
            result["verdict"] = "mismatch"
            return result

        key = entry.get("key")
        columns = entry["columns"]
        if key:
            value_columns = [c for c in columns if c["name"] not in set(key)]
            result["comparison"] = "keyed_join"
            result["diff"] = _keyed_diff(
                con, oracle_ref, scan, key, value_columns, rtol, atol, sample_limit
            )
            clean = (
                result["diff"]["only_oracle"] == 0
                and result["diff"]["only_candidate"] == 0
                and result["diff"]["differing"] == 0
            )
        else:
            result["comparison"] = "full_tuple_multiset"
            result["diff"] = _multiset_diff(con, oracle_ref, scan, columns, sample_limit)
            clean = (
                result["diff"]["only_oracle"] == 0
                and result["diff"]["only_candidate"] == 0
            )

        result["match"] = bool(result["row_count"]["match"] and clean)
        result["verdict"] = "match" if result["match"] else "mismatch"
        result["diagnostics"] = _diagnostics(result)
        return result
    finally:
        con.close()


def _diagnostics(result: Dict[str, Any]) -> List[str]:
    """Human-readable summary lines for a mismatch."""
    out: List[str] = []
    rc = result.get("row_count", {})
    if rc and not rc.get("match"):
        out.append(
            f"row count: oracle {rc['oracle']:,} vs candidate {rc['candidate']:,} "
            f"(delta {rc['delta']:+,})"
        )
    diff = result.get("diff") or {}
    if diff.get("only_oracle"):
        out.append(f"{diff['only_oracle']:,} row(s) present in oracle but not candidate")
    if diff.get("only_candidate"):
        out.append(f"{diff['only_candidate']:,} row(s) present in candidate but not oracle")
    if diff.get("differing"):
        out.append(f"{diff['differing']:,} key-matched row(s) with differing values")
    for column, n in (diff.get("columns_differing") or {}).items():
        out.append(f"  column {column!r} differs on {n:,} row(s)")
    return out


# ---------------------------------------------------------------------------
# Artifact writing
# ---------------------------------------------------------------------------


def _json_default(value: Any) -> Any:
    """Serialise DuckDB scalars (datetime, Decimal, ...) that JSON cannot."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_comparison(result: Dict[str, Any], output_path: str | Path) -> Path:
    """Write the comparison artifact write-once, via a temp file + rename."""
    output_path = Path(output_path).resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Comparison artifact already exists (write-once): {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        tmp_path.replace(output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Exit codes: 0 pass, 1 fail, 2 unsure (demo only -- neither pass nor fail).
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_UNSURE = 2


def compare_port_results_cli(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="compare-port-results",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "mode",
        choices=("shape", "full"),
        help="shape = demo gate (columns/types only); full = correctness gate",
    )
    ap.add_argument("--concept", required=True)
    ap.add_argument(
        "--manifest",
        required=True,
        help="oracle manifest JSON (mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json)",
    )
    ap.add_argument(
        "--candidate", required=True, help="candidate result (.parquet / .ndjson / .csv)"
    )
    ap.add_argument("--output", required=True, help="comparison JSON (must not exist)")
    ap.add_argument("--oracle", help="oracle DuckDB file (required for --mode full)")
    ap.add_argument("--schema", default=DERIVED_SCHEMA)
    ap.add_argument("--rtol", type=float, default=DEFAULT_RTOL)
    ap.add_argument("--atol", type=float, default=DEFAULT_ATOL)
    ap.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    args = ap.parse_args(argv)

    try:
        if args.mode == "shape":
            result = compare_shape(args.concept, args.manifest, args.candidate)
        else:
            if not args.oracle:
                ap.error("--oracle is required for mode 'full'")
            result = compare_full(
                args.concept,
                args.manifest,
                args.oracle,
                args.candidate,
                schema=args.schema,
                rtol=args.rtol,
                atol=args.atol,
                sample_limit=args.sample_limit,
            )
    except Exception as exc:  # noqa: BLE001
        logging.error("compare-port-results failed: %s", exc)
        return EXIT_FAIL

    out = write_comparison(result, args.output)
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


if __name__ == "__main__":
    sys.exit(compare_port_results_cli())
