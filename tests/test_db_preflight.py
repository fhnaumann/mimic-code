"""Tests for the DuckDB oracle preflight.

These build a **real miniature DuckDB oracle** rather than mocking a database
connection. Under PostgreSQL the preflight talked to a server, so mocking was
unavoidable; DuckDB opens a file, so a genuine 3-schema fixture is both simpler
and a far stronger test -- it exercises the real SQL, the real read-only
enforcement, and the real type reporting.

One structural note: ``PreflightResult.counts_ok`` requires every table in
``DEMO_EXACT_COUNTS`` to match exactly (100 patients, 668,862 chartevents, ...),
so a synthetic fixture can never make ``passed`` true. Gates are therefore
asserted individually here, and overall pass is covered by an integration test
against the real demo oracle, skipped when that file is absent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import duckdb
import pytest

from mimic_utils.db_preflight import (
    DEMO_EXACT_COUNTS,
    EXPECTED_EMPTY_CONCEPTS,
    PreflightResult,
    format_report,
    run_preflight,
)
from mimic_utils.duckdb_oracle import (
    DEFAULT_DUCKDB_PATH,
    ENV_KEY,
    REQUIRED_SCHEMAS,
    OracleError,
    connect_read_only,
    describe_columns,
    duckdb_version,
    file_sha256,
    list_schemas,
    list_tables,
    resolve_duckdb_path,
)

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_repo(tmp_path):
    """A repo root whose DAG declares three concepts."""
    dag_dir = tmp_path / "mimic-iv" / "concept_dag"
    dag_dir.mkdir(parents=True)
    dag = {
        "nodes": {
            "age": {"stem": "age", "path": "demographics/age.sql"},
            "sofa": {"stem": "sofa", "path": "score/sofa.sql"},
            "neuroblock": {"stem": "neuroblock", "path": "medication/neuroblock.sql"},
        }
    }
    (dag_dir / "concept_dag.json").write_text(json.dumps(dag))
    return tmp_path


def _make_oracle(path: Path, *, concepts: dict[str, int]) -> Path:
    """Build a DuckDB file with all required schemas and the given concept rows."""
    con = duckdb.connect(str(path))
    for schema in REQUIRED_SCHEMAS:
        con.execute(f"CREATE SCHEMA {schema}")
    con.execute("CREATE TABLE mimiciv_hosp.patients (subject_id INTEGER, anchor_age SMALLINT)")
    con.execute("INSERT INTO mimiciv_hosp.patients VALUES (1, 40), (2, 50)")
    con.execute("CREATE TABLE mimiciv_icu.icustays (stay_id INTEGER)")
    con.execute("INSERT INTO mimiciv_icu.icustays VALUES (10)")
    for name, n_rows in concepts.items():
        con.execute(f"CREATE TABLE mimiciv_derived.{name} (subject_id INTEGER, v BIGINT)")
        for i in range(n_rows):
            con.execute(f"INSERT INTO mimiciv_derived.{name} VALUES ({i}, {i})")
    con.close()
    return path


@pytest.fixture
def oracle(tmp_path):
    """A well-formed oracle. ``neuroblock`` is empty -- the real demo condition."""
    return _make_oracle(
        tmp_path / "oracle.db", concepts={"age": 2, "sofa": 1, "neuroblock": 0}
    )


# ---------------------------------------------------------------------------
# path resolution
# ---------------------------------------------------------------------------


class TestResolveDuckdbPath:
    def test_explicit_wins(self, tmp_path):
        p = tmp_path / "explicit.db"
        assert resolve_duckdb_path(p) == p.resolve()

    def test_env_var_used_when_no_explicit(self, tmp_path):
        p = tmp_path / "from-env.db"
        with mock.patch.dict(os.environ, {ENV_KEY: str(p)}):
            assert resolve_duckdb_path() == p.resolve()

    def test_explicit_overrides_env(self, tmp_path):
        with mock.patch.dict(os.environ, {ENV_KEY: str(tmp_path / "env.db")}):
            explicit = tmp_path / "explicit.db"
            assert resolve_duckdb_path(explicit) == explicit.resolve()

    def test_falls_back_to_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert resolve_duckdb_path() == Path(DEFAULT_DUCKDB_PATH).resolve()

    def test_env_key_and_default_are_duckdb_not_postgres(self):
        assert ENV_KEY == "MIMIC_DUCKDB_PATH"
        assert "postgres" not in DEFAULT_DUCKDB_PATH.lower()
        assert DEFAULT_DUCKDB_PATH.endswith(".db")


# ---------------------------------------------------------------------------
# read-only enforcement -- the load-bearing safety property
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_can_read(self, oracle):
        with connect_read_only(oracle) as con:
            assert con.execute("SELECT count(*) FROM mimiciv_derived.age").fetchone()[0] == 2

    def test_rejects_writes(self, oracle):
        """The oracle must be unmodifiable through the loop's own helper."""
        with connect_read_only(oracle) as con:
            with pytest.raises(Exception):
                con.execute("CREATE TABLE mimiciv_derived.injected (x INT)")

    def test_rejects_deletes(self, oracle):
        with connect_read_only(oracle) as con:
            with pytest.raises(Exception):
                con.execute("DELETE FROM mimiciv_derived.age")

    def test_missing_file_raises_oracle_error(self, tmp_path):
        with pytest.raises(OracleError):
            with connect_read_only(tmp_path / "absent.db"):
                pass


