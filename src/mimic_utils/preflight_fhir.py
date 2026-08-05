"""MIMIC-on-FHIR / Pathling integration preflight check.

Proves the target side of the port loop end to end before any concept work
starts: that Pathling is reachable and capable, that a ViewDefinition can be
registered and queried, and — the point of the whole check — that the FHIR
warehouse holds **exactly the same patient cohort** as the DuckDB oracle.

Gates
-----
1. **CapabilityStatement** — ``GET /metadata``; require FHIR 4.0.x, the
   ViewDefinition and Library resource types, and the ``$sqlquery-run``
   operation.  Records the Pathling version.
2. **ViewDefinition PUT** — upsert a preflight-scoped Patient ViewDefinition
   projecting ``getResourceKey()`` plus identifier system/value via a
   string-valued ``forEachOrNull`` with a sibling ``column`` array.
3. **$sqlquery-run** — execute against that ViewDefinition through an inline
   sql-query Library carrying it as a ``depends-on`` relatedArtifact, and
   parse the NDJSON result.
4. **Cohort identity** — take identifiers whose system ends in
   ``/identifier/patient``, require every one to be numeric, and compare the
   set to ``SELECT subject_id FROM mimiciv_hosp.patients`` read from the
   read-only DuckDB oracle.  Require exactly 100 identifiers on the demo
   dataset and exact set equality.

A non-numeric value under the MIMIC patient identifier system is a **hard
failure**, not a skipped row: it means the identifier namespace is not what
the port assumes, and every downstream subject join would be built on sand.

Resolution
----------
FHIR base URL: ``--base-url`` -> ``PATHLING_FHIR_BASE_URL`` -> ``http://localhost:8080/fhir/``
DuckDB oracle: ``--duckdb`` -> ``MIMIC_DUCKDB_PATH`` -> built-in default

No secrets are persisted; resource ids and canonicals are clearly
preflight-scoped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from mimic_utils.duckdb_oracle import (
    ENV_KEY as DUCKDB_ENV_KEY,
    OracleError,
    connect_read_only,
    resolve_duckdb_path,
)
from mimic_utils.pathling import (
    BASE_URL_ENV_KEY,
    DEFAULT_BASE_URL,
    PathlingClient,
    PathlingError,
    RelatedArtifact,
    capability_summary,
    resolve_base_url,
)

# Preflight-scoped resource identity — never collides with attempt resources.
PREFLIGHT_VD_NAME = "preflight_patient_identifiers"
PREFLIGHT_VD_ID = "preflight-patient-identifiers"
PREFLIGHT_VD_URL = (
    "http://mimic.mit.edu/fhir/ViewDefinition/preflight-patient-identifiers"
)

# The identifier system whose values are MIMIC ``subject_id``s.
IDENTIFIER_SYSTEM_SUFFIX = "/identifier/patient"

# Expected patient count on the MIMIC-IV 2.2 demo dataset.
EXPECTED_PATIENT_COUNT = 100

REQUIRED_RESOURCE_TYPES = ("ViewDefinition", "Library")
REQUIRED_OPERATION = "sqlquery-run"

PREFLIGHT_SQL = f"""\
SELECT patient_key, ident_system, ident_value
FROM {PREFLIGHT_VD_NAME}
WHERE ident_system IS NOT NULL\
"""


def build_preflight_viewdefinition() -> Dict[str, Any]:
    """The preflight Patient ViewDefinition, in the form Pathling accepts.

    ``forEachOrNull`` is a **string** FHIRPath expression with a sibling
    ``column`` array — not a nested object with its own ``select``.  The FHIR
    key comes from ``getResourceKey()``, not from ``id``.
    """
    return {
        "resourceType": "ViewDefinition",
        "url": PREFLIGHT_VD_URL,
        "name": PREFLIGHT_VD_NAME,
        "status": "active",
        "resource": "Patient",
        "select": [
            {"column": [{"path": "getResourceKey()", "name": "patient_key"}]},
            {
                "forEachOrNull": "identifier",
                "column": [
                    {"path": "system", "name": "ident_system"},
                    {"path": "value", "name": "ident_value"},
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class PreflightFhirResult:
    """Aggregate result of the FHIR preflight check."""

    base_url: str
    duckdb_path: str = ""

    # -- Gate 1: CapabilityStatement -----------------------------------------
    capstmt_ok: bool = False
    fhir_version: str = ""
    fhir_40_compliant: bool = False
    has_view_definition: bool = False
    has_library: bool = False
    has_sqlquery_run: bool = False
    pathling_version: str = ""
    capstmt_errors: List[str] = field(default_factory=list)

    # -- Gate 2: ViewDefinition PUT ------------------------------------------
    vd_put_ok: bool = False
    vd_put_errors: List[str] = field(default_factory=list)

    # -- Gate 3: SQL execution -----------------------------------------------
    sql_run_ok: bool = False
    sql_row_count: int = 0
    sql_run_errors: List[str] = field(default_factory=list)

    # -- Gate 4: Cohort identity ---------------------------------------------
    oracle_connected: bool = False
    oracle_patient_count: int = 0
    fhir_patient_count: int = 0
    set_match: bool = False
    only_fhir: List[int] = field(default_factory=list)
    only_oracle: List[int] = field(default_factory=list)
    compare_errors: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    @property
    def gate1_passed(self) -> bool:
        return (
            self.capstmt_ok
            and self.fhir_40_compliant
            and self.has_view_definition
            and self.has_library
            and self.has_sqlquery_run
            and not self.capstmt_errors
        )

    @property
    def gate2_passed(self) -> bool:
        return self.vd_put_ok and not self.vd_put_errors

    @property
    def gate3_passed(self) -> bool:
        return self.sql_run_ok and not self.sql_run_errors

    @property
    def gate4_passed(self) -> bool:
        return (
            self.oracle_connected
            and self.oracle_patient_count == EXPECTED_PATIENT_COUNT
            and self.fhir_patient_count == EXPECTED_PATIENT_COUNT
            and self.set_match
            and not self.compare_errors
        )

    @property
    def passed(self) -> bool:
        return (
            self.gate1_passed
            and self.gate2_passed
            and self.gate3_passed
            and self.gate4_passed
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_preflight_fhir(
    fhir_base_url: Optional[str] = None,
    duckdb_path: Optional[str | Path] = None,
    *,
    client: Optional[PathlingClient] = None,
) -> PreflightFhirResult:
    """Perform the FHIR preflight and return a result object.

    Gates run in order and short-circuit: a broken CapabilityStatement makes
    every later gate meaningless.
    """
    base = resolve_base_url(fhir_base_url)
    oracle = resolve_duckdb_path(duckdb_path)
    result = PreflightFhirResult(base_url=base, duckdb_path=str(oracle))
    if client is None:
        client = PathlingClient(base)

    _gate_capability_statement(client, result)
    if not result.gate1_passed:
        return result

    _gate_view_definition_put(client, result)
    if not result.gate2_passed:
        return result

    rows = _gate_sql_run(client, result)
    if not result.gate3_passed:
        return result

    _gate_cohort_identity(rows, oracle, result)
    return result


# ---------------------------------------------------------------------------
# Gate implementations
# ---------------------------------------------------------------------------


def _gate_capability_statement(
    client: PathlingClient, result: PreflightFhirResult
) -> None:
    """Gate 1: fetch the CapabilityStatement and check required capabilities."""
    try:
        capstmt = client.capability_statement()
    except PathlingError as exc:
        result.capstmt_errors.append(str(exc))
        return

    summary = capability_summary(capstmt)
    if summary["resource_type"] != "CapabilityStatement":
        result.capstmt_errors.append(
            f"Expected CapabilityStatement, got {summary['resource_type']!r}"
        )
        return

    result.capstmt_ok = True
    result.fhir_version = summary["fhir_version"]
    result.fhir_40_compliant = result.fhir_version.startswith("4.0")
    if not result.fhir_40_compliant:
        result.capstmt_errors.append(
            f"FHIR version must be 4.0.x, got {result.fhir_version!r}"
        )

    result.pathling_version = summary["software_version"]

    resource_types = summary["resource_types"]
    result.has_view_definition = "ViewDefinition" in resource_types
    result.has_library = "Library" in resource_types
    for name, present in (
        ("ViewDefinition", result.has_view_definition),
        ("Library", result.has_library),
    ):
        if not present:
            result.capstmt_errors.append(f"{name} resource type not advertised")

    result.has_sqlquery_run = REQUIRED_OPERATION in summary["operations"]
    if not result.has_sqlquery_run:
        result.capstmt_errors.append(
            f"${REQUIRED_OPERATION} operation not advertised in CapabilityStatement"
        )


def _gate_view_definition_put(
    client: PathlingClient, result: PreflightFhirResult
) -> None:
    """Gate 2: upsert the preflight ViewDefinition."""
    try:
        client.put_definitional(
            resource_type="ViewDefinition",
            resource_id=PREFLIGHT_VD_ID,
            resource_body=build_preflight_viewdefinition(),
        )
    except PathlingError as exc:
        result.vd_put_errors.append(str(exc))
        return
    result.vd_put_ok = True


def _gate_sql_run(
    client: PathlingClient, result: PreflightFhirResult
) -> List[Dict[str, Any]]:
    """Gate 3: run the preflight SQL; return rows as ``{column: value}`` dicts."""
    dependency = RelatedArtifact(label=PREFLIGHT_VD_NAME, resource=PREFLIGHT_VD_URL)
    try:
        columns, rows = client.sqlquery_run_sync(PREFLIGHT_SQL, [dependency])
    except PathlingError as exc:
        result.sql_run_errors.append(str(exc))
        return []

    if not rows:
        result.sql_run_errors.append(
            "$sqlquery-run returned no rows — the FHIR warehouse has no "
            "Patient identifiers to compare"
        )
        return []

    result.sql_run_ok = True
    result.sql_row_count = len(rows)
    return [dict(zip(columns, row)) for row in rows]


def _gate_cohort_identity(
    rows: List[Dict[str, Any]],
    oracle_path: Path,
    result: PreflightFhirResult,
) -> None:
    """Gate 4: compare the FHIR patient identifier set to the DuckDB oracle."""
    fhir_ids: Set[int] = set()
    for row in rows:
        system = row.get("ident_system") or ""
        if not str(system).endswith(IDENTIFIER_SYSTEM_SUFFIX):
            continue
        value = row.get("ident_value")
        if value is None or str(value) == "":
            result.compare_errors.append(
                f"Empty identifier value under system {system!r}"
            )
            continue
        try:
            fhir_ids.add(int(str(value)))
        except ValueError:
            # Strict by design: an unexpected value in the MIMIC patient
            # identifier namespace invalidates every subject join.
            result.compare_errors.append(
                f"Non-numeric identifier value {value!r} under system {system!r}"
            )

    result.fhir_patient_count = len(fhir_ids)
    if result.fhir_patient_count != EXPECTED_PATIENT_COUNT:
        result.compare_errors.append(
            f"FHIR patient identifier count is {result.fhir_patient_count}, "
            f"expected {EXPECTED_PATIENT_COUNT}"
        )

    oracle_ids: Set[int] = set()
    try:
        with connect_read_only(oracle_path) as con:
            result.oracle_connected = True
            oracle_ids = {
                int(sid)
                for (sid,) in con.execute(
                    "SELECT subject_id FROM mimiciv_hosp.patients"
                ).fetchall()
            }
    except OracleError as exc:
        result.compare_errors.append(str(exc))
        return
    except Exception as exc:
        result.compare_errors.append(f"Oracle query error: {exc}")
        return

    result.oracle_patient_count = len(oracle_ids)
    if result.oracle_patient_count != EXPECTED_PATIENT_COUNT:
        result.compare_errors.append(
            f"Oracle patient count is {result.oracle_patient_count}, "
            f"expected {EXPECTED_PATIENT_COUNT}"
        )

    result.set_match = bool(fhir_ids) and fhir_ids == oracle_ids
    result.only_fhir = sorted(fhir_ids - oracle_ids)
    result.only_oracle = sorted(oracle_ids - fhir_ids)
    if result.only_fhir:
        result.compare_errors.append(
            f"{len(result.only_fhir)} FHIR-only identifier(s): "
            f"{result.only_fhir[:10]}"
        )
    if result.only_oracle:
        result.compare_errors.append(
            f"{len(result.only_oracle)} oracle-only subject_id(s): "
            f"{result.only_oracle[:10]}"
        )


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_fhir_report(result: PreflightFhirResult, *, color: bool = True) -> str:
    """Render *result* as a human-readable report string."""
    lines: List[str] = []
    GREEN = "\033[92m" if color else ""
    RED = "\033[91m" if color else ""
    RESET = "\033[0m" if color else ""

    def gate_mark(passed: bool) -> str:
        return f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"

    def bullet(items: List[str]) -> None:
        for item in items:
            lines.append(f"    {RED}x{RESET} {item}")

    lines.append("=" * 68)
    lines.append("  MIMIC-on-FHIR / Pathling Integration Preflight")
    lines.append(f"  FHIR:   {result.base_url}")
    lines.append(f"  Oracle: {result.duckdb_path}")
    lines.append("=" * 68)
    lines.append("")

    # --- Gate 1 --------------------------------------------------------------
    lines.append(f"  Gate 1 — CapabilityStatement .. {gate_mark(result.gate1_passed)}")
    if not result.capstmt_ok:
        bullet(result.capstmt_errors)
        lines.append("")
        lines.append(f"  {RED}Aborting — no usable CapabilityStatement.{RESET}")
        return "\n".join(lines)

    compliance = "compliant" if result.fhir_40_compliant else "non-compliant"
    lines.append(f"    FHIR version ......... {result.fhir_version} ({compliance})")
    lines.append(f"    ViewDefinition ....... {_yn(result.has_view_definition)}")
    lines.append(f"    Library .............. {_yn(result.has_library)}")
    lines.append(f"    $sqlquery-run ........ {_yn(result.has_sqlquery_run)}")
    if result.pathling_version:
        lines.append(f"    Pathling version ..... {result.pathling_version}")
    bullet(result.capstmt_errors)
    lines.append("")

    # --- Gate 2 --------------------------------------------------------------
    lines.append(f"  Gate 2 — ViewDefinition PUT ... {gate_mark(result.gate2_passed)}")
    if result.vd_put_ok:
        lines.append(f"    PUT ViewDefinition/{PREFLIGHT_VD_ID}")
    bullet(result.vd_put_errors)
    lines.append("")

    # --- Gate 3 --------------------------------------------------------------
    lines.append(f"  Gate 3 — $sqlquery-run ........ {gate_mark(result.gate3_passed)}")
    if result.sql_run_ok:
        lines.append(f"    NDJSON rows returned . {result.sql_row_count}")
    bullet(result.sql_run_errors)
    lines.append("")

    # --- Gate 4 --------------------------------------------------------------
    lines.append(f"  Gate 4 — Cohort identity ...... {gate_mark(result.gate4_passed)}")
    lines.append(f"    Oracle opened ........ {_yn(result.oracle_connected)}")
    lines.append(f"    Oracle subject_ids ... {result.oracle_patient_count}")
    lines.append(f"    FHIR identifiers ..... {result.fhir_patient_count}")
    lines.append(f"    Expected ............. {EXPECTED_PATIENT_COUNT}")
    lines.append(
        f"    Set identity ......... "
        f"{'exact match' if result.set_match else 'MISMATCH'}"
    )
    bullet(result.compare_errors)
    lines.append("")

    lines.append("=" * 68)
    lines.append(
        f"  {GREEN}Overall: PASS{RESET}" if result.passed else f"  {RED}Overall: FAIL{RESET}"
    )
    bullet(result.errors)
    lines.append("=" * 68)

    return "\n".join(lines)


def _yn(value: bool) -> str:
    return "yes" if value else "no"


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def preflight_fhir_cli(args: Optional[List[str]] = None) -> int:
    """Run the FHIR preflight from an argument list.  0 = pass, 1 = fail."""
    import argparse

    parser = argparse.ArgumentParser(
        description="MIMIC-on-FHIR / Pathling integration preflight check."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            f"Pathling FHIR base URL "
            f"(default: ${BASE_URL_ENV_KEY} or {DEFAULT_BASE_URL})."
        ),
    )
    parser.add_argument(
        "--duckdb",
        default=None,
        help=f"DuckDB oracle path (default from ${DUCKDB_ENV_KEY} or built-in).",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colours.")
    opts = parser.parse_args(args)

    result = run_preflight_fhir(
        fhir_base_url=opts.base_url, duckdb_path=opts.duckdb
    )
    print(format_fhir_report(result, color=not opts.no_color))
    return 0 if result.passed else 1
