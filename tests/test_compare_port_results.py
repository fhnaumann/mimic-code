"""Tests for the deterministic concept-port comparator.

The comparator was rewritten from "parse two JSON artifacts into Python and
compare cell by cell" to "run SQL inside DuckDB against a table and a Parquet
file". These tests follow: they build real oracles and real candidate Parquet
files and assert on the SQL's actual output. Nothing is mocked, because there
is no longer a connection to mock.

The central test is :meth:`TestKeyedDiff.test_catches_multiset_permutation`.
The previous comparator gated on row count, schema and per-column min/max; a
candidate that computes every value correctly but attaches it to the wrong key
satisfies all three, and additionally has an identical mean, sum and value
multiset. Only the keyed diff rejects it.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from mimic_utils.compare_port_results import (
    DEFAULT_ATOL,
    DEFAULT_RTOL,
    EXIT_FAIL,
    EXIT_PASS,
    EXIT_UNSURE,
    classify_logical_type,
    compare_full,
    compare_port_results_cli,
    compare_shape,
    load_manifest_entry,
    scan_expression,
    types_compatible,
    write_comparison,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

AGE_COLUMNS = [
    {"name": "subject_id", "type": "INTEGER"},
    {"name": "hadm_id", "type": "INTEGER"},
    {"name": "admittime", "type": "TIMESTAMP"},
    {"name": "age", "type": "BIGINT"},
    {"name": "ratio", "type": "DOUBLE"},
]

ROWS = [
    (1, 100, "2110-04-11 15:08:00", 40, 1.0),
    (2, 200, "2180-07-23 12:35:00", 52, 2.0),
    (3, 300, "2150-01-02 03:04:00", 91, 3.0),
    (4, 400, "2160-05-06 07:08:00", 27, 4.0),
]


def _values_sql(rows=ROWS):
    return ", ".join(
        f"({r[0]}, {r[1]}, TIMESTAMP '{r[2]}', {r[3]}, {r[4]})" for r in rows
    )


@pytest.fixture
def oracle(tmp_path):
    """Oracle with `age` (key: hadm_id) and `unkeyed` (genuine duplicate rows)."""
    path = tmp_path / "oracle.db"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA mimiciv_derived")
    con.execute(
        """CREATE TABLE mimiciv_derived.age (
               subject_id INTEGER, hadm_id INTEGER, admittime TIMESTAMP,
               age BIGINT, ratio DOUBLE)"""
    )
    con.execute(f"INSERT INTO mimiciv_derived.age VALUES {_values_sql()}")
    con.execute("CREATE TABLE mimiciv_derived.unkeyed (subject_id INTEGER, drug VARCHAR)")
    con.execute(
        "INSERT INTO mimiciv_derived.unkeyed VALUES (1,'a'), (1,'a'), (2,'b')"
    )
    con.close()
    return path


@pytest.fixture
def manifest(tmp_path, oracle):
    """Manifest describing that oracle: `age` keyed, `unkeyed` full-tuple."""
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "1.0",
                "dataset": "full",
                "schema": "mimiciv_derived",
                "oracle": {"path": str(oracle), "duckdb_version": "1.5.5"},
                "concepts": {
                    "age": {
                        "row_count": len(ROWS),
                        "columns": AGE_COLUMNS,
                        "key": ["hadm_id"],
                        "comparison": "keyed_join",
                        "content_hash": "123",
                    },
                    "unkeyed": {
                        "row_count": 3,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "drug", "type": "VARCHAR"},
                        ],
                        "key": None,
                        "comparison": "full_tuple_multiset",
                    },
                },
            }
        )
    )
    return path


@pytest.fixture
def candidate(tmp_path, oracle):
    """Factory: run SQL against the oracle, write the result as a candidate file."""

    def _make(sql, name="cand", suffix=".parquet"):
        out = tmp_path / f"{name}{suffix}"
        con = duckdb.connect(str(oracle), read_only=True)
        fmt = "PARQUET" if suffix == ".parquet" else "CSV"
        con.execute(f"COPY ({sql}) TO '{out}' (FORMAT {fmt})")
        con.close()
        return out

    return _make


ALL_AGE = "SELECT * FROM mimiciv_derived.age"


# ---------------------------------------------------------------------------
# type classification
# ---------------------------------------------------------------------------


class TestTypeClassification:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("BIGINT", "integer"), ("long", "integer"), ("SMALLINT", "integer"),
            ("HUGEINT", "integer"), ("DOUBLE", "numeric"), ("double", "numeric"),
            ("DECIMAL(10,2)", "numeric"), ("FLOAT", "numeric"),
            ("VARCHAR", "string"), ("string", "string"), ("TEXT", "string"),
            ("BOOLEAN", "boolean"), ("TIMESTAMP", "datetime"), ("DATE", "date"),
            ("TIME", "time"), ("INTERVAL", "interval"), ("BLOB", "binary"),
        ],
    )
    def test_classification(self, name, expected):
        assert classify_logical_type(name) == expected

    def test_parameterised_types_stripped(self):
        assert classify_logical_type("DECIMAL(38,10)") == "numeric"
        assert classify_logical_type("VARCHAR(255)") == "string"

    @pytest.mark.parametrize(
        "a,b",
        [
            ("BIGINT", "long"),          # DuckDB vs Spark spelling
            ("DOUBLE", "double"),
            ("VARCHAR", "string"),
            ("INTEGER", "BIGINT"),       # numeric widening
            ("BIGINT", "DOUBLE"),
            ("TIMESTAMP", "DATE"),       # Pathling often returns a timestamp
            ("SMALLINT", "int"),
        ],
    )
    def test_compatible(self, a, b):
        assert types_compatible(a, b)
        assert types_compatible(b, a)  # symmetric

    @pytest.mark.parametrize(
        "a,b",
        [("BIGINT", "VARCHAR"), ("TIMESTAMP", "BIGINT"), ("BOOLEAN", "VARCHAR")],
    )
    def test_incompatible(self, a, b):
        assert not types_compatible(a, b)
        assert not types_compatible(b, a)


class TestScanExpression:
    def test_parquet(self):
        assert "read_parquet" in scan_expression("/x/a.parquet")

    def test_ndjson(self):
        assert "read_json_auto" in scan_expression("/x/a.ndjson")

    def test_csv(self):
        assert "read_csv_auto" in scan_expression("/x/a.csv")

    def test_unsupported(self):
        with pytest.raises(ValueError):
            scan_expression("/x/a.xlsx")

    def test_quotes_escaped(self):
        assert "''" in scan_expression("/x/it's.parquet")


class TestLoadManifestEntry:
    def test_loads(self, manifest):
        e = load_manifest_entry(manifest, "age")
        assert e["row_count"] == 4
        assert e["key"] == ["hadm_id"]

    def test_unknown_concept(self, manifest):
        with pytest.raises(ValueError, match="not in manifest"):
            load_manifest_entry(manifest, "nope")


# ---------------------------------------------------------------------------
# demo shape gate
# ---------------------------------------------------------------------------


class TestShapeGate:
    def test_correct_shape_passes(self, manifest, candidate):
        r = compare_shape("age", manifest, candidate(ALL_AGE))
        assert r["verdict"] == "shape_ok"
        assert r["schema"]["match"] is True
        assert r["executed"] is True

    def test_zero_rows_is_unsure_never_fail(self, manifest, candidate):
        """The 100-patient demo cohort legitimately holds nothing for some
        concepts -- neuroblock has 0 demo rows and 14,174 on full data."""
        r = compare_shape("age", manifest, candidate(f"{ALL_AGE} WHERE false"))
        assert r["verdict"] == "unsure"
        assert r["verdict"] != "shape_fail"
        assert r["schema"]["match"] is True
        assert r["candidate_row_count"] == 0

    def test_row_count_is_not_gated(self, manifest, candidate):
        """A wildly wrong demo row count must still be shape_ok."""
        r = compare_shape("age", manifest, candidate(f"{ALL_AGE} WHERE hadm_id = 100"))
        assert r["candidate_row_count"] == 1
        assert r["verdict"] == "shape_ok"
        assert "row_count" in r["not_gated"]

    def test_missing_column_fails(self, manifest, candidate):
        sql = "SELECT subject_id, hadm_id, admittime, age FROM mimiciv_derived.age"
        r = compare_shape("age", manifest, candidate(sql))
        assert r["verdict"] == "shape_fail"
        assert r["schema"]["missing_columns"] == ["ratio"]

    def test_renamed_column_reported_both_ways(self, manifest, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age AS age_years, ratio "
               "FROM mimiciv_derived.age")
        r = compare_shape("age", manifest, candidate(sql))
        assert r["verdict"] == "shape_fail"
        assert r["schema"]["missing_columns"] == ["age"]
        assert r["schema"]["extra_columns"] == ["age_years"]

    def test_extra_column_fails(self, manifest, candidate):
        r = compare_shape("age", manifest, candidate(f"SELECT *, 1 AS bonus FROM mimiciv_derived.age"))
        assert r["verdict"] == "shape_fail"
        assert r["schema"]["extra_columns"] == ["bonus"]

    def test_incompatible_type_fails(self, manifest, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, CAST(age AS VARCHAR) AS age, "
               "ratio FROM mimiciv_derived.age")
        r = compare_shape("age", manifest, candidate(sql))
        assert r["verdict"] == "shape_fail"
        assert r["schema"]["incompatible_types"][0]["column"] == "age"

    def test_compatible_type_widening_passes(self, manifest, candidate):
        """BIGINT vs DOUBLE carries the same values here."""
        sql = ("SELECT subject_id, hadm_id, admittime, CAST(age AS DOUBLE) AS age, "
               "ratio FROM mimiciv_derived.age")
        assert compare_shape("age", manifest, candidate(sql))["verdict"] == "shape_ok"

    def test_unreadable_candidate_fails_without_raising(self, manifest, tmp_path):
        r = compare_shape("age", manifest, tmp_path / "absent.parquet")
        assert r["verdict"] == "shape_fail"
        assert r["executed"] is False
        assert r["error"]

    def test_shape_gate_never_reads_the_oracle(self, manifest, candidate):
        """The demo gate works from the manifest alone -- no oracle needed."""
        r = compare_shape("age", manifest, candidate(ALL_AGE))
        assert "oracle" not in r


# ---------------------------------------------------------------------------
# full keyed diff
# ---------------------------------------------------------------------------


class TestKeyedDiff:
    def test_identical_matches(self, manifest, oracle, candidate):
        r = compare_full("age", manifest, oracle, candidate(ALL_AGE))
        assert r["verdict"] == "match"
        assert r["match"] is True
        assert r["comparison"] == "keyed_join"
        d = r["diff"]
        assert (d["only_oracle"], d["only_candidate"], d["differing"]) == (0, 0, 0)
        assert d["identical"] == 4

    def test_catches_multiset_permutation(self, manifest, oracle, candidate):
        """THE case the old min/max comparator could not see.

        Rotating the `age` column preserves row count, schema, min, max, mean,
        sum and the entire value multiset -- every gate the previous comparator
        applied. Only a keyed join reveals that the values hang off the wrong
        admissions.
        """
        sql = """
        WITH ranked AS (
          SELECT *, row_number() OVER (ORDER BY hadm_id) AS rn FROM mimiciv_derived.age
        ), rotated AS (
          SELECT age, ((row_number() OVER (ORDER BY hadm_id)) % 4) + 1 AS target_rn
          FROM mimiciv_derived.age
        )
        SELECT r.subject_id, r.hadm_id, r.admittime, v.age, r.ratio
        FROM ranked r JOIN rotated v ON r.rn = v.target_rn
        """
        cand = candidate(sql)

        # First establish that the old gates would all have passed.
        con = duckdb.connect(str(oracle), read_only=True)
        o_stats = con.execute(
            "SELECT count(*), min(age), max(age), sum(age) FROM mimiciv_derived.age"
        ).fetchone()
        c_stats = con.execute(
            f"SELECT count(*), min(age), max(age), sum(age) FROM read_parquet('{cand}')"
        ).fetchone()
        con.close()
        assert o_stats == c_stats, "precondition: aggregate stats must be identical"

        r = compare_full("age", manifest, oracle, cand)
        assert r["row_count"]["match"] is True
        assert r["schema"]["match"] is True
        assert r["verdict"] == "mismatch"
        assert r["diff"]["differing"] > 0
        assert "age" in r["diff"]["columns_differing"]

    def test_missing_row_detected(self, manifest, oracle, candidate):
        r = compare_full("age", manifest, oracle, candidate(f"{ALL_AGE} WHERE hadm_id <> 100"))
        assert r["verdict"] == "mismatch"
        assert r["diff"]["only_oracle"] == 1
        assert r["diff"]["only_candidate"] == 0

    def test_extra_row_detected(self, manifest, oracle, candidate):
        sql = (f"{ALL_AGE} UNION ALL "
               "SELECT 9, 900, TIMESTAMP '2170-01-01 00:00:00', 55, 9.0")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert r["diff"]["only_candidate"] == 1
        assert r["diff"]["only_oracle"] == 0

    def test_names_the_differing_column(self, manifest, oracle, candidate):
        """A diagnosis needs a column name, not just 'counts differ'."""
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["diff"]["columns_differing"] == {"age": 4}
        assert any("'age' differs" in d for d in r["diagnostics"])

    def test_columns_differing_omits_matching_columns(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert set(r["diff"]["columns_differing"]) == {"age"}

    def test_row_count_has_no_tolerance(self, manifest, oracle, candidate):
        r = compare_full(
            "age", manifest, oracle, candidate(f"{ALL_AGE} WHERE hadm_id <> 100"),
            rtol=0.99,
        )
        assert r["row_count"]["match"] is False
        assert r["verdict"] == "mismatch"

    def test_float_within_tolerance_matches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age, ratio * 1.0001 AS ratio "
               "FROM mimiciv_derived.age")
        assert compare_full("age", manifest, oracle, candidate(sql))["verdict"] == "match"

    def test_float_outside_tolerance_mismatches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age, ratio * 1.05 AS ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert "ratio" in r["diff"]["columns_differing"]

    def test_integers_compared_exactly(self, manifest, oracle, candidate):
        """Tolerance must not leak into integer columns."""
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        assert compare_full("age", manifest, oracle, candidate(sql))["verdict"] == "mismatch"

    def test_timestamp_within_one_second_matches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime + INTERVAL 500 MILLISECOND "
               "AS admittime, age, ratio FROM mimiciv_derived.age")
        assert compare_full("age", manifest, oracle, candidate(sql))["verdict"] == "match"

    def test_timestamp_beyond_tolerance_mismatches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime + INTERVAL 5 MINUTE AS admittime, "
               "age, ratio FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert "admittime" in r["diff"]["columns_differing"]

    def test_null_must_be_reproduced_as_null(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age, NULL::DOUBLE AS ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert "ratio" in r["diff"]["columns_differing"]

    def test_null_equals_null(self, manifest, oracle, tmp_path):
        """NULL on both sides is agreement, not a difference."""
        con = duckdb.connect(str(oracle))
        con.execute("UPDATE mimiciv_derived.age SET ratio = NULL WHERE hadm_id = 100")
        out = tmp_path / "nulls.parquet"
        con.execute(f"COPY ({ALL_AGE}) TO '{out}' (FORMAT PARQUET)")
        con.close()
        assert compare_full("age", manifest, oracle, out)["verdict"] == "match"

    def test_schema_mismatch_skips_the_diff(self, manifest, oracle, candidate):
        """Joining across mismatched columns yields noise, not a diagnosis."""
        sql = "SELECT subject_id, hadm_id, admittime, age FROM mimiciv_derived.age"
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert r["diff"] is None
        assert "diff_skipped" in r

    def test_samples_show_both_sides(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        sample = r["diff"]["samples"]["differing"][0]
        assert sample["age__candidate"] == sample["age__oracle"] + 1

    def test_sample_limit_respected(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql), sample_limit=2)
        assert len(r["diff"]["samples"]["differing"]) == 2

    def test_samples_disabled(self, manifest, oracle, candidate):
        r = compare_full("age", manifest, oracle, candidate(ALL_AGE), sample_limit=0)
        assert "samples" not in r["diff"]

    def test_artifact_stays_small(self, manifest, oracle, candidate):
        """The artifact travels back from HPC, so it must not scale with rows."""
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert len(json.dumps(r, default=str)) < 20_000

    def test_oracle_opened_read_only(self, manifest, oracle, candidate):
        before = oracle.stat().st_size
        compare_full("age", manifest, oracle, candidate(ALL_AGE))
        assert oracle.stat().st_size == before

    def test_missing_oracle_raises(self, manifest, tmp_path, candidate):
        with pytest.raises(FileNotFoundError):
            compare_full("age", manifest, tmp_path / "absent.db", tmp_path / "x.parquet")

    def test_unreadable_candidate_is_mismatch_not_crash(self, manifest, oracle, tmp_path):
        r = compare_full("age", manifest, oracle, tmp_path / "absent.parquet")
        assert r["verdict"] == "mismatch"
        assert r["executed"] is False

    def test_stale_manifest_warns(self, manifest, oracle, candidate, tmp_path):
        """A manifest describing a different oracle build must be flagged."""
        m = json.loads(Path(manifest).read_text())
        m["concepts"]["age"]["row_count"] = 999
        p = tmp_path / "stale.json"
        p.write_text(json.dumps(m))
        r = compare_full("age", p, oracle, candidate(ALL_AGE))
        assert any("stale" in w for w in r["warnings"])

    def test_ndjson_candidate_supported(self, manifest, oracle, tmp_path):
        con = duckdb.connect(str(oracle), read_only=True)
        out = tmp_path / "cand.ndjson"
        con.execute(f"COPY ({ALL_AGE}) TO '{out}' (FORMAT JSON)")
        con.close()
        assert compare_full("age", manifest, oracle, out)["verdict"] == "match"


# ---------------------------------------------------------------------------
# multiset comparison (the 13 unkeyed concepts)
# ---------------------------------------------------------------------------


class TestMultisetDiff:
    ALL = "SELECT * FROM mimiciv_derived.unkeyed"

    def test_identical_matches(self, manifest, oracle, candidate):
        r = compare_full("unkeyed", manifest, oracle, candidate(self.ALL))
        assert r["comparison"] == "full_tuple_multiset"
        assert r["verdict"] == "match"

    def test_duplicate_multiplicity_respected(self, manifest, oracle, candidate):
        """EXCEPT ALL counts duplicates: two identical rows are not one row."""
        sql = "SELECT DISTINCT subject_id, drug FROM mimiciv_derived.unkeyed"
        r = compare_full("unkeyed", manifest, oracle, candidate(sql))
        assert r["verdict"] == "mismatch"
        assert r["diff"]["only_oracle"] == 1

    def test_missing_row_detected(self, manifest, oracle, candidate):
        r = compare_full(
            "unkeyed", manifest, oracle, candidate(f"{self.ALL} WHERE drug <> 'b'")
        )
        assert r["diff"]["only_oracle"] == 1

    def test_extra_row_detected(self, manifest, oracle, candidate):
        r = compare_full(
            "unkeyed", manifest, oracle, candidate(f"{self.ALL} UNION ALL SELECT 7, 'z'")
        )
        assert r["diff"]["only_candidate"] == 1

    def test_key_is_null_in_artifact(self, manifest, oracle, candidate):
        r = compare_full("unkeyed", manifest, oracle, candidate(self.ALL))
        assert r["diff"]["key"] is None


# ---------------------------------------------------------------------------
# artifact writing + CLI
# ---------------------------------------------------------------------------


class TestWriteComparison:
    def test_write_once(self, tmp_path):
        out = tmp_path / "c.json"
        write_comparison({"verdict": "match"}, out)
        with pytest.raises(FileExistsError):
            write_comparison({"verdict": "mismatch"}, out)
        assert json.loads(out.read_text())["verdict"] == "match"

    def test_serialises_datetimes(self, tmp_path, manifest, oracle, candidate):
        """Samples contain DuckDB timestamps, which plain json.dumps rejects."""
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        out = write_comparison(r, tmp_path / "c.json")
        assert json.loads(out.read_text())["diff"]["samples"]["differing"]

    def test_creates_parents_and_leaves_no_temp(self, tmp_path):
        write_comparison({"x": 1}, tmp_path / "a" / "b" / "c.json")
        assert not list((tmp_path / "a" / "b").glob("*.tmp"))


class TestCli:
    def _run(self, *args):
        return compare_port_results_cli(list(args))

    def test_full_match_exit_0(self, manifest, oracle, candidate, tmp_path):
        rc = self._run(
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(ALL_AGE)), "--oracle", str(oracle),
            "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_PASS

    def test_full_mismatch_exit_1(self, manifest, oracle, candidate, tmp_path):
        rc = self._run(
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(f"{ALL_AGE} WHERE hadm_id <> 100")),
            "--oracle", str(oracle), "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_FAIL

    def test_shape_ok_exit_0(self, manifest, candidate, tmp_path):
        rc = self._run(
            "shape", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(ALL_AGE)),
            "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_PASS

    def test_shape_zero_rows_exit_2_unsure(self, manifest, candidate, tmp_path):
        """Distinct exit code: neither pass nor fail -- proceed to full data."""
        out = tmp_path / "o.json"
        rc = self._run(
            "shape", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(f"{ALL_AGE} WHERE false")),
            "--output", str(out),
        )
        assert rc == EXIT_UNSURE
        assert json.loads(out.read_text())["verdict"] == "unsure"

    def test_shape_fail_exit_1(self, manifest, candidate, tmp_path):
        sql = "SELECT subject_id, hadm_id, admittime, age FROM mimiciv_derived.age"
        rc = self._run(
            "shape", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(sql)), "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_FAIL

    def test_full_without_oracle_errors(self, manifest, candidate, tmp_path, capsys):
        with pytest.raises(SystemExit):
            self._run(
                "full", "--concept", "age", "--manifest", str(manifest),
                "--candidate", str(candidate(ALL_AGE)),
                "--output", str(tmp_path / "o.json"),
            )

    def test_unknown_concept_exit_1(self, manifest, oracle, candidate, tmp_path):
        rc = self._run(
            "full", "--concept", "nope", "--manifest", str(manifest),
            "--candidate", str(candidate(ALL_AGE)), "--oracle", str(oracle),
            "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_FAIL


class TestTolerancesDocumented:
    def test_defaults(self):
        assert DEFAULT_RTOL == 0.001
        assert DEFAULT_ATOL == 1e-6

    def test_artifact_records_that_row_count_is_exact(
        self, manifest, oracle, candidate
    ):
        r = compare_full("age", manifest, oracle, candidate(ALL_AGE))
        assert r["tolerances"]["row_count"] == "none (exact)"