# ---------------------------------------------------------------------------
# introspection helpers
# ---------------------------------------------------------------------------


class TestIntrospection:
    def test_list_schemas(self, oracle):
        with connect_read_only(oracle) as con:
            assert set(REQUIRED_SCHEMAS) <= set(list_schemas(con))

    def test_list_tables(self, oracle):
        with connect_read_only(oracle) as con:
            assert set(list_tables(con, "mimiciv_derived")) == {"age", "sofa", "neuroblock"}

    def test_describe_columns_returns_duckdb_type_names(self, oracle):
        with connect_read_only(oracle) as con:
            cols = describe_columns(con, "mimiciv_derived", "age")
        assert cols["subject_id"] == "INTEGER"
        assert cols["v"] == "BIGINT"

    def test_file_sha256_stable_and_hex(self, oracle):
        a, b = file_sha256(oracle), file_sha256(oracle)
        assert a == b and len(a) == 64
        int(a, 16)

    def test_file_sha256_changes_with_content(self, tmp_path):
        one = _make_oracle(tmp_path / "a.db", concepts={"age": 1})
        two = _make_oracle(tmp_path / "b.db", concepts={"age": 2})
        assert file_sha256(one) != file_sha256(two)

    def test_duckdb_version_reported(self):
        assert duckdb_version()


# ---------------------------------------------------------------------------
# the preflight
# ---------------------------------------------------------------------------


class TestRunPreflight:
    def test_records_identity_and_opens_read_only(self, oracle, dag_repo):
        r = run_preflight(oracle, repo_root=dag_repo)
        assert r.opened_read_only is True
        assert r.path == str(oracle.resolve())
        assert len(r.sha256) == 64
        assert r.duckdb_version

    def test_schemas_gate_passes(self, oracle, dag_repo):
        r = run_preflight(oracle, repo_root=dag_repo)
        assert r.schemas_ok is True
        assert not r.schemas_missing

    def test_concepts_gate_passes_when_all_dag_tables_present(self, oracle, dag_repo):
        r = run_preflight(oracle, repo_root=dag_repo)
        assert r.concepts_ok is True
        assert r.concepts_expected == 3
        assert not r.concepts_missing

    def test_missing_file_is_error_not_crash(self, tmp_path, dag_repo):
        r = run_preflight(tmp_path / "absent.db", repo_root=dag_repo)
        assert r.passed is False
        assert r.errors

    def test_missing_schema_fails(self, tmp_path, dag_repo):
        path = tmp_path / "partial.db"
        con = duckdb.connect(str(path))
        con.execute("CREATE SCHEMA mimiciv_hosp")  # icu + derived absent
        con.close()
        r = run_preflight(path, repo_root=dag_repo)
        assert r.schemas_ok is False
        assert r.passed is False

    def test_missing_concept_table_fails_concepts_gate(self, tmp_path, dag_repo):
        path = _make_oracle(tmp_path / "no-sofa.db", concepts={"age": 1})
        r = run_preflight(path, repo_root=dag_repo)
        assert r.concepts_ok is False
        assert "sofa" in r.concepts_missing

    def test_empty_neuroblock_is_expected_not_unexpected(self, oracle, dag_repo):
        """No neuromuscular blocker administrations exist among the 100 demo
        patients. That is a correct result, not a build failure."""
        assert "neuroblock" in EXPECTED_EMPTY_CONCEPTS
        r = run_preflight(oracle, repo_root=dag_repo)
        assert "neuroblock" in r.expected_empty_concepts
        assert "neuroblock" not in r.unexpected_empty_concepts

    def test_unexpectedly_empty_concept_is_flagged(self, tmp_path, dag_repo):
        """An empty concept NOT on the expected-empty list must be caught --
        otherwise a port returning zero rows would compare as equivalent."""
        path = _make_oracle(
            tmp_path / "empty-age.db", concepts={"age": 0, "sofa": 1, "neuroblock": 0}
        )
        r = run_preflight(path, repo_root=dag_repo)
        assert "age" in r.unexpected_empty_concepts
        assert r.passed is False


