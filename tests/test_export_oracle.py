"""Tests for the DuckDB oracle exporter.

Two things changed with the DuckDB port and are reflected here:

* ``_redact_uri`` is gone -- there is no connection URI to redact, so the class
  of credential-leak tests it existed for is now structurally impossible. The
  exporter records a file path and a SHA256 instead.
* ``_serialise_row`` became :func:`serialise_rows`, which also **sorts**
  deterministically, so two exports of the same table are comparable regardless
  of scan order.

Type coverage runs through a real DuckDB oracle rather than mocked psycopg2 type
codes: the values under test are whatever DuckDB actually hands back.
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import duckdb
import pytest

from mimic_utils.duckdb_oracle import REQUIRED_SCHEMAS
from mimic_utils.export_oracle import (
    _sanitise_identifier,
    _serialise_value,
    _validate_concept_in_dag,
    export_oracle,
    serialise_rows,
    write_artifact,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_repo(tmp_path):
    dag_dir = tmp_path / "mimic-iv" / "concept_dag"
    dag_dir.mkdir(parents=True)
    (dag_dir / "concept_dag.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "age": {"stem": "age", "path": "demographics/age.sql"},
                    "acei": {"stem": "acei", "path": "medication/acei.sql"},
                    "empty_concept": {
                        "stem": "empty_concept",
                        "path": "medication/empty_concept.sql",
                    },
                }
            }
        )
    )
    return tmp_path


@pytest.fixture
def oracle(tmp_path):
    """Real oracle with a typed ``age`` table plus an empty concept."""
    path = tmp_path / "oracle.db"
    con = duckdb.connect(str(path))
    for schema in REQUIRED_SCHEMAS:
        con.execute(f"CREATE SCHEMA {schema}")
    con.execute(
        """CREATE TABLE mimiciv_derived.age (
               subject_id INTEGER, hadm_id INTEGER, admittime TIMESTAMP,
               anchor_age SMALLINT, ratio DOUBLE, note VARCHAR)"""
    )
    con.execute(
        """INSERT INTO mimiciv_derived.age VALUES
             (2, 200, TIMESTAMP '2180-07-23 12:35:00', 52, 1.5, 'b'),
             (1, 100, TIMESTAMP '2110-04-11 15:08:00', 40, 0.5, 'a'),
             (3, 300, NULL, 91, NULL, NULL)"""
    )
    con.execute("CREATE TABLE mimiciv_derived.empty_concept (stay_id INTEGER)")
    con.close()
    return path


# ---------------------------------------------------------------------------
# identifier safety
# ---------------------------------------------------------------------------


class TestSanitiseIdentifier:
    @pytest.mark.parametrize("name", ["age", "first_day_sofa", "_x", "a1", "A_9"])
    def test_accepts_valid(self, name):
        assert _sanitise_identifier(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "1age",
            "age-1",
            "age;DROP TABLE x",
            "age table",
            'age"',
            "age'",
            "a" * 64,
            "sofa--comment",
            "mimiciv_derived.age",
        ],
    )
    def test_rejects_unsafe(self, name):
        with pytest.raises(ValueError):
            _sanitise_identifier(name)


class TestValidateConceptInDag:
    def test_accepts_known(self, dag_repo):
        assert _validate_concept_in_dag("age", dag_repo) == "age"

    def test_lowercases(self, dag_repo):
        assert _validate_concept_in_dag("AGE", dag_repo) == "age"

    def test_rejects_unknown(self, dag_repo):
        with pytest.raises(ValueError, match="not a recognised stem"):
            _validate_concept_in_dag("not_a_concept", dag_repo)

    def test_missing_dag_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _validate_concept_in_dag("age", tmp_path)


# ---------------------------------------------------------------------------
# value serialisation
# ---------------------------------------------------------------------------


class TestSerialiseValue:
    def test_none(self):
        assert _serialise_value(None) is None

    def test_bool_checked_before_int(self):
        """bool subclasses int, so dispatch order matters."""
        assert _serialise_value(True) is True
        assert _serialise_value(False) is False

    def test_int_and_str(self):
        assert _serialise_value(42) == 42
        assert _serialise_value("hi") == "hi"

    def test_float_finite(self):
        assert _serialise_value(3.14) == 3.14

    def test_non_finite_floats_become_strings(self):
        """JSON has no NaN/Infinity literal."""
        assert _serialise_value(float("nan")) == "NaN"
        assert _serialise_value(float("inf")) == "Infinity"
        assert _serialise_value(float("-inf")) == "-Infinity"

    def test_decimal_becomes_string_to_preserve_precision(self):
        assert _serialise_value(Decimal("0.1")) == "0.1"
        assert (
            _serialise_value(Decimal("12345678901234567890.123"))
            == "12345678901234567890.123"
        )

    def test_naive_datetime_kept_naive(self):
        assert _serialise_value(datetime(2180, 7, 23, 12, 35)) == "2180-07-23T12:35:00"

    def test_aware_datetime_normalised_to_utc_z(self):
        aware = datetime(2180, 7, 23, 12, 35, tzinfo=timezone(timedelta(hours=10)))
        assert _serialise_value(aware) == "2180-07-23T02:35:00Z"

    def test_date_and_time(self):
        assert _serialise_value(date(2180, 7, 23)) == "2180-07-23"
        assert _serialise_value(time(12, 35, 1)) == "12:35:01"

    def test_timedelta_iso_duration(self):
        assert _serialise_value(timedelta(0)) == "PT0S"
        assert _serialise_value(timedelta(hours=2)) == "PT2H"
        assert _serialise_value(timedelta(days=1, hours=2, minutes=3)) == "P1DT2H3M"
        assert _serialise_value(timedelta(seconds=-30)).startswith("-")

    def test_bytes_base64(self):
        assert _serialise_value(b"\x00\x01") == base64.b64encode(b"\x00\x01").decode()
        assert _serialise_value(memoryview(b"ab")) == base64.b64encode(b"ab").decode()

    def test_nested_containers(self):
        assert _serialise_value([1, None, "x"]) == [1, None, "x"]
        assert _serialise_value((1, 2)) == [1, 2]
        assert _serialise_value({"k": Decimal("1.5")}) == {"k": "1.5"}

    def test_unknown_object_stringified(self):
        class Weird:
            def __str__(self):
                return "weird"

        assert _serialise_value(Weird()) == "weird"

    def test_output_is_json_encodable(self):
        vals = [None, True, 1, 1.5, Decimal("2.5"), datetime(2000, 1, 1), b"x"]
        json.dumps([_serialise_value(v) for v in vals])


class TestSerialiseRows:
    def test_deterministic_regardless_of_input_order(self):
        a = serialise_rows([(1, "a"), (2, "b"), (3, "c")])
        b = serialise_rows([(3, "c"), (1, "a"), (2, "b")])
        assert a == b

    def test_preserves_duplicate_rows(self):
        assert len(serialise_rows([(1,), (1,), (2,)])) == 3

    def test_empty(self):
        assert serialise_rows([]) == []


# ---------------------------------------------------------------------------
# write-once artifact
# ---------------------------------------------------------------------------


class TestWriteArtifact:
    def test_writes_json(self, tmp_path):
        out = tmp_path / "a.json"
        write_artifact({"concept": "age"}, out)
        assert json.loads(out.read_text())["concept"] == "age"

    def test_refuses_to_overwrite(self, tmp_path):
        out = tmp_path / "a.json"
        write_artifact({"x": 1}, out)
        with pytest.raises(FileExistsError):
            write_artifact({"x": 2}, out)
        assert json.loads(out.read_text())["x"] == 1

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "a.json"
        write_artifact({"x": 1}, out)
        assert out.is_file()

    def test_leaves_no_temp_file(self, tmp_path):
        write_artifact({"x": 1}, tmp_path / "a.json")
        assert not list(tmp_path.glob("*.tmp"))


# ---------------------------------------------------------------------------
# export_oracle end to end, against a real oracle
# ---------------------------------------------------------------------------


class TestExportOracle:
    def _export(self, oracle, dag_repo, tmp_path, concept="age", name="out.json"):
        out = tmp_path / name
        export_oracle(concept, out, duckdb_path=oracle, repo_root=dag_repo)
        return json.loads(out.read_text())

    def test_artifact_contract(self, oracle, dag_repo, tmp_path):
        art = self._export(oracle, dag_repo, tmp_path)
        assert art["format_version"] == "1.0"
        assert art["concept"] == "age"
        assert art["dataset"] == "demo"
        assert art["columns"] == [
            "subject_id",
            "hadm_id",
            "admittime",
            "anchor_age",
            "ratio",
            "note",
        ]
        assert art["row_count"] == 3
        assert len(art["rows"]) == 3
        assert art["exported_at"].endswith("Z")

    def test_records_duckdb_provenance_not_a_uri(self, oracle, dag_repo, tmp_path):
        src = self._export(oracle, dag_repo, tmp_path)["source"]
        assert src["engine"] == "duckdb"
        assert src["table"] == "mimiciv_derived.age"
        assert len(src["sha256"]) == 64
        assert src["version"]
        assert "postgresql://" not in json.dumps(src)

    def test_column_types_are_duckdb_names(self, oracle, dag_repo, tmp_path):
        types = self._export(oracle, dag_repo, tmp_path)["column_types"]
        assert types["subject_id"] == "INTEGER"
        assert types["anchor_age"] == "SMALLINT"
        assert types["ratio"] == "DOUBLE"
        assert types["admittime"] == "TIMESTAMP"

    def test_nulls_round_trip(self, oracle, dag_repo, tmp_path):
        rows = self._export(oracle, dag_repo, tmp_path)["rows"]
        assert any(r[2] is None and r[4] is None and r[5] is None for r in rows)

    def test_timestamps_serialised_iso(self, oracle, dag_repo, tmp_path):
        rows = self._export(oracle, dag_repo, tmp_path)["rows"]
        assert "2110-04-11T15:08:00" in [r[2] for r in rows if r[2] is not None]

    def test_output_is_deterministic(self, oracle, dag_repo, tmp_path):
        a = self._export(oracle, dag_repo, tmp_path, name="a.json")
        b = self._export(oracle, dag_repo, tmp_path, name="b.json")
        assert a["rows"] == b["rows"]

    def test_empty_concept_exports_zero_rows(self, oracle, dag_repo, tmp_path):
        art = self._export(oracle, dag_repo, tmp_path, concept="empty_concept")
        assert art["row_count"] == 0
        assert art["rows"] == []

    def test_write_once_enforced(self, oracle, dag_repo, tmp_path):
        out = tmp_path / "once.json"
        export_oracle("age", out, duckdb_path=oracle, repo_root=dag_repo)
        with pytest.raises(FileExistsError):
            export_oracle("age", out, duckdb_path=oracle, repo_root=dag_repo)

    def test_unknown_concept_rejected(self, oracle, dag_repo, tmp_path):
        with pytest.raises(ValueError):
            export_oracle(
                "nope", tmp_path / "x.json", duckdb_path=oracle, repo_root=dag_repo
            )

    def test_concept_in_dag_but_absent_from_oracle(self, oracle, dag_repo, tmp_path):
        """``acei`` is declared in the DAG but was never built in this oracle."""
        with pytest.raises(RuntimeError, match="not found"):
            export_oracle(
                "acei", tmp_path / "x.json", duckdb_path=oracle, repo_root=dag_repo
            )

    def test_missing_oracle_raises_runtime_error(self, dag_repo, tmp_path):
        with pytest.raises(RuntimeError):
            export_oracle(
                "age",
                tmp_path / "x.json",
                duckdb_path=tmp_path / "absent.db",
                repo_root=dag_repo,
            )

    def test_dataset_label_recorded(self, oracle, dag_repo, tmp_path):
        out = tmp_path / "full.json"
        export_oracle("age", out, duckdb_path=oracle, repo_root=dag_repo, dataset="full")
        assert json.loads(out.read_text())["dataset"] == "full"

    def test_oracle_not_modified_by_export(self, oracle, dag_repo, tmp_path):
        before = oracle.stat().st_size
        export_oracle("age", tmp_path / "x.json", duckdb_path=oracle, repo_root=dag_repo)
        assert oracle.stat().st_size == before
        con = duckdb.connect(str(oracle), read_only=True)
        assert con.execute("SELECT count(*) FROM mimiciv_derived.age").fetchone()[0] == 3
        con.close()
