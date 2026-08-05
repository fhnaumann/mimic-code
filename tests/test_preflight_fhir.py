"""Tests for the FHIR preflight (Pathling <-> DuckDB cohort identity).

This preflight answers one question before any concept port begins: **do the
demo FHIR warehouse and the demo relational oracle describe the same 100
patients?** If they do not, every later comparison silently compares different
cohorts -- so this is the gate that makes the whole demo layer trustworthy.

Two structural changes from the PostgreSQL version:

* Gate 4 compares against a real DuckDB oracle, so it is built as an actual
  100-row database instead of a mocked cursor.
* ``run_preflight_fhir`` accepts an injected ``client``, so the Pathling side
  uses a fake object rather than patched transport internals. Nothing here
  monkeypatches urllib.

Names that moved during the port: ``DEFAULT_FHIR_BASE_URL`` ->
``pathling.DEFAULT_BASE_URL``, ``FHIR_ENV_KEY`` -> ``pathling.BASE_URL_ENV_KEY``,
``_resolve_fhir_base_url`` -> ``pathling.resolve_base_url``, and
``_build_preflight_viewdefinition`` -> public
``build_preflight_viewdefinition``. ``_build_preflight_library`` and
``PREFLIGHT_LIBRARY_ID`` are gone -- the Library is now built generically by
``pathling.build_sqlquery_library``.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from unittest import mock

import duckdb
import pytest

from mimic_utils.duckdb_oracle import REQUIRED_SCHEMAS
from mimic_utils.pathling import (
    BASE_URL_ENV_KEY,
    DEFAULT_BASE_URL,
    LIBRARY_KIND_SQL_QUERY,
    LIBRARY_TYPE_SYSTEM,
    PathlingError,
    RelatedArtifact,
    build_sqlquery_library,
    capability_summary,
    parse_ndjson,
    parse_ndjson_dicts,
    resolve_base_url,
)
from mimic_utils.preflight_fhir import (
    EXPECTED_PATIENT_COUNT,
    IDENTIFIER_SYSTEM_SUFFIX,
    PREFLIGHT_SQL,
    PREFLIGHT_VD_ID,
    PREFLIGHT_VD_NAME,
    PREFLIGHT_VD_URL,
    PreflightFhirResult,
    build_preflight_viewdefinition,
    format_fhir_report,
    run_preflight_fhir,
)

PATIENT_SYSTEM = "http://mimic.mit.edu/fhir/identifier/patient"
OTHER_SYSTEM = "http://mimic.mit.edu/fhir/identifier/encounter"


# ---------------------------------------------------------------------------
# fixtures / doubles
# ---------------------------------------------------------------------------


def _capability(
    *,
    resource_type: str = "CapabilityStatement",
    fhir_version: str = "4.0.1",
    resources: tuple[str, ...] = ("ViewDefinition", "Library", "Patient"),
    operations: tuple[str, ...] = ("sqlquery-run",),
    software_version: str = "3.0.0-SNAPSHOT",
) -> dict:
    return {
        "resourceType": resource_type,
        "fhirVersion": fhir_version,
        "software": {"name": "Pathling", "version": software_version},
        "rest": [
            {
                "resource": [{"type": t} for t in resources],
                "operation": [{"name": op} for op in operations],
            }
        ],
    }


class FakePathlingClient:
    """Records calls and returns scripted responses."""

    def __init__(
        self,
        *,
        capability=None,
        rows=None,
        columns=("patient_key", "ident_system", "ident_value"),
        capability_error=None,
        put_error=None,
        sql_error=None,
    ):
        self._capability = capability if capability is not None else _capability()
        self._rows = rows if rows is not None else []
        self._columns = list(columns)
        self._capability_error = capability_error
        self._put_error = put_error
        self._sql_error = sql_error
        self.puts: list[tuple[str, str, dict]] = []
        self.queries: list[tuple[str, list]] = []

    def capability_statement(self):
        if self._capability_error:
            raise PathlingError(self._capability_error)
        return self._capability

    def put_definitional(self, *, resource_type, resource_id, resource_body):
        if self._put_error:
            raise PathlingError(self._put_error)
        self.puts.append((resource_type, resource_id, resource_body))
        return resource_body

    def sqlquery_run_sync(self, sql, related_artifacts=()):
        if self._sql_error:
            raise PathlingError(self._sql_error)
        self.queries.append((sql, list(related_artifacts)))
        return self._columns, self._rows


def _fhir_rows(subject_ids, *, system=PATIENT_SYSTEM):
    return [[f"Patient/{sid}", system, str(sid)] for sid in subject_ids]


def _make_oracle(path: Path, subject_ids) -> Path:
    con = duckdb.connect(str(path))
    for schema in REQUIRED_SCHEMAS:
        con.execute(f"CREATE SCHEMA {schema}")
    con.execute("CREATE TABLE mimiciv_hosp.patients (subject_id INTEGER)")
    for sid in subject_ids:
        con.execute(f"INSERT INTO mimiciv_hosp.patients VALUES ({sid})")
    con.close()
    return path


COHORT = list(range(10000001, 10000001 + EXPECTED_PATIENT_COUNT))


@pytest.fixture
def oracle(tmp_path):
    """An oracle holding exactly the expected 100 demo patients."""
    return _make_oracle(tmp_path / "oracle.db", COHORT)


# ---------------------------------------------------------------------------
# base URL resolution
# ---------------------------------------------------------------------------


class TestResolveBaseUrl:
    def test_explicit_wins(self):
        assert resolve_base_url("http://example/fhir/") == "http://example/fhir/"

    def test_env_used(self):
        with mock.patch.dict(os.environ, {BASE_URL_ENV_KEY: "http://env/fhir/"}):
            assert resolve_base_url() == "http://env/fhir/"

    def test_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert resolve_base_url() == DEFAULT_BASE_URL

    def test_default_is_local_http(self):
        assert DEFAULT_BASE_URL.startswith("http://localhost")


# ---------------------------------------------------------------------------
# the ViewDefinition -- the shape Pathling actually accepts
# ---------------------------------------------------------------------------


class TestBuildPreflightViewDefinition:
    def test_basic_identity(self):
        vd = build_preflight_viewdefinition()
        assert vd["resourceType"] == "ViewDefinition"
        assert vd["resource"] == "Patient"
        assert vd["name"] == PREFLIGHT_VD_NAME
        assert vd["url"] == PREFLIGHT_VD_URL
        assert vd["status"] == "active"

    def test_key_uses_get_resource_key_not_id(self):
        """``id`` is not the SQL-on-FHIR resource key."""
        first = build_preflight_viewdefinition()["select"][0]["column"][0]
        assert first["path"] == "getResourceKey()"
        assert first["name"] == "patient_key"

    def test_for_each_or_null_is_a_string_with_sibling_columns(self):
        """The proven Pathling form: a FHIRPath *string* with a sibling
        ``column`` array -- not a nested object carrying its own ``select``."""
        select = build_preflight_viewdefinition()["select"]
        ident = next(s for s in select if "forEachOrNull" in s)
        assert isinstance(ident["forEachOrNull"], str)
        assert ident["forEachOrNull"] == "identifier"
        assert [c["name"] for c in ident["column"]] == ["ident_system", "ident_value"]
        assert "select" not in ident

    def test_is_json_serialisable(self):
        json.dumps(build_preflight_viewdefinition())


class TestPreflightSql:
    def test_selects_from_the_view_and_filters_null_systems(self):
        assert PREFLIGHT_VD_NAME in PREFLIGHT_SQL
        assert "ident_system" in PREFLIGHT_SQL
        assert "IS NOT NULL" in PREFLIGHT_SQL


class TestBuildSqlqueryLibrary:
    def test_sql_is_base64_content(self):
        lib = build_sqlquery_library("SELECT 1")
        assert lib["resourceType"] == "Library"
        assert base64.b64decode(lib["content"][0]["data"]).decode() == "SELECT 1"
        assert lib["content"][0]["contentType"] == "application/sql"

    def test_type_coding_uses_sql_on_fhir_system(self):
        coding = build_sqlquery_library("SELECT 1")["type"]["coding"][0]
        assert coding["system"] == LIBRARY_TYPE_SYSTEM
        assert coding["code"] == LIBRARY_KIND_SQL_QUERY

    def test_related_artifact_carries_label_and_resource(self):
        """A missing ``resource`` canonical was a defect in the earlier draft:
        the label alone does not bind the SQL table name to a ViewDefinition."""
        art = RelatedArtifact(label="v_patient", resource=PREFLIGHT_VD_URL)
        ra = build_sqlquery_library("SELECT 1", [art])["relatedArtifact"][0]
        assert ra == {
            "type": "depends-on",
            "label": "v_patient",
            "resource": PREFLIGHT_VD_URL,
        }

    def test_url_and_name_optional(self):
        assert "url" not in build_sqlquery_library("SELECT 1")
        lib = build_sqlquery_library("SELECT 1", url="http://x/L", name="L")
        assert lib["url"] == "http://x/L" and lib["name"] == "L"


# ---------------------------------------------------------------------------
# capability parsing / NDJSON
# ---------------------------------------------------------------------------


class TestCapabilitySummary:
    def test_extracts_expected_facts(self):
        s = capability_summary(_capability())
        assert s["resource_type"] == "CapabilityStatement"
        assert s["fhir_version"] == "4.0.1"
        assert {"ViewDefinition", "Library"} <= s["resource_types"]
        assert "sqlquery-run" in s["operations"]
        assert s["software_version"] == "3.0.0-SNAPSHOT"

    def test_tolerates_empty_statement(self):
        s = capability_summary({})
        assert s["resource_types"] == set()
        assert s["operations"] == set()


class TestParseNdjson:
    def test_dicts(self):
        assert parse_ndjson_dicts('{"a": 1}\n{"a": 2}\n') == [{"a": 1}, {"a": 2}]

    def test_columns_and_rows(self):
        cols, rows = parse_ndjson('{"a": 1, "b": "x"}\n{"a": 2, "b": "y"}\n')
        assert cols == ["a", "b"]
        assert rows == [[1, "x"], [2, "y"]]

    def test_blank_lines_ignored(self):
        assert parse_ndjson_dicts('\n{"a": 1}\n\n') == [{"a": 1}]

    def test_empty_body(self):
        assert parse_ndjson_dicts("") == []


# ---------------------------------------------------------------------------
# gate 1
# ---------------------------------------------------------------------------


class TestGateCapabilityStatement:
    def test_passes_on_good_statement(self, oracle):
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient())
        assert r.gate1_passed is True
        assert r.fhir_version == "4.0.1"
        assert r.pathling_version == "3.0.0-SNAPSHOT"

    def test_transport_error_fails_and_short_circuits(self, oracle):
        client = FakePathlingClient(capability_error="connection refused")
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.gate1_passed is False
        assert r.passed is False
        assert client.puts == []  # later gates never ran

    def test_wrong_resource_type_rejected(self, oracle):
        client = FakePathlingClient(
            capability=_capability(resource_type="OperationOutcome")
        )
        assert run_preflight_fhir(duckdb_path=oracle, client=client).gate1_passed is False

    @pytest.mark.parametrize("version", ["3.0.2", "5.0.0", ""])
    def test_non_r4_rejected(self, oracle, version):
        client = FakePathlingClient(capability=_capability(fhir_version=version))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.fhir_40_compliant is False
        assert r.gate1_passed is False

    def test_missing_view_definition_rejected(self, oracle):
        client = FakePathlingClient(capability=_capability(resources=("Library",)))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.has_view_definition is False
        assert r.gate1_passed is False

    def test_missing_library_rejected(self, oracle):
        client = FakePathlingClient(capability=_capability(resources=("ViewDefinition",)))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.has_library is False
        assert r.gate1_passed is False

    def test_missing_sqlquery_run_rejected(self, oracle):
        client = FakePathlingClient(capability=_capability(operations=()))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.has_sqlquery_run is False
        assert r.gate1_passed is False


# ---------------------------------------------------------------------------
# gates 2 and 3
# ---------------------------------------------------------------------------


class TestGateViewDefinitionPut:
    def test_puts_under_the_preflight_scoped_id(self, oracle):
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.gate2_passed is True
        resource_type, resource_id, body = client.puts[0]
        assert resource_type == "ViewDefinition"
        assert resource_id == PREFLIGHT_VD_ID
        assert body["name"] == PREFLIGHT_VD_NAME

    def test_put_failure_fails_gate_and_stops(self, oracle):
        client = FakePathlingClient(put_error="422 Unprocessable Entity")
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.gate2_passed is False
        assert r.passed is False
        assert client.queries == []


class TestGateSqlRun:
    def test_passes_and_records_row_count(self, oracle):
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.gate3_passed is True
        assert r.sql_row_count == EXPECTED_PATIENT_COUNT

    def test_passes_the_viewdefinition_as_a_dependency(self, oracle):
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        run_preflight_fhir(duckdb_path=oracle, client=client)
        _sql, artifacts = client.queries[0]
        assert artifacts[0].label == PREFLIGHT_VD_NAME
        assert artifacts[0].resource == PREFLIGHT_VD_URL

    def test_zero_rows_is_a_failure(self, oracle):
        """An empty warehouse must not pass -- nothing would be compared."""
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient(rows=[]))
        assert r.gate3_passed is False
        assert r.passed is False

    def test_query_error_fails_gate(self, oracle):
        client = FakePathlingClient(sql_error="table not found")
        assert run_preflight_fhir(duckdb_path=oracle, client=client).gate3_passed is False


# ---------------------------------------------------------------------------
# gate 4 -- cohort identity, the point of the whole preflight
# ---------------------------------------------------------------------------


class TestGateCohortIdentity:
    def test_exact_match_passes_everything(self, oracle):
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.oracle_connected is True
        assert r.oracle_patient_count == EXPECTED_PATIENT_COUNT
        assert r.fhir_patient_count == EXPECTED_PATIENT_COUNT
        assert r.set_match is True
        assert r.only_fhir == [] and r.only_oracle == []
        assert r.passed is True

    def test_only_patient_system_identifiers_counted(self, oracle):
        """Encounter identifiers must be ignored, not counted as patients."""
        rows = _fhir_rows(COHORT) + _fhir_rows([999, 998], system=OTHER_SYSTEM)
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient(rows=rows))
        assert r.fhir_patient_count == EXPECTED_PATIENT_COUNT
        assert r.set_match is True

    def test_identifier_system_suffix_is_the_discriminator(self):
        assert PATIENT_SYSTEM.endswith(IDENTIFIER_SYSTEM_SUFFIX)
        assert not OTHER_SYSTEM.endswith(IDENTIFIER_SYSTEM_SUFFIX)

    def test_fhir_only_identifier_detected(self, tmp_path):
        """FHIR has a patient the oracle does not."""
        small = _make_oracle(tmp_path / "o.db", COHORT[:-1])
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        r = run_preflight_fhir(duckdb_path=small, client=client)
        assert r.set_match is False
        assert r.only_fhir == [COHORT[-1]]
        assert r.passed is False

    def test_oracle_only_identifier_detected(self, oracle):
        client = FakePathlingClient(rows=_fhir_rows(COHORT[:-1]))
        r = run_preflight_fhir(duckdb_path=oracle, client=client)
        assert r.set_match is False
        assert r.only_oracle == [COHORT[-1]]
        assert r.passed is False

    def test_same_count_different_members_detected(self, oracle):
        """Equal counts must not be mistaken for equal cohorts."""
        swapped = COHORT[:-1] + [77777777]
        r = run_preflight_fhir(
            duckdb_path=oracle, client=FakePathlingClient(rows=_fhir_rows(swapped))
        )
        assert r.fhir_patient_count == EXPECTED_PATIENT_COUNT
        assert r.set_match is False
        assert r.only_fhir == [77777777]
        assert r.passed is False

    def test_non_numeric_identifier_is_strict_failure(self, oracle):
        """Strict by design: an unexpected value in the MIMIC patient identifier
        namespace invalidates every subject join, so it must fail rather than be
        silently skipped."""
        rows = _fhir_rows(COHORT) + [["Patient/x", PATIENT_SYSTEM, "not-a-number"]]
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient(rows=rows))
        assert any("non-numeric" in e.lower() for e in r.compare_errors)
        assert r.passed is False

    def test_empty_identifier_value_is_failure(self, oracle):
        rows = _fhir_rows(COHORT) + [["Patient/x", PATIENT_SYSTEM, ""]]
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient(rows=rows))
        assert r.compare_errors
        assert r.passed is False

    def test_wrong_oracle_count_fails(self, tmp_path):
        small = _make_oracle(tmp_path / "o.db", COHORT[:50])
        client = FakePathlingClient(rows=_fhir_rows(COHORT[:50]))
        r = run_preflight_fhir(duckdb_path=small, client=client)
        assert r.oracle_patient_count == 50
        assert r.gate4_passed is False

    def test_missing_oracle_reported_not_raised(self, tmp_path):
        client = FakePathlingClient(rows=_fhir_rows(COHORT))
        r = run_preflight_fhir(duckdb_path=tmp_path / "absent.db", client=client)
        assert r.oracle_connected is False
        assert r.compare_errors
        assert r.passed is False

    def test_duplicate_identifiers_deduplicated(self, oracle):
        """Several identifier rows per patient must not inflate the count."""
        rows = _fhir_rows(COHORT) + _fhir_rows(COHORT[:5])
        r = run_preflight_fhir(duckdb_path=oracle, client=FakePathlingClient(rows=rows))
        assert r.fhir_patient_count == EXPECTED_PATIENT_COUNT
        assert r.set_match is True

    def test_oracle_never_modified(self, oracle):
        before = oracle.stat().st_size
        run_preflight_fhir(
            duckdb_path=oracle, client=FakePathlingClient(rows=_fhir_rows(COHORT))
        )
        assert oracle.stat().st_size == before


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


class TestFormatFhirReport:
    def _result(self, oracle):
        return run_preflight_fhir(
            duckdb_path=oracle, client=FakePathlingClient(rows=_fhir_rows(COHORT))
        )

    def test_plain_has_no_escapes(self, oracle):
        text = format_fhir_report(self._result(oracle), color=False)
        assert "\x1b[" not in text
        assert "Gate" in text

    def test_color_has_escapes(self, oracle):
        assert "\x1b[" in format_fhir_report(self._result(oracle), color=True)

    def test_no_postgres_wording(self, oracle):
        text = format_fhir_report(self._result(oracle), color=False).lower()
        assert "psycopg" not in text
        assert "postgresql://" not in text

    def test_failure_report_renderable(self):
        r = PreflightFhirResult(base_url="http://x/fhir/", errors=["boom"])
        assert isinstance(format_fhir_report(r, color=False), str)


class TestExpectedConstants:
    def test_demo_cohort_size(self):
        assert EXPECTED_PATIENT_COUNT == 100

    def test_preflight_ids_are_scoped(self):
        """Preflight resources must never collide with per-attempt resources."""
        assert "preflight" in PREFLIGHT_VD_ID
        assert "preflight" in PREFLIGHT_VD_NAME
        assert "preflight" in PREFLIGHT_VD_URL