class TestDemoExactCounts:
    """Expected counts come from ``buildmimic/postgres/validate_demo.sql``.

    That script is plain SQL over ``information_schema`` and is engine
    independent; it sits in the postgres directory for historical reasons only,
    and remains the reference under DuckDB.
    """

    def test_structure(self):
        assert DEMO_EXACT_COUNTS
        for schema, tables in DEMO_EXACT_COUNTS.items():
            assert schema.startswith("mimiciv_")
            for table, count in tables.items():
                assert isinstance(count, int) and count > 0, (schema, table)

    def test_known_anchor_counts(self):
        assert DEMO_EXACT_COUNTS["mimiciv_hosp"]["patients"] == 100
        assert DEMO_EXACT_COUNTS["mimiciv_hosp"]["admissions"] == 275
        assert DEMO_EXACT_COUNTS["mimiciv_icu"]["icustays"] == 140

    def test_wrong_count_fails_counts_gate(self, oracle, dag_repo):
        """The fixture has 2 patients where the demo has 100."""
        r = run_preflight(oracle, repo_root=dag_repo)
        assert r.counts_ok is False
        assert r.passed is False


class TestFormatReport:
    def test_renders_without_color(self, oracle, dag_repo):
        text = format_report(run_preflight(oracle, repo_root=dag_repo), color=False)
        assert "\x1b[" not in text
        assert "Gate" in text

    def test_color_emits_escapes(self, oracle, dag_repo):
        text = format_report(run_preflight(oracle, repo_root=dag_repo), color=True)
        assert "\x1b[" in text

    def test_no_postgres_wording_remains(self, oracle, dag_repo):
        text = format_report(run_preflight(oracle, repo_root=dag_repo), color=False).lower()
        assert "psycopg" not in text
        assert "postgresql://" not in text

    def test_bare_result_is_renderable(self):
        assert isinstance(format_report(PreflightResult(path="/nowhere.db"), color=False), str)


# ---------------------------------------------------------------------------
# integration: the real demo oracle
# ---------------------------------------------------------------------------

_REAL = Path(DEFAULT_DUCKDB_PATH)


@pytest.mark.skipif(not _REAL.is_file(), reason=f"demo oracle absent: {_REAL}")
class TestRealDemoOracle:
    """Only the real oracle can satisfy ``counts_ok``, so overall pass lives here."""

    def test_preflight_passes(self):
        r = run_preflight(_REAL)
        assert r.passed is True, r.errors

    def test_all_65_concepts_present(self):
        r = run_preflight(_REAL)
        assert r.concepts_expected == 65
        assert not r.concepts_missing

    def test_only_neuroblock_is_empty(self):
        r = run_preflight(_REAL)
        assert r.expected_empty_concepts == ["neuroblock"]
        assert not r.unexpected_empty_concepts
