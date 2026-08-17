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
    _check_key_alignment,
    _check_key_prefixes,
    DEFAULT_RTOL,
    EXIT_FAIL,
    EXIT_PASS,
    EXIT_UNSURE,
    UNREPRESENTABLE_FILENAME,
    UnrepresentableDeclarationError,
    classify_logical_type,
    compare_full,
    compare_port_results_cli,
    compare_shape,
    load_manifest_entry,
    load_unrepresentable,
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
    # Shaped like `acei`/`arb`: unkeyed, but with an identity spine and two
    # timestamp columns the FHIR ETL is known to drop. This is the shape the
    # residual pairing exists for.
    con.execute(
        """CREATE TABLE mimiciv_derived.meds (
               subject_id INTEGER, hadm_id INTEGER, drug VARCHAR,
               starttime TIMESTAMP, stoptime TIMESTAMP)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.meds VALUES
               (1, 100, 'Lisinopril', TIMESTAMP '2150-01-01 08:00:00',
                                      TIMESTAMP '2150-01-02 08:00:00'),
               (1, 100, 'Captopril',  TIMESTAMP '2150-01-03 08:00:00',
                                      TIMESTAMP '2150-01-04 08:00:00'),
               (2, 200, 'Lisinopril', TIMESTAMP '2151-03-12 02:30:00',
                                      TIMESTAMP '2151-03-13 02:30:00'),
               (3, 300, 'Ramipril',   TIMESTAMP '2152-05-01 08:00:00',
                                      TIMESTAMP '2152-05-02 08:00:00')"""
    )
    # No identity column at all: pairing must refuse to claim an anchor.
    con.execute("CREATE TABLE mimiciv_derived.anon (label VARCHAR, amount INTEGER)")
    con.execute("INSERT INTO mimiciv_derived.anon VALUES ('a', 1), ('b', 2)")
    # Two DST spring-forward wall times and two ordinary ones. The gap rows are
    # what `mimic-fhir`'s TIMESTAMPTZ cast rewrites and no port can invert; the
    # ordinary ones must stay unexplained by the same replay, or attribution
    # would be a licence rather than a proof.
    con.execute(
        """CREATE TABLE mimiciv_derived.dst (
               subject_id INTEGER, hadm_id INTEGER, charttime TIMESTAMP,
               value DOUBLE)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.dst VALUES
               (1, 100, TIMESTAMP '2153-03-11 02:30:00', 3.0),
               (2, 200, TIMESTAMP '2181-03-11 02:52:00', 2.0),
               (3, 300, TIMESTAMP '2154-05-02 15:55:21', 1.0),
               (4, 400, TIMESTAMP '2160-05-06 07:08:00', 4.0)"""
    )
    # The same shape without a key, so the paired residual earns the same
    # attribution the keyed join does.
    con.execute(
        """CREATE TABLE mimiciv_derived.dst_unkeyed (
               subject_id INTEGER, drug VARCHAR, starttime TIMESTAMP)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.dst_unkeyed VALUES
               (1, 'Lisinopril', TIMESTAMP '2153-03-11 02:30:00'),
               (2, 'Captopril',  TIMESTAMP '2181-03-11 02:52:00'),
               (3, 'Ramipril',   TIMESTAMP '2154-05-02 15:55:21')"""
    )
    # The same shift, but landing in the *key* instead of in a value. This is
    # the shape six chartevents concepts have: they key on `charttime`, so a
    # shifted row does not conflict -- it fails to join at all, and shows up as
    # `only_oracle` plus `only_candidate`.
    con.execute(
        """CREATE TABLE mimiciv_derived.dst_keyed_time (
               stay_id INTEGER, charttime TIMESTAMP, value DOUBLE)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.dst_keyed_time VALUES
               (1, TIMESTAMP '2153-03-11 02:30:00', 3.0),
               (2, TIMESTAMP '2154-05-02 15:55:21', 1.0),
               (3, TIMESTAMP '2160-05-06 07:08:00', 4.0)"""
    )
    # `oxygen_delivery`'s shape: the shift lands on a key the candidate ALREADY
    # holds, so the row is absorbed instead of re-appearing beside its partner.
    # Subject 1 owns both 02:00 (in the gap) and 03:00 on the same March Sunday.
    con.execute(
        """CREATE TABLE mimiciv_derived.dst_collision (
               subject_id INTEGER, charttime TIMESTAMP, o2_flow DOUBLE,
               device VARCHAR)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.dst_collision VALUES
               (1, TIMESTAMP '2190-03-14 02:00:00', 15.0, 'Aerosol-cool'),
               (1, TIMESTAMP '2190-03-14 03:00:00',  6.0, 'Nasal cannula'),
               (2, TIMESTAMP '2153-03-11 02:30:00',  4.0, 'Face tent'),
               (3, TIMESTAMP '2160-05-06 07:08:00',  2.0, 'Nasal cannula')"""
    )
    # `phenylephrine`'s shape: unkeyed, a float the FHIR warehouse serves at
    # decimal(32,6), and an identifier column with no FHIR representation.
    con.execute(
        """CREATE TABLE mimiciv_derived.infusion (
               stay_id INTEGER, linkorderid INTEGER, vaso_rate FLOAT,
               starttime TIMESTAMP)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.infusion VALUES
               (1, 111, 0.5002709627151489, TIMESTAMP '2150-06-01 08:00:00'),
               (1, 112, 1.7431196212768555, TIMESTAMP '2150-06-01 09:00:00'),
               (2, 221, 3.2984561920166016, TIMESTAMP '2150-06-02 08:00:00'),
               (2, 222, 8.1179904937744141, TIMESTAMP '2153-03-11 02:30:00')"""
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
                    "meds": {
                        "row_count": 4,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "hadm_id", "type": "INTEGER"},
                            {"name": "drug", "type": "VARCHAR"},
                            {"name": "starttime", "type": "TIMESTAMP"},
                            {"name": "stoptime", "type": "TIMESTAMP"},
                        ],
                        "key": None,
                        "comparison": "full_tuple_multiset",
                    },
                    "anon": {
                        "row_count": 2,
                        "columns": [
                            {"name": "label", "type": "VARCHAR"},
                            {"name": "amount", "type": "INTEGER"},
                        ],
                        "key": None,
                        "comparison": "full_tuple_multiset",
                    },
                    "dst": {
                        "row_count": 4,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "hadm_id", "type": "INTEGER"},
                            {"name": "charttime", "type": "TIMESTAMP"},
                            {"name": "value", "type": "DOUBLE"},
                        ],
                        "key": ["hadm_id"],
                        "comparison": "keyed_join",
                    },
                    "dst_unkeyed": {
                        "row_count": 3,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "drug", "type": "VARCHAR"},
                            {"name": "starttime", "type": "TIMESTAMP"},
                        ],
                        "key": None,
                        "comparison": "full_tuple_multiset",
                    },
                    "dst_keyed_time": {
                        "row_count": 3,
                        "columns": [
                            {"name": "stay_id", "type": "INTEGER"},
                            {"name": "charttime", "type": "TIMESTAMP"},
                            {"name": "value", "type": "DOUBLE"},
                        ],
                        "key": ["stay_id", "charttime"],
                        "comparison": "keyed_join",
                    },
                    "dst_collision": {
                        "row_count": 4,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "charttime", "type": "TIMESTAMP"},
                            {"name": "o2_flow", "type": "DOUBLE"},
                            {"name": "device", "type": "VARCHAR"},
                        ],
                        "key": ["subject_id", "charttime"],
                        "comparison": "keyed_join",
                    },
                    "infusion": {
                        "row_count": 4,
                        "columns": [
                            {"name": "stay_id", "type": "INTEGER"},
                            {"name": "linkorderid", "type": "INTEGER"},
                            {"name": "vaso_rate", "type": "FLOAT"},
                            {"name": "starttime", "type": "TIMESTAMP"},
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

    def test_string_where_number_expected_carries_a_cast_hint(self, manifest, candidate):
        """The remedy travels with the failure, so no probing is needed to find it."""
        sql = ("SELECT subject_id, hadm_id, admittime, CAST(age AS VARCHAR) AS age, "
               "ratio FROM mimiciv_derived.age")
        r = compare_shape("age", manifest, candidate(sql))
        assert len(r["schema"]["hints"]) == 1
        assert r["schema"]["hints"][0].startswith("age: candidate is VARCHAR")
        assert "CAST" in r["schema"]["hints"][0]
        # `age` is not an identifier, so the identifier-spine half stays quiet.
        assert "getResourceKey" not in r["schema"]["hints"][0]

    def test_identifier_column_hint_names_the_identifier_spine(self, manifest, candidate):
        sql = ("SELECT CAST(subject_id AS VARCHAR) AS subject_id, hadm_id, admittime, "
               "age, ratio FROM mimiciv_derived.age")
        r = compare_shape("age", manifest, candidate(sql))
        assert "getResourceKey" in r["schema"]["hints"][0]
        assert "identifier.value" in r["schema"]["hints"][0]

    def test_no_hints_when_types_agree(self, manifest, candidate):
        r = compare_shape("age", manifest, candidate(ALL_AGE))
        assert r["verdict"] == "shape_ok"
        assert "hints" not in r["schema"]

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
        # `contested`, not `mismatch`: the comparator sees a value conflict and
        # says so, but rotated values and upstream ETL rewriting are the same
        # shape from here. The judge separates them.
        assert r["verdict"] == "review"
        assert r["divergence"]["tier"] == "contested"
        assert r["diff"]["differing"] > 0
        assert "age" in r["diff"]["columns_differing"]

    def test_missing_row_detected(self, manifest, oracle, candidate):
        """A missing row is `review`: a coverage gap looks exactly like this."""
        r = compare_full("age", manifest, oracle, candidate(f"{ALL_AGE} WHERE hadm_id <> 100"))
        assert r["verdict"] == "review"
        assert r["diff"]["only_oracle"] == 1
        assert r["diff"]["only_candidate"] == 0
        assert [c["class"] for c in r["divergence"]["reviewable"]] == ["only_oracle"]
        assert r["divergence"]["tier"] == "gap_shaped"
        assert r["divergence"]["blocking"] == []

    def test_extra_row_detected(self, manifest, oracle, candidate):
        """An invented row is contested, not auto-failed -- but it is not a gap."""
        sql = (f"{ALL_AGE} UNION ALL "
               "SELECT 9, 900, TIMESTAMP '2170-01-01 00:00:00', 55, 9.0")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "review"
        assert r["divergence"]["tier"] == "contested"
        assert [c["class"] for c in r["divergence"]["contested"]] == ["only_candidate"]
        assert r["divergence"]["gap_shaped"] == []
        assert r["diff"]["only_candidate"] == 1
        assert r["diff"]["only_oracle"] == 0

    def test_names_the_differing_column(self, manifest, oracle, candidate):
        """A diagnosis needs a column name, not just 'counts differ'."""
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["diff"]["columns_differing"] == {"age": 4}
        assert any("column 'age' conflicts on 4 row(s)" in d for d in r["diagnostics"])

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
        # A value tolerance never absorbs a missing row: it still surfaces as
        # `only_oracle`, which is reviewable but never silently equal.
        assert r["row_count"]["match"] is False
        assert r["row_count"]["gated"] is False
        assert r["diff"]["only_oracle"] == 1
        assert r["verdict"] == "review"

    def test_float_within_tolerance_matches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age, ratio * 1.0001 AS ratio "
               "FROM mimiciv_derived.age")
        assert compare_full("age", manifest, oracle, candidate(sql))["verdict"] == "match"

    def test_float_outside_tolerance_conflicts(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age, ratio * 1.05 AS ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["divergence"]["tier"] == "contested"
        assert r["diff"]["differing_conflict"] == len(ROWS)
        assert "ratio" in r["diff"]["columns_differing"]

    def test_integers_compared_exactly(self, manifest, oracle, candidate):
        """Tolerance must not leak into integer columns."""
        r = compare_full(
            "age", manifest, oracle,
            candidate("SELECT subject_id, hadm_id, admittime, age + 1 AS age, "
                      "ratio FROM mimiciv_derived.age"),
        )
        assert r["verdict"] != "match"
        assert r["diff"]["differing_conflict"] == len(ROWS)

    def test_timestamp_within_one_second_matches(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime + INTERVAL 500 MILLISECOND "
               "AS admittime, age, ratio FROM mimiciv_derived.age")
        assert compare_full("age", manifest, oracle, candidate(sql))["verdict"] == "match"

    def test_timestamp_beyond_tolerance_conflicts(self, manifest, oracle, candidate):
        """The shape of the real DST-shift divergence: a value conflict.

        `age`'s 44 shifted admission times reach the judge as `contested`
        rather than hard-failing, because the shift happened in
        `fhir_encounter.sql`, not in the port.
        """
        sql = ("SELECT subject_id, hadm_id, admittime + INTERVAL 5 MINUTE AS admittime, "
               "age, ratio FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "review"
        assert r["divergence"]["tier"] == "contested"
        assert "admittime" in r["diff"]["columns_differing"]

    def test_candidate_null_for_a_value_is_gap_shaped(
        self, manifest, oracle, candidate
    ):
        """NULL where the oracle has a value is the shape of a missing element.

        Still a divergence -- never silently equal -- but `differing_null_only`
        rather than a conflict, so the judge rules at the lower of the two bars.
        """
        sql = ("SELECT subject_id, hadm_id, admittime, age, NULL::DOUBLE AS ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql))
        assert r["verdict"] == "review"
        assert r["divergence"]["tier"] == "gap_shaped"
        assert r["diff"]["differing_null_only"] == len(ROWS)
        assert r["diff"]["differing_conflict"] == 0
        assert "ratio" in r["diff"]["columns_candidate_null"]
        assert "ratio" in r["diff"]["columns_differing"]

    def test_candidate_value_for_an_oracle_null_is_contested(
        self, manifest, oracle, candidate
    ):
        """The mirror case is a conflict: a gap cannot make the candidate fuller.

        It reaches the judge, but at the raised bar -- an absent element does
        not explain a value the oracle does not have.
        """
        cand = candidate(ALL_AGE, name="filled")  # built while ratio still has values
        con = duckdb.connect(str(oracle))
        con.execute("UPDATE mimiciv_derived.age SET ratio = NULL WHERE hadm_id = 100")
        con.close()
        r = compare_full("age", manifest, oracle, cand)
        assert r["verdict"] == "review"
        assert r["divergence"]["tier"] == "contested"
        assert r["divergence"]["judge_bar"]
        assert r["diff"]["differing_conflict"] == 1

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
        sample = r["diff"]["samples"]["differing_conflict"][0]
        assert sample["age__candidate"] == sample["age__oracle"] + 1

    def test_sample_limit_respected(self, manifest, oracle, candidate):
        sql = ("SELECT subject_id, hadm_id, admittime, age + 1 AS age, ratio "
               "FROM mimiciv_derived.age")
        r = compare_full("age", manifest, oracle, candidate(sql), sample_limit=2)
        assert len(r["diff"]["samples"]["differing_conflict"]) == 2

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
        # No key: `only_candidate` and a NULL divergence are indistinguishable,
        # so an unkeyed concept routes to the judge instead of hard-failing.
        assert r["verdict"] == "review"
        assert r["divergence"]["classification"] == "unavailable_no_key"
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
# residual pairing -- recovering the classification a missing key withheld
# ---------------------------------------------------------------------------


class TestResidualPairing:
    """The evidence `only_oracle == only_candidate` was being read as.

    That equality is an identity, not a finding: ``EXCEPT ALL`` is multiset
    difference, so the two counts differ by exactly the row-count difference.
    Equal row counts force equal counts for *every* candidate, however wrong.
    These tests pin the real check that replaced it.
    """

    ALL = "SELECT * FROM mimiciv_derived.meds"

    def test_dropped_timestamps_pair_and_are_gap_shaped(
        self, manifest, oracle, candidate
    ):
        """The acei/arb/antibiotic shape: the ETL drops both interval endpoints.

        Every row still exists and only the two timestamps went NULL, so this is
        a coverage gap. Before pairing it presented as `only_candidate` and was
        forced to the `contested` bar, which demanded an ETL citation for what
        is an absent element.
        """
        sql = f"""SELECT subject_id, hadm_id, drug,
                         CASE WHEN drug = 'Lisinopril' THEN NULL ELSE starttime END
                             AS starttime,
                         CASE WHEN drug = 'Lisinopril' THEN NULL ELSE stoptime END
                             AS stoptime
                  FROM ({self.ALL})"""
        r = compare_full("meds", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["classification"] == "paired_residual"
        assert diff["residual_pairing"]["paired"] == 2
        assert diff["residual_pairing"]["pairing_columns"] == [
            "drug", "hadm_id", "subject_id",
        ]
        assert diff["residual_pairing"]["substituted_columns"] == [
            "starttime", "stoptime",
        ]
        # The point of the whole exercise: gap_shaped, not contested.
        assert div["tier"] == "gap_shaped"
        assert diff["differing_null_only"] == 2
        assert diff["differing_conflict"] == 0
        assert diff["columns_candidate_null"] == {"starttime": 2, "stoptime": 2}
        # A paired residual knows how many rows survived untouched, which an
        # unkeyed concept previously could not state at all.
        assert diff["identical"] == 2

    def test_rewritten_timestamp_pairs_and_is_contested(
        self, manifest, oracle, candidate
    ):
        """A rewritten value is present on both sides and disagrees."""
        sql = f"""SELECT subject_id, hadm_id, drug,
                         starttime + INTERVAL 1 HOUR AS starttime, stoptime
                  FROM ({self.ALL}) WHERE subject_id = 2
                  UNION ALL SELECT * FROM ({self.ALL}) WHERE subject_id <> 2"""
        r = compare_full("meds", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["classification"] == "paired_residual"
        assert div["tier"] == "contested"
        assert diff["differing_conflict"] == 1
        assert diff["columns_conflicting"] == {"starttime": 1}
        # `2151-03-12 02:30` is a Friday, so a plain +1h is NOT the upstream
        # DST cast. Attribution must not fire on the arithmetic alone.
        assert diff["conflict_attribution"]["complete"] is False
        assert diff["conflict_attribution"]["attributed_rows"] == 0
        assert div["attributed"] == []

    def test_invented_row_does_not_pair(self, manifest, oracle, candidate):
        """A row the oracle never had must not be absorbed as a substitution."""
        sql = f"""SELECT * FROM ({self.ALL}) WHERE subject_id <> 3
                  UNION ALL SELECT 9, 900, 'Enalapril',
                                   TIMESTAMP '2160-01-01 08:00:00',
                                   TIMESTAMP '2160-01-02 08:00:00'"""
        r = compare_full("meds", manifest, oracle, candidate(sql))
        diff = r["diff"]

        assert diff["classification"] == "unavailable_no_key"
        assert diff["only_oracle"] == 1
        assert diff["only_candidate"] == 1
        assert r["divergence"]["tier"] == "contested"

    def test_tautology_is_named_when_the_residual_does_not_pair(
        self, manifest, oracle, candidate
    ):
        """The equal counts must be labelled as vacuous where they appear."""
        sql = f"""SELECT * FROM ({self.ALL}) WHERE subject_id <> 3
                  UNION ALL SELECT 9, 900, 'Enalapril',
                                   TIMESTAMP '2160-01-01 08:00:00',
                                   TIMESTAMP '2160-01-02 08:00:00'"""
        r = compare_full("meds", manifest, oracle, candidate(sql))
        notes = " ".join(r["divergence"]["notes"])
        assert "NOT evidence" in notes
        assert "row-count difference" in notes

    def test_pairing_without_an_identity_column_is_not_claimed(
        self, manifest, oracle, candidate
    ):
        """Pairing on values alone aligns unrelated rows; refuse to call it proof."""
        sql = "SELECT label, amount + 1 AS amount FROM mimiciv_derived.anon"
        r = compare_full("anon", manifest, oracle, candidate(sql))
        pairing = r["diff"]["residual_pairing"]

        assert pairing["unpaired_oracle"] == 0  # it *does* pair on `label`
        assert pairing["anchored"] is False
        # ...but an unanchored pairing does not earn the classification.
        assert r["diff"]["classification"] == "unavailable_no_key"

    def test_identical_result_attempts_no_pairing(self, manifest, oracle, candidate):
        r = compare_full("meds", manifest, oracle, candidate(self.ALL))
        assert r["verdict"] == "match"
        assert r["diff"]["residual_pairing"]["attempted"] is False


# ---------------------------------------------------------------------------
# upstream-ETL attribution
# ---------------------------------------------------------------------------


class TestUpstreamAttribution:
    """The conflict class the comparator can now explain by itself.

    `mimic-fhir` casts naive MIMIC wall times through `TIMESTAMPTZ`, which is
    not the identity inside the DST spring-forward gap. That operation is
    replayable, so a `differing_conflict` that reproduces it is provably
    upstream transformation loss rather than a port bug -- established here over
    every conflicting row, not a sample.

    The tests are weighted towards the ways attribution must *refuse*: a
    licence to call any inconvenient conflict "upstream" would be far worse than
    the diagnosis it replaces.
    """

    ALL = "SELECT * FROM mimiciv_derived.dst"

    #: What the upstream cast writes for the two gap rows. Literal rather than
    #: computed, so the candidate is a stand-in for the ETL's output and the
    #: replay is exercised only inside the comparator.
    REPLAYED = f"""SELECT subject_id, hadm_id,
                          CASE hadm_id
                              WHEN 100 THEN TIMESTAMP '2153-03-11 03:30:00'
                              WHEN 200 THEN TIMESTAMP '2181-03-11 03:52:00'
                              ELSE charttime END AS charttime,
                          value
                   FROM ({ALL})"""

    def test_replayed_dst_shift_is_attributed_not_contested(
        self, manifest, oracle, candidate
    ):
        """The cardiac_marker / enzyme / complete_blood_count shape."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        diff, div = r["diff"], r["divergence"]

        assert diff["differing_conflict"] == 2
        assert diff["columns_conflicting"] == {"charttime": 2}

        attribution = diff["conflict_attribution"]
        assert attribution["attempted"] is True
        assert attribution["complete"] is True
        assert attribution["conflict_rows"] == 2
        assert attribution["attributed_rows"] == 2
        assert attribution["residual_rows"] == 0
        assert attribution["columns"] == {"charttime": 2}
        assert attribution["timezone"] == "America/New_York"

        # The whole point: out of `contested`, into `attributed`.
        assert div["tier"] == "attributed"
        assert div["contested"] == []
        assert div["blocking"] == []
        assert [item["class"] for item in div["attributed"]] == ["differing_conflict"]
        assert div["attributed"][0]["attributed_rows"] == 2

    def test_attribution_never_produces_a_match(self, manifest, oracle, candidate):
        """The values still differ from the oracle; only a judge may accept that."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))

        assert r["verdict"] == "review"
        assert r["match"] is False
        assert r["divergence"]["judge_required"] is True

    def test_the_judge_is_never_skipped_but_the_diagnostician_is(
        self, manifest, oracle, candidate
    ):
        """The saving is the diagnosis, never the final guard."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        div = r["divergence"]

        assert div["judge_required"] is True
        assert div["diagnostician_required"] is False

    def test_contested_still_requires_the_diagnostician(
        self, manifest, oracle, candidate
    ):
        sql = f"""SELECT subject_id, hadm_id, charttime, value + 100 AS value
                  FROM ({self.ALL})"""
        r = compare_full("dst", manifest, oracle, candidate(sql))

        assert r["divergence"]["tier"] == "contested"
        assert r["divergence"]["diagnostician_required"] is True

    def test_citations_and_the_confirmation_obligation_travel_with_the_finding(
        self, manifest, oracle, candidate
    ):
        """The judge must not have to go and find the citation itself."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        item = r["divergence"]["attributed"][0]

        assert any("fhir_encounter.sql" in c for c in item["citations"])
        assert "TIMESTAMPTZ" in item["proof"]
        assert "fraction" in item["judge_must_confirm"]

    def test_the_bar_names_what_the_replay_does_not_prove(
        self, manifest, oracle, candidate
    ):
        """Provenance and shape stay the judge's, explicitly."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        bar = r["divergence"]["judge_bar"]

        assert "PROVENANCE" in bar
        assert "SHAPE" in bar
        # The falsification test: a large fraction argues against attribution.
        assert "`bug`" in bar

    def test_a_plain_hour_shift_off_a_gap_date_is_not_attributed(
        self, manifest, oracle, candidate
    ):
        """`+1 hour` is not the signature; reproducing the *cast* is.

        The two ordinary rows are outside the gap, so round-tripping them
        through the zone is the identity and a shifted candidate cannot match it.
        A diagnostician reading "differs by exactly an hour" off a sample would
        get this wrong.
        """
        sql = f"""SELECT subject_id, hadm_id,
                         charttime + INTERVAL 1 HOUR AS charttime, value
                  FROM ({self.ALL}) WHERE hadm_id IN (300, 400)
                  UNION ALL SELECT * FROM ({self.ALL}) WHERE hadm_id IN (100, 200)"""
        r = compare_full("dst", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["differing_conflict"] == 2
        assert diff["conflict_attribution"]["attributed_rows"] == 0
        assert diff["conflict_attribution"]["complete"] is False
        assert div["tier"] == "contested"
        assert div["attributed"] == []

    def test_partial_attribution_stays_contested(self, manifest, oracle, candidate):
        """Unexplained rows decide the bar, however many explained ones sit beside them."""
        sql = f"""SELECT subject_id, hadm_id,
                         CASE hadm_id
                             WHEN 100 THEN TIMESTAMP '2153-03-11 03:30:00'
                             WHEN 200 THEN TIMESTAMP '2181-03-11 03:52:00'
                             ELSE charttime + INTERVAL 1 HOUR END AS charttime,
                         value
                  FROM ({self.ALL})"""
        r = compare_full("dst", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["differing_conflict"] == 4
        assert diff["conflict_attribution"]["attributed_rows"] == 2
        assert diff["conflict_attribution"]["residual_rows"] == 2
        assert diff["conflict_attribution"]["complete"] is False
        assert div["tier"] == "contested"
        assert div["attributed"] == []
        assert div["diagnostician_required"] is True
        # ...but the diagnostician is told not to re-derive the explained half.
        notes = " ".join(div["notes"])
        assert "2 do not" in notes and "residual rows" in notes

    def test_a_non_datetime_conflict_on_the_same_row_blocks_attribution(
        self, manifest, oracle, candidate
    ):
        """The row is the unit: one unexplained column leaves the whole row out."""
        sql = f"""SELECT subject_id, hadm_id,
                         CASE hadm_id
                             WHEN 100 THEN TIMESTAMP '2153-03-11 03:30:00'
                             WHEN 200 THEN TIMESTAMP '2181-03-11 03:52:00'
                             ELSE charttime END AS charttime,
                         CASE WHEN hadm_id = 100 THEN value + 100 ELSE value END
                             AS value
                  FROM ({self.ALL})"""
        r = compare_full("dst", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["differing_conflict"] == 2
        # Row 200 replays; row 100 also has a `value` conflict nothing explains.
        assert diff["conflict_attribution"]["attributed_rows"] == 1
        assert diff["conflict_attribution"]["complete"] is False
        assert div["tier"] == "contested"

    def test_attribution_alongside_a_gap_is_gap_shaped_with_the_addendum(
        self, manifest, oracle, candidate
    ):
        """A gap the judge must still rule on outranks the attributed conflict."""
        sql = f"""SELECT subject_id, hadm_id,
                         CASE hadm_id
                             WHEN 100 THEN TIMESTAMP '2153-03-11 03:30:00'
                             WHEN 200 THEN TIMESTAMP '2181-03-11 03:52:00'
                             ELSE charttime END AS charttime,
                         CASE WHEN hadm_id = 300 THEN NULL ELSE value END AS value
                  FROM ({self.ALL})"""
        r = compare_full("dst", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["differing_conflict"] == 2
        assert diff["differing_null_only"] == 1
        assert div["tier"] == "gap_shaped"
        assert div["contested"] == []
        assert len(div["attributed"]) == 1
        # The gap bar, plus a pointer so the attribution is not absorbed silently.
        assert "coverage gap" not in div["judge_bar"] or "machine-attributed" in div["judge_bar"]
        assert "machine-attributed" in div["judge_bar"]
        # The diagnostician is still not needed: nothing contested remains.
        assert div["diagnostician_required"] is False

    def test_a_match_carries_no_attribution_at_all(self, manifest, oracle, candidate):
        """Attribution can lower a bar, so it must not appear where none is needed."""
        r = compare_full("dst", manifest, oracle, candidate(self.ALL))

        assert r["verdict"] == "match"
        assert "conflict_attribution" not in r["diff"]
        assert r["divergence"]["tier"] == "none"
        assert r["divergence"]["attributed"] == []
        assert r["divergence"]["conflict_attribution"] is None

    def test_attribution_does_not_depend_on_samples(
        self, manifest, oracle, candidate
    ):
        """It is a count over every conflicting row, not a read of the sample."""
        r = compare_full(
            "dst", manifest, oracle, candidate(self.REPLAYED), sample_limit=0
        )
        attribution = r["diff"]["conflict_attribution"]

        assert attribution["complete"] is True
        assert attribution["attributed_rows"] == 2
        assert "samples" not in attribution
        assert r["divergence"]["tier"] == "attributed"

    def test_samples_show_the_replayed_value_beside_both_sides(
        self, manifest, oracle, candidate
    ):
        """The judge should be able to eyeball the proof without re-running SQL."""
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        sample = r["diff"]["conflict_attribution"]["samples"][0]

        assert sample["charttime__replayed"] == sample["charttime__candidate"]
        assert sample["charttime__replayed"] != sample["charttime__oracle"]

    def test_a_concept_with_no_datetime_column_is_not_attempted(
        self, manifest, oracle, candidate
    ):
        sql = "SELECT label, amount + 1 AS amount FROM mimiciv_derived.anon"
        r = compare_full("anon", manifest, oracle, candidate(sql))
        attribution = (r["diff"].get("residual_pairing") or {}).get(
            "conflict_attribution"
        )

        if attribution is not None:  # only reached if the residual paired
            assert attribution["attempted"] is False
            assert "no datetime column" in attribution["why"]

    def test_unkeyed_paired_residual_earns_the_same_attribution(
        self, manifest, oracle, candidate
    ):
        """An unkeyed concept whose residual paired is diagnosed like a keyed one."""
        sql = """SELECT subject_id, drug,
                        CASE subject_id
                            WHEN 1 THEN TIMESTAMP '2153-03-11 03:30:00'
                            WHEN 2 THEN TIMESTAMP '2181-03-11 03:52:00'
                            ELSE starttime END AS starttime
                 FROM mimiciv_derived.dst_unkeyed"""
        r = compare_full("dst_unkeyed", manifest, oracle, candidate(sql))
        diff, div = r["diff"], r["divergence"]

        assert diff["classification"] == "paired_residual"
        assert diff["differing_conflict"] == 2
        assert diff["conflict_attribution"]["complete"] is True
        assert diff["conflict_attribution"]["attributed_rows"] == 2
        assert div["tier"] == "attributed"
        assert div["judge_required"] is True
        assert div["diagnostician_required"] is False

    def test_no_zone_database_means_no_attribution_and_no_fallback(
        self, manifest, oracle, candidate, monkeypatch
    ):
        """Without the ETL's zone rules the conflict stays the diagnostician's.

        There is deliberately no hand-rolled "second Sunday in March" fallback:
        a weaker proof under the same tier name is the erosion this tier exists
        to avoid. Degrading to today's behaviour is the correct failure.
        """
        import mimic_utils.compare_port_results as cpr

        monkeypatch.setattr(
            cpr, "_dst_replay_available", lambda con: "icu extension not available"
        )
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        diff, div = r["diff"], r["divergence"]

        assert diff["conflict_attribution"]["attempted"] is False
        assert diff["conflict_attribution"]["complete"] is False
        assert div["tier"] == "contested"
        assert div["attributed"] == []
        assert div["diagnostician_required"] is True
        assert "not attempted" in " ".join(div["notes"])

    def test_the_sample_payload_is_not_duplicated_into_divergence(
        self, manifest, oracle, candidate
    ):
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))

        assert r["diff"]["conflict_attribution"]["samples"]
        assert "samples" not in r["divergence"]["conflict_attribution"]
        # ...but the counts and provenance are on both, so either is routable.
        assert r["divergence"]["conflict_attribution"]["complete"] is True
        assert r["divergence"]["conflict_attribution"]["citations"]

    def test_diagnostics_state_the_attribution_and_the_obligation(
        self, manifest, oracle, candidate
    ):
        r = compare_full("dst", manifest, oracle, candidate(self.REPLAYED))
        text = "\n".join(r["diagnostics"])

        assert "ATTRIBUTED" in text
        assert "fhir_encounter.sql" in text
        assert "judge still rules" in text

    def test_attributed_result_exits_unsure_not_fail(
        self, manifest, oracle, candidate, tmp_path
    ):
        """`review` is not a failure, and this tier reads least like one."""
        out = tmp_path / "attributed.json"
        rc = compare_port_results_cli([
            "full", "--concept", "dst", "--manifest", str(manifest),
            "--oracle", str(oracle), "--candidate", str(candidate(self.REPLAYED)),
            "--output", str(out),
        ])
        assert rc == EXIT_UNSURE
        assert json.loads(out.read_text())["divergence"]["tier"] == "attributed"

    @pytest.mark.parametrize("tier_sql,tier", [
        (REPLAYED, "attributed"),
        ("SELECT subject_id, hadm_id, charttime, value + 100 AS value "
         "FROM mimiciv_derived.dst", "contested"),
        ("SELECT subject_id, hadm_id, charttime, NULL::DOUBLE AS value "
         "FROM mimiciv_derived.dst", "gap_shaped"),
    ])
    def test_every_review_tier_exits_unsure_on_both_entry_points(
        self, manifest, oracle, candidate, tmp_path, tier_sql, tier
    ):
        """`mimic_utils compare-port-results` had no `review` branch at all.

        It reimplemented the reporting tail instead of sharing it, and the copy
        never grew one -- so every `review`, at every tier, exited 1. A caller
        reading that as failure turns "the judge must look at this" into "this
        port is wrong", which is precisely what the exit-code contract exists to
        prevent. Both entry points are pinned here so the copy cannot drift again.
        """
        from mimic_utils.__main__ import _compare_port_results_command

        cand = candidate(tier_sql, name=f"cand_{tier}")
        rc_lib = compare_port_results_cli([
            "full", "--concept", "dst", "--manifest", str(manifest),
            "--oracle", str(oracle), "--candidate", str(cand),
            "--output", str(tmp_path / f"{tier}_lib.json"),
        ])
        rc_main = _compare_port_results_command(
            mode="full", concept="dst", manifest=str(manifest), oracle=str(oracle),
            candidate=str(cand), output=str(tmp_path / f"{tier}_main.json"),
        )

        artifact = json.loads((tmp_path / f"{tier}_lib.json").read_text())
        assert artifact["divergence"]["tier"] == tier
        assert artifact["verdict"] == "review"
        assert rc_lib == EXIT_UNSURE
        assert rc_main == EXIT_UNSURE


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
        assert json.loads(out.read_text())["diff"]["samples"]["differing_conflict"]

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
        """A self-refuting declaration exits 1 -- nothing for the judge to weigh."""
        rc = self._run(
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(ALL_AGE)),
            "--oracle", str(oracle), "--output", str(tmp_path / "o.json"),
            # `ratio` is populated in ALL_AGE, so the declaration refutes itself.
            "--unrepresentable", str(_declare(tmp_path, {"ratio": _WHY})),
        )
        assert rc == EXIT_FAIL

    def test_full_contested_exit_2(self, manifest, oracle, candidate, tmp_path):
        """A conflict is no longer exit 1: it is a question, not a verdict.

        An invented row used to hard-fail here. It now routes to the judge at
        the raised bar, so the exit code must say "neither pass nor fail".
        """
        sql = (f"{ALL_AGE} UNION ALL "
               "SELECT 9, 900, TIMESTAMP '2170-01-01 00:00:00', 55, 9.0")
        out = tmp_path / "o.json"
        rc = self._run(
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(sql)),
            "--oracle", str(oracle), "--output", str(out),
        )
        assert rc == EXIT_UNSURE
        assert json.loads(out.read_text())["divergence"]["tier"] == "contested"

    def test_full_review_exit_2(self, manifest, oracle, candidate, tmp_path):
        """Gap-shaped divergence is neither pass nor fail -- the judge decides.

        Collapsing this onto 1 would turn "look at this" into "this is wrong".
        """
        rc = self._run(
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(f"{ALL_AGE} WHERE hadm_id <> 100")),
            "--oracle", str(oracle), "--output", str(tmp_path / "o.json"),
        )
        assert rc == EXIT_UNSURE
        written = json.loads((tmp_path / "o.json").read_text())
        assert written["verdict"] == "review"
        assert written["divergence"]["judge_required"] is True

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


# ---------------------------------------------------------------------------
# declared-unrepresentable columns
#
# The rule under test: a column MIMIC-on-FHIR cannot represent must be emitted
# as a typed NULL and declared. A NULL is reviewable; an estimate is blocking.
# The declaration is verified against the data, never trusted.
# ---------------------------------------------------------------------------

NULL_RATIO = (
    "SELECT subject_id, hadm_id, admittime, age, CAST(NULL AS DOUBLE) AS ratio "
    "FROM mimiciv_derived.age"
)

_WHY = "No FHIR element carries this; Patient.birthDate collapses the pair."


def _declare(tmp_path, mapping, name=UNREPRESENTABLE_FILENAME):
    path = tmp_path / name
    path.write_text(json.dumps(mapping))
    return path


class TestLoadUnrepresentable:
    def test_reads_column_to_justification(self, tmp_path):
        path = _declare(tmp_path, {"ratio": _WHY})
        assert load_unrepresentable(path) == {"ratio": _WHY}

    def test_missing_file_is_an_error(self, tmp_path):
        with pytest.raises(UnrepresentableDeclarationError, match="not found"):
            load_unrepresentable(tmp_path / "nope.json")

    def test_rejects_non_object(self, tmp_path):
        path = tmp_path / "d.json"
        path.write_text(json.dumps(["ratio"]))
        with pytest.raises(UnrepresentableDeclarationError, match="JSON object"):
            load_unrepresentable(path)

    def test_rejects_invalid_json(self, tmp_path):
        path = tmp_path / "d.json"
        path.write_text("{not json")
        with pytest.raises(UnrepresentableDeclarationError, match="not valid JSON"):
            load_unrepresentable(path)

    @pytest.mark.parametrize("justification", ["", "n/a", "none", "   "])
    def test_rejects_a_token_justification(self, tmp_path, justification):
        path = _declare(tmp_path, {"ratio": justification})
        with pytest.raises(UnrepresentableDeclarationError, match="justification"):
            load_unrepresentable(path)


class TestUnrepresentableVerification:
    def test_all_null_declared_column_is_confirmed_and_still_review(
        self, tmp_path, manifest, oracle, candidate
    ):
        """A verified declaration is evidence, not a verdict: still `review`."""
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"ratio": _WHY},
        )
        assert result["verdict"] == "review"
        assert result["unrepresentable"]["confirmed"] == {"ratio": _WHY}
        assert result["unrepresentable"]["violations"] == []
        # the justification reaches the judge alongside the divergence
        assert result["divergence"]["declared_unrepresentable"] == {"ratio": _WHY}
        assert any(
            "declared unrepresentable" in line for line in result["diagnostics"]
        )

    def test_a_confirmed_declaration_gets_a_representable_fidelity_figure(
        self, manifest, oracle, candidate
    ):
        """A by-design NULL column drives `identical` to zero. It must not be
        the only number reported.

        This is the `age` reading problem exactly: 0 of 431,231 identical, while
        every representable value on 430,727 of those rows was reproduced. Both
        figures are reported; the honest total is not replaced.
        """
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"ratio": _WHY},
        )
        d = result["divergence"]
        assert d["identical_rows"] == 0
        assert d["identical_fraction"] == 0.0
        assert d["identical_representable_rows"] == len(ROWS)
        assert d["representable_fraction"] == 1.0
        assert d["representable_excludes"] == ["ratio"]
        assert any("on the representable columns" in x for x in result["diagnostics"])

    def test_no_declaration_means_no_second_fidelity_figure(
        self, manifest, oracle, candidate
    ):
        """With nothing excluded the two numbers would be identical, and a
        duplicated figure invites the reader to think it means something."""
        d = compare_full("age", manifest, oracle, candidate(ALL_AGE))["divergence"]
        assert d["identical_fraction"] == 1.0
        assert "representable_fraction" not in d

    def test_declaring_a_column_then_emitting_values_is_blocking(
        self, tmp_path, manifest, oracle, candidate
    ):
        """The estimate-instead-of-NULL failure the declaration exists to catch."""
        result = compare_full(
            "age", manifest, oracle, candidate(ALL_AGE),
            unrepresentable={"ratio": _WHY},
        )
        assert result["verdict"] == "mismatch"
        violations = result["unrepresentable"]["violations"]
        assert [v["column"] for v in violations] == ["ratio"]
        assert violations[0]["non_null_rows"] == len(ROWS)
        assert any(
            b["class"] == "false_unrepresentable_declaration"
            for b in result["divergence"]["blocking"]
        )

    def test_declaring_an_unknown_column_is_blocking(
        self, manifest, oracle, candidate
    ):
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"anchor_year": _WHY},
        )
        assert result["verdict"] == "mismatch"
        assert "not a column" in result["unrepresentable"]["violations"][0]["reason"]

    def test_declaring_a_key_column_voids_the_diff_and_reaches_the_judge(
        self, manifest, oracle, candidate
    ):
        """A key column is the one violation the port did not cause.

        The manifest key is chosen by empirical uniqueness over relational
        MIMIC, blind to what MIMIC-on-FHIR carries, so it can land on a column
        no port could supply -- `epinephrine` keyed on `linkorderid` because
        `(stay_id, starttime)` was not unique at full scale. The keyed join
        then aligns nothing and the counts are void, but that is the
        instrument failing, not the port contradicting itself, and only the
        judge may end a concept on a semantic gap. So: `review`, with the
        diff explicitly marked void, rather than a mechanical `mismatch`.
        """
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"hadm_id": _WHY},
        )
        assert result["verdict"] == "review"
        violation = result["unrepresentable"]["violations"][0]
        assert violation["kind"] == "key_column"
        assert "natural key" in violation["reason"]
        # The violation is still recorded, but never as a blocking class.
        blocking = result["divergence"]["blocking"]
        assert not any(
            item["class"] == "false_unrepresentable_declaration" for item in blocking
        )
        assert any("VOID DIFF" in note for note in result["divergence"]["notes"])

    def test_unpaired_counts_survive_an_all_null_key_column(
        self, manifest, oracle, candidate
    ):
        """`only_oracle` must never exceed the oracle row count.

        Presence used to be tested as ``c.<first key column> IS NULL``, which
        is true both of an oracle row that found no partner *and* of a
        candidate row whose key column is a typed NULL. Every candidate-only
        row was therefore counted a second time as oracle-only.

        `epinephrine` hit this exactly: 24,470 rows a side, reported as
        ``only_oracle: 48,940`` against 24,470 oracle rows -- an arithmetic
        impossibility that reached an equivalence judge and was quoted in a
        terminal ruling. Emitting the typed NULL is the contract's *prescribed*
        way to declare an unrepresentable column, so the comparator has to
        count correctly in precisely the case the contract asks for.
        """
        null_key = (
            "SELECT subject_id, CAST(NULL AS INTEGER) AS hadm_id, admittime, "
            "age, ratio FROM mimiciv_derived.age"
        )
        result = compare_full(
            "age", manifest, oracle, candidate(null_key),
            unrepresentable={"hadm_id": _WHY},
        )
        diff = result["diff"]
        # Nothing can join, so each side is wholly unpaired -- once.
        assert diff["only_oracle"] == len(ROWS)
        assert diff["only_candidate"] == len(ROWS)
        assert diff["identical"] == 0
        assert diff["only_oracle"] <= result["divergence"]["oracle_rows"]
        # Samples are drawn by the same predicate and must not cross over.
        assert all(
            row["hadm_id"] is not None for row in diff["samples"]["only_oracle"]
        )
        assert all(
            row["hadm_id"] is None for row in diff["samples"]["only_candidate"]
        )

    def test_declaring_a_non_key_column_and_emitting_values_still_blocks(
        self, manifest, oracle, candidate
    ):
        """The two violations the port *does* cause keep terminating by machine."""
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"age": _WHY},
        )
        assert result["verdict"] == "mismatch"
        violation = result["unrepresentable"]["violations"][0]
        assert violation["kind"] == "emitted_values"

    def test_undeclared_all_null_column_is_noted_not_failed(
        self, manifest, oracle, candidate
    ):
        """An unreported gap is surfaced, but it is not itself a failure."""
        result = compare_full(
            "age", manifest, oracle, candidate(NULL_RATIO),
            unrepresentable={"age": "Placeholder justification naming an element."},
        )
        # `age` is declared but populated -> blocking; `ratio` is the undeclared one
        assert "ratio" in result["unrepresentable"]["undeclared_fully_null_columns"]

    def test_declaration_cannot_rescue_a_real_conflict(
        self, manifest, oracle, candidate
    ):
        """Declaring one column does not excuse a conflict in another.

        The declaration is confirmed and `ratio`'s NULLs become gap-shaped, but
        `age` still conflicts, and a conflict outranks a gap: the result is
        `contested`, not the gap-shaped review the declaration alone would earn.
        """
        sql = (
            "SELECT subject_id, hadm_id, admittime, age + 1 AS age, "
            "CAST(NULL AS DOUBLE) AS ratio FROM mimiciv_derived.age"
        )
        result = compare_full(
            "age", manifest, oracle, candidate(sql),
            unrepresentable={"ratio": _WHY},
        )
        assert result["verdict"] == "review"
        assert result["divergence"]["tier"] == "contested"
        assert result["unrepresentable"]["confirmed"] == {"ratio": _WHY}
        assert result["diff"]["columns_conflicting"] == {"age": len(ROWS)}

    def test_no_declaration_leaves_the_result_unchanged(
        self, manifest, oracle, candidate
    ):
        result = compare_full("age", manifest, oracle, candidate(NULL_RATIO))
        assert result["verdict"] == "review"
        assert "unrepresentable" not in result
        assert result["divergence"]["declared_unrepresentable"] == {}


class TestUnrepresentableCli:
    def test_full_mode_accepts_the_flag(self, tmp_path, manifest, oracle, candidate):
        rc = compare_port_results_cli([
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(NULL_RATIO)),
            "--oracle", str(oracle),
            "--unrepresentable", str(_declare(tmp_path, {"ratio": _WHY})),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == EXIT_UNSURE  # review
        written = json.loads((tmp_path / "out.json").read_text())
        assert written["unrepresentable"]["confirmed"] == {"ratio": _WHY}

    def test_false_declaration_exits_fail(self, tmp_path, manifest, oracle, candidate):
        rc = compare_port_results_cli([
            "full", "--concept", "age", "--manifest", str(manifest),
            "--candidate", str(candidate(ALL_AGE)), "--oracle", str(oracle),
            "--unrepresentable", str(_declare(tmp_path, {"ratio": _WHY})),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == EXIT_FAIL

    def test_shape_mode_rejects_the_flag(self, tmp_path, manifest, candidate):
        with pytest.raises(SystemExit):
            compare_port_results_cli([
                "shape", "--concept", "age", "--manifest", str(manifest),
                "--candidate", str(candidate(NULL_RATIO)),
                "--unrepresentable", str(_declare(tmp_path, {"ratio": _WHY})),
                "--output", str(tmp_path / "out.json"),
            ])


# ---------------------------------------------------------------------------
# DST shift that lands in the natural key
# ---------------------------------------------------------------------------

#: The upstream cast, as the candidate would have received it: gap wall times
#: move forward an hour, everything else is untouched.
_SHIFT = (
    "timezone('America/New_York', "
    "timezone('America/New_York', CAST(charttime AS TIMESTAMP)))"
)


class TestKeyAttribution:
    """A shift in a key column reads as row-missing plus row-invented.

    `conflict_attribution` cannot see it -- it partitions the *conflict* set,
    and a row that never joined never conflicts. Six chartevents concepts key on
    `charttime`, saw `{"attempted": false}`, and had the documented `attributed`
    route closed to them. These tests pin it open.
    """

    def _compare(self, manifest, oracle, candidate, sql):
        return compare_full("dst_keyed_time", manifest, oracle, candidate(sql))

    def test_shifted_key_is_attributed_on_both_sides(
        self, manifest, oracle, candidate
    ):
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time"""
        diff = self._compare(manifest, oracle, candidate, sql)["diff"]

        # One gap row: it left its key, so it is missing *and* invented.
        assert diff["only_oracle"] == 1
        assert diff["only_candidate"] == 1

        attr = diff["key_attribution"]
        assert attr["attempted"] is True
        assert attr["keys_considered"] == ["charttime"]
        assert attr["attributed_only_oracle"] == 1
        assert attr["attributed_only_candidate"] == 1
        assert attr["residual_only_oracle"] == 0
        assert attr["residual_only_candidate"] == 0
        assert attr["complete"] is True

    def test_sample_shows_the_replayed_key(self, manifest, oracle, candidate):
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time"""
        attr = self._compare(manifest, oracle, candidate, sql)["diff"][
            "key_attribution"
        ]
        sample = attr["samples"][0]
        assert str(sample["charttime"]) == "2153-03-11 02:30:00"
        assert str(sample["charttime__replayed"]) == "2153-03-11 03:30:00"

    def test_complete_attribution_moves_both_classes_out_of_their_tiers(
        self, manifest, oracle, candidate
    ):
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time"""
        div = self._compare(manifest, oracle, candidate, sql)["divergence"]

        moved = {"only_oracle", "only_candidate"}
        assert {item["class"] for item in div["attributed"]} == moved
        # Neither class may remain where it started: `only_candidate` in
        # `contested` would bill the port for a row it never invented, and
        # `only_oracle` in `gap_shaped` would name an absent element that is
        # not absent.
        assert not [i for i in div["gap_shaped"] if i["class"] in moved]
        assert not [i for i in div["contested"] if i["class"] in moved]
        assert div["verdict"] == "review"

    def test_attributed_rows_carry_the_citation_and_the_judge_instruction(
        self, manifest, oracle, candidate
    ):
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time"""
        div = self._compare(manifest, oracle, candidate, sql)["divergence"]
        item = next(i for i in div["attributed"] if i["class"] == "only_oracle")
        assert item["citations"]
        assert item["keys"] == ["charttime"]
        # The instruction that stops the loop reaching for the id inversion again.
        assert "reconstructing a resource id" in item["judge_must_confirm"]

    def test_an_unexplained_missing_row_leaves_it_incomplete(
        self, manifest, oracle, candidate
    ):
        # Shift the gap row *and* drop an ordinary one: two `only_oracle`, only
        # one of which the replay reaches.
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time WHERE stay_id <> 3"""
        diff = self._compare(manifest, oracle, candidate, sql)["diff"]
        attr = diff["key_attribution"]
        assert attr["only_oracle"] == 2
        assert attr["attributed_only_oracle"] == 1
        assert attr["residual_only_oracle"] == 1
        assert attr["complete"] is False

    def test_an_invented_row_leaves_it_incomplete(self, manifest, oracle, candidate):
        # A candidate row the replay cannot reach is still a row the port
        # invented, however tidy the oracle side looks.
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time
                  UNION ALL
                  SELECT 9, TIMESTAMP '2199-01-01 00:00:00', 9.0"""
        attr = self._compare(manifest, oracle, candidate, sql)["diff"][
            "key_attribution"
        ]
        assert attr["attributed_only_oracle"] == 1
        assert attr["residual_only_candidate"] == 1
        assert attr["complete"] is False

    def test_incomplete_attribution_does_not_move_the_tier(
        self, manifest, oracle, candidate
    ):
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time WHERE stay_id <> 3"""
        div = self._compare(manifest, oracle, candidate, sql)["divergence"]
        assert any(i["class"] == "only_oracle" for i in div["gap_shaped"])
        assert not div["attributed"]

    def test_an_ordinary_wall_time_is_never_attributed(
        self, manifest, oracle, candidate
    ):
        # Move a non-gap row by an hour by hand. The replay is the identity on
        # it, so it must stay unexplained -- otherwise attribution would be a
        # licence to relabel any one-hour error.
        sql = """SELECT stay_id,
                        CASE WHEN stay_id = 3
                             THEN charttime + INTERVAL 1 HOUR ELSE charttime END
                        AS charttime,
                        value
                 FROM mimiciv_derived.dst_keyed_time"""
        attr = self._compare(manifest, oracle, candidate, sql)["diff"][
            "key_attribution"
        ]
        assert attr["attributed_only_oracle"] == 0
        assert attr["complete"] is False

    def test_not_attempted_when_no_key_column_is_a_datetime(
        self, manifest, oracle, candidate
    ):
        # `age` keys on `hadm_id`; a key shift cannot apply, and saying so is
        # more useful to the diagnostician than an empty attribution block.
        sql = "SELECT * FROM mimiciv_derived.age WHERE hadm_id <> 400"
        diff = compare_full("age", manifest, oracle, candidate(sql))["diff"]
        attr = diff["key_attribution"]
        assert attr["attempted"] is False
        assert "no datetime column in the natural key" in attr["why"]

    def test_absent_when_nothing_is_unpaired(self, manifest, oracle, candidate):
        # Attribution lowers a bar, so it must not appear on a clean result.
        sql = "SELECT * FROM mimiciv_derived.dst_keyed_time"
        diff = self._compare(manifest, oracle, candidate, sql)["diff"]
        assert "key_attribution" not in diff


# ---------------------------------------------------------------------------
# key collision -- the shift lands on a key the candidate already holds
# ---------------------------------------------------------------------------


_COLLIDE = (
    "SELECT subject_id, charttime, max(o2_flow) AS o2_flow, "
    "max(device) AS device FROM ("
    "  SELECT subject_id, timezone('America/New_York', "
    "         timezone('America/New_York', CAST(charttime AS TIMESTAMP))) AS charttime,"
    "         o2_flow, device FROM mimiciv_derived.dst_collision"
    ") GROUP BY subject_id, charttime"
)


class TestKeyCollisionAttribution:
    """One transformation was being billed as two unexplained findings.

    ``_attribute_dst_unpaired`` semi-joins the unpaired oracle rows against the
    unpaired *candidate* rows. When the replayed key is one the candidate
    already holds, the candidate row is not unpaired -- it paired with a
    different oracle row and conflicts with it -- so the semi-join missed it and
    the event was reported as an unexplained ``only_oracle`` plus an unexplained
    ``differing_conflict``. All-or-nothing then let those rows set the tier for
    the whole concept: `oxygen_delivery` reproduced 601,509 of 601,546 rows,
    had every one of its 37 divergent rows inside a March 02:00-03:00 hour, and
    was blocked on the 3 that collided.
    """

    def _compare(self, manifest, oracle, candidate, sql=_COLLIDE):
        return compare_full("dst_collision", manifest, oracle, candidate(sql))

    def test_absorbed_row_is_attributed(self, manifest, oracle, candidate):
        attr = self._compare(manifest, oracle, candidate)["diff"]["key_attribution"]
        # Subject 2 moved into an empty key; subject 1 was absorbed into 03:00.
        assert attr["attributed_only_oracle_repaired"] == 1
        assert attr["attributed_only_oracle_collided"] == 1
        assert attr["residual_only_oracle"] == 0
        assert attr["residual_only_candidate"] == 0
        assert attr["complete"] is True

    def test_the_conflict_it_caused_is_attributed_with_it(
        self, manifest, oracle, candidate
    ):
        diff = self._compare(manifest, oracle, candidate)["diff"]
        # The merged row disagrees on o2_flow: the candidate aggregated two
        # source rows where the oracle aggregated one.
        assert diff["differing_conflict"] == 1
        attr = diff["conflict_attribution"]
        assert attr["attributed_by_key_collision"] == 1
        assert attr["attributed_rows"] == 1
        assert attr["complete"] is True

    def test_tier_moves_to_attributed(self, manifest, oracle, candidate):
        div = self._compare(manifest, oracle, candidate)["divergence"]
        assert div["tier"] == "attributed"
        assert div["verdict"] == "review"
        assert not div["contested"]
        # The whole point: a diagnosis here would only re-derive the replay.
        assert div["diagnostician_required"] is False

    def test_sample_labels_which_route_each_row_took(
        self, manifest, oracle, candidate
    ):
        attr = self._compare(manifest, oracle, candidate)["diff"]["key_attribution"]
        routes = {s["_route"] for s in attr["samples"]}
        assert routes == {"repaired", "key_collision"}

    def test_a_conflict_the_collision_does_not_reach_stays_contested(
        self, manifest, oracle, candidate
    ):
        # Same collision, plus an unrelated wrong value on subject 3. The
        # collision must not launder a conflict it has nothing to do with.
        sql = (
            f"SELECT subject_id, charttime, "
            f"CASE WHEN subject_id = 3 THEN 99.0 ELSE o2_flow END AS o2_flow, "
            f"device FROM ({_COLLIDE})"
        )
        r = self._compare(manifest, oracle, candidate, sql)
        attr = r["diff"]["conflict_attribution"]
        assert attr["conflict_rows"] == 2
        assert attr["attributed_by_key_collision"] == 1
        assert attr["residual_rows"] == 1
        assert attr["complete"] is False
        assert r["divergence"]["tier"] == "contested"

    def test_an_ordinary_missing_row_is_not_a_collision(
        self, manifest, oracle, candidate
    ):
        # Drop subject 3 outright. Its key is not in the candidate at all, so
        # there is nothing for it to have collided with.
        sql = f"SELECT * FROM ({_COLLIDE}) WHERE subject_id <> 3"
        attr = self._compare(manifest, oracle, candidate, sql)["diff"][
            "key_attribution"
        ]
        assert attr["attributed_only_oracle_collided"] == 1
        assert attr["residual_only_oracle"] == 1
        assert attr["complete"] is False

    def test_collision_table_does_not_leak_between_comparisons(
        self, manifest, oracle, candidate
    ):
        # A concept with no collision must not read the previous one's keys.
        self._compare(manifest, oracle, candidate)
        sql = f"""SELECT stay_id, {_SHIFT} AS charttime, value
                  FROM mimiciv_derived.dst_keyed_time"""
        attr = compare_full("dst_keyed_time", manifest, oracle, candidate(sql))[
            "diff"
        ]["key_attribution"]
        assert attr["attributed_only_oracle_collided"] == 0
        assert attr["complete"] is True


# ---------------------------------------------------------------------------
# the unkeyed path applies the comparator's own tolerances
# ---------------------------------------------------------------------------


class TestUnkeyedTolerances:
    """A concept must not be judged on whether it was given a manifest key.

    The residual is built with ``EXCEPT ALL``, which is exact and cannot be
    otherwise. Classifying that residual exactly too reported a seventh-decimal
    float difference as a ``differing_conflict`` -- the contested class, needing
    an upstream ETL citation. `phenylephrine` reported 0.00% identical and
    190,872 conflicts that way; `dobutamine`, same table and same ETL but keyed,
    reported 99.98%.
    """

    ALL = "SELECT * FROM mimiciv_derived.infusion"
    #: What Pathling serves: the FHIR warehouse stores Quantity at scale 6.
    TRUNCATED = (
        "CAST(round(CAST(vaso_rate AS DECIMAL(32,10)), 6) AS FLOAT) AS vaso_rate"
    )
    DECLARATION = {
        "linkorderid": "No FHIR element: the ICU ETL writes no inputevent identifier."
    }

    def _candidate_sql(self, rate=None, linkorderid="CAST(NULL AS INTEGER)"):
        return (
            f"SELECT stay_id, {linkorderid} AS linkorderid, "
            f"{rate or self.TRUNCATED}, starttime FROM ({self.ALL})"
        )

    def test_float_within_tolerance_is_identical_not_a_conflict(
        self, manifest, oracle, candidate
    ):
        sql = f"SELECT stay_id, linkorderid, {self.TRUNCATED}, starttime FROM ({self.ALL})"
        r = compare_full("infusion", manifest, oracle, candidate(sql))
        diff = r["diff"]
        # Every row lands in the exact residual, and every one of them agrees
        # within the comparator's own 0.1% relative tolerance.
        assert diff["residual_pairing"]["paired"] == 4
        assert diff["residual_pairing"]["paired_equal"] == 4
        assert diff["differing_conflict"] == 0
        assert diff["identical"] == 4
        assert r["divergence"]["verdict"] == "match"

    def test_float_outside_tolerance_still_conflicts(
        self, manifest, oracle, candidate
    ):
        sql = self._candidate_sql(
            rate="CAST(vaso_rate * 2 AS FLOAT) AS vaso_rate",
            linkorderid="linkorderid",
        )
        diff = compare_full("infusion", manifest, oracle, candidate(sql))["diff"]
        assert diff["differing_conflict"] == 4
        assert diff["columns_conflicting"]["vaso_rate"] == 4

    def test_declared_column_is_kept_out_of_the_alignment(
        self, manifest, oracle, candidate
    ):
        r = compare_full(
            "infusion", manifest, oracle, candidate(self._candidate_sql()),
            unrepresentable=self.DECLARATION,
        )
        pairing = r["diff"]["residual_pairing"]
        # A 100%-NULL column in the pairing set aligns nothing and puts every
        # row in the residual; it is tallied analytically instead.
        assert "linkorderid" not in pairing["pairing_columns"]
        assert "linkorderid" not in pairing["substituted_columns"]
        assert r["diff"]["excluded_as_alignment"] == ["linkorderid"]
        assert r["diff"]["columns_candidate_null"]["linkorderid"] == 4

    def test_declared_column_reports_both_fidelity_numbers(
        self, manifest, oracle, candidate
    ):
        r = compare_full(
            "infusion", manifest, oracle, candidate(self._candidate_sql()),
            unrepresentable=self.DECLARATION,
        )
        div = r["diff"], r["divergence"]
        diff, divergence = div
        # The honest total: no row is reproduced in full, because one column is
        # NULL by design on every one of them.
        assert diff["identical"] == 0
        # The number that is about the port.
        assert diff["identical_representable"] == 4
        assert divergence["representable_fraction"] == 1.0
        assert divergence["representable_excludes"] == ["linkorderid"]

    def test_the_three_classes_still_sum(self, manifest, oracle, candidate):
        sql = self._candidate_sql(
            rate=(
                "CAST(CASE WHEN stay_id = 1 THEN vaso_rate * 2 ELSE vaso_rate END "
                "AS FLOAT) AS vaso_rate"
            )
        )
        r = compare_full(
            "infusion", manifest, oracle, candidate(sql),
            unrepresentable=self.DECLARATION,
        )
        diff = r["diff"]
        assert diff["differing_conflict"] == 2
        assert (
            diff["identical"] + diff["differing_conflict"] + diff["differing_null_only"]
            == r["divergence"]["oracle_rows"]
        )


class TestResourceKeyChecks:
    """The key contract is the one part of the output nothing else verifies.

    Keys are absent from the oracle, so both diff paths project the manifest's
    ``columns`` and skip them. A key joined off the wrong resource, or selected
    by an aggregate over a group in which it is not constant, yields a column
    that is present, correctly typed, correctly prefixed -- and wrong. It even
    joins downstream, just to the wrong row.
    """

    ACTUAL = {
        "subject_id": "INTEGER",
        "patient_key": "VARCHAR",
        "hadm_id": "INTEGER",
        "encounter_key": "VARCHAR",
    }

    def _table(self, sql):
        con = duckdb.connect()
        con.execute(f"CREATE TABLE x AS {sql}")
        return con

    def test_a_bijective_key_passes(self):
        con = self._table(
            "SELECT 1 subject_id, 'Patient/a' patient_key "
            "UNION ALL SELECT 2, 'Patient/b'"
        )
        assert _check_key_alignment(con, "x", ["patient_key"], self.ACTUAL) == []

    def test_two_identifiers_collapsed_onto_one_key_is_caught(self):
        # The MAX()-over-a-non-constant-group failure: both rows survive, both
        # carry a well-formed key, and one of them names the wrong patient.
        con = self._table(
            "SELECT 1 subject_id, 'Patient/a' patient_key "
            "UNION ALL SELECT 2, 'Patient/a'"
        )
        found = _check_key_alignment(con, "x", ["patient_key"], self.ACTUAL)
        assert [f["column"] for f in found] == ["patient_key"]
        assert found[0]["distinct_identifiers"] == 2
        assert found[0]["distinct_keys"] == 1

    def test_one_identifier_spanning_two_keys_is_caught(self):
        con = self._table(
            "SELECT 1 subject_id, 'Patient/a' patient_key "
            "UNION ALL SELECT 1, 'Patient/b'"
        )
        found = _check_key_alignment(con, "x", ["patient_key"], self.ACTUAL)
        assert found and found[0]["distinct_keys"] == 2

    def test_a_key_without_its_identifier_is_not_a_violation(self):
        # An Encounter view unfiltered by identifier.system holds a key for the
        # ICU and ED streams while hadm_id_str is NULL there. Comparing whole
        # -column distinct counts would reject that legitimate shape.
        con = self._table(
            "SELECT 1 subject_id, 'Patient/a' patient_key "
            "UNION ALL SELECT NULL, 'Patient/b'"
        )
        assert _check_key_alignment(con, "x", ["patient_key"], self.ACTUAL) == []

    def test_a_key_with_no_paired_identifier_column_is_skipped(self):
        # kdigo_creatinine emits no subject_id and still owes a patient_key.
        # There is nothing to align against; presence and prefix still apply.
        con = self._table("SELECT 'Patient/a' patient_key")
        assert _check_key_alignment(con, "x", ["patient_key"], {"patient_key": "VARCHAR"}) == []

    def test_a_bare_uuid_is_rejected_by_the_prefix_check(self):
        con = self._table("SELECT '0a8eebfd-a352-522e-89f0-1d4a13abdebc' patient_key")
        found = _check_key_prefixes(con, "x", ["patient_key"])
        assert [f["column"] for f in found] == ["patient_key"]

    def test_the_prefixed_form_passes_the_prefix_check(self):
        con = self._table(
            "SELECT 'Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc' patient_key"
        )
        assert _check_key_prefixes(con, "x", ["patient_key"]) == []
