"""Read-only DuckDB preflight check for the MIMIC-IV 2.2 demo oracle.

Establishes that the local source-of-truth oracle is the database the
concept-port loop thinks it is, before any concept work starts.

Gates (all must pass)
---------------------
1. **File** — the DuckDB file exists and opens with ``read_only=True``.
2. **Schemas** — ``mimiciv_hosp``, ``mimiciv_icu`` and ``mimiciv_derived``
   are all present.
3. **Row counts** — every table in :data:`DEMO_EXACT_COUNTS` has its exact
   count from ``mimic-iv/buildmimic/postgres/validate_demo.sql``.  Those
   counts are properties of the MIMIC-IV 2.2 demo *dataset*, not of the
   build engine, so they apply unchanged to the DuckDB build.
4. **Concepts** — every concept in the generated DAG exists as a table in
   ``mimiciv_derived``.

``neuroblock`` is legitimately empty on the demo dataset (no qualifying
administrations in the 100-patient sample), so an empty concept table is
reported as expected rather than as a failed build.  Any *other* empty
concept table is surfaced as a warning, because it usually means a concept
build step silently produced nothing.

The file SHA-256 and DuckDB version are recorded so an attempt can be tied
back to an exact oracle.

Path resolution
---------------
``--duckdb PATH`` -> ``MIMIC_DUCKDB_PATH`` -> ``/Users/nau025/warehouses/mimic4-demo.db``
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mimic_utils.duckdb_oracle import (
    DERIVED_SCHEMA,
    ENV_KEY,
    REQUIRED_SCHEMAS,
    OracleError,
    connect_read_only,
    duckdb_version,
    file_sha256,
    list_schemas,
    list_tables,
    resolve_duckdb_path,
)

# ---------------------------------------------------------------------------
# Exact demo row counts — sourced from
#  mimic-iv/buildmimic/postgres/validate_demo.sql
#
# These are dataset facts (MIMIC-IV 2.2 demo, 100 patients) and are engine
# independent; validate_demo.sql lives under buildmimic/postgres only for
# historical reasons.
# ---------------------------------------------------------------------------

DEMO_EXACT_COUNTS: Dict[str, Dict[str, int]] = {
    "mimiciv_hosp": {
        "admissions":           275,
        "d_hcpcs":            89200,
        "d_icd_diagnoses":   109775,
        "d_icd_procedures":   85257,
        "d_labitems":          1622,
        "diagnoses_icd":       4506,
        "drgcodes":             454,
        "emar":               35835,
        "emar_detail":        72018,
        "hcpcsevents":           61,
        "labevents":         107727,
        "microbiologyevents":  2899,
        "omr":                 2964,
        "patients":             100,
        "pharmacy":           15306,
        "poe":                45154,
        "poe_detail":          3795,
        "prescriptions":      18087,
        "procedures_icd":       722,
        "services":             319,
        "transfers":           1190,
    },
    "mimiciv_icu": {
        "icustays":             140,
        "d_items":             4014,
        "chartevents":       668862,
        "datetimeevents":     15280,
        "inputevents":        20404,
        "outputevents":        9362,
        "procedureevents":     1468,
    },
}

# Concepts that are legitimately empty on the 100-patient demo sample.
EXPECTED_EMPTY_CONCEPTS = frozenset({"neuroblock"})


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class PreflightResult:
    """Aggregate result of the DuckDB preflight check."""

    path: str
    duckdb_version: str = ""
    sha256: str = ""
    opened_read_only: bool = False
    schemas_found: List[str] = field(default_factory=list)
    schemas_missing: List[str] = field(default_factory=list)
    count_checks: List[Dict[str, Any]] = field(default_factory=list)
    concepts_expected: int = 0
    concepts_found: List[str] = field(default_factory=list)
    concepts_missing: List[str] = field(default_factory=list)
    expected_empty_concepts: List[str] = field(default_factory=list)
    unexpected_empty_concepts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def schemas_ok(self) -> bool:
        return bool(self.schemas_found) and not self.schemas_missing

    @property
    def counts_ok(self) -> bool:
        """True when every checked table matched its exact expected count."""
        if not self.count_checks:
            return False
        for cc in self.count_checks:
            if cc.get("error") is not None:
                return False
            if cc.get("count") != cc.get("expected"):
                return False
        return True

    @property
    def concepts_ok(self) -> bool:
        return self.concepts_expected > 0 and not self.concepts_missing

    @property
    def passed(self) -> bool:
        """Preflight passes only when all four gates are green."""
        return (
            self.opened_read_only
            and self.schemas_ok
            and self.counts_ok
            and self.concepts_ok
        )


# ---------------------------------------------------------------------------
# Concept list
# ---------------------------------------------------------------------------


def _dag_concepts(repo_root: Optional[Path] = None) -> List[str]:
    """Concept stems from the generated DAG artifact, sorted.

    Returns an empty list when the artifact is missing; the caller records
    that as an error rather than crashing the whole preflight.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    dag_path = repo_root / "mimic-iv" / "concept_dag" / "concept_dag.json"
    if not dag_path.exists():
        return []
    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    return sorted(dag.get("nodes", {}).keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_preflight(
    path: Optional[str | Path] = None,
    *,
    repo_root: Optional[Path] = None,
) -> PreflightResult:
    """Perform the read-only DuckDB preflight and return a result object."""
    resolved = resolve_duckdb_path(path)
    result = PreflightResult(path=str(resolved), duckdb_version=duckdb_version())

    try:
        with connect_read_only(resolved) as con:
            result.opened_read_only = True

            # -- 1. file identity ---------------------------------------------
            try:
                result.sha256 = file_sha256(resolved)
            except OSError as exc:
                result.errors.append(f"Cannot hash oracle file: {exc}")

            # -- 2. schemas ---------------------------------------------------
            found = set(list_schemas(con))
            result.schemas_found = sorted(found)
            result.schemas_missing = [s for s in REQUIRED_SCHEMAS if s not in found]
            if result.schemas_missing:
                result.errors.append(
                    f"Required schemas not found: {result.schemas_missing}"
                )

            # -- 3. exact row counts ------------------------------------------
            for schema, tables in DEMO_EXACT_COUNTS.items():
                if schema not in found:
                    continue
                for table, expected in tables.items():
                    entry: Dict[str, Any] = {
                        "schema": schema,
                        "table": table,
                        "expected": expected,
                    }
                    try:
                        count = con.execute(
                            f'SELECT COUNT(*) FROM "{schema}"."{table}"'
                        ).fetchone()[0]
                        entry["count"] = int(count)
                        entry["match"] = int(count) == expected
                    except Exception as exc:
                        entry["count"] = None
                        entry["match"] = False
                        entry["error"] = str(exc)
                    result.count_checks.append(entry)

            # -- 4. concept tables --------------------------------------------
            concepts = _dag_concepts(repo_root)
            result.concepts_expected = len(concepts)
            if not concepts:
                result.errors.append(
                    "concept_dag.json not found or empty — run "
                    "`mimic_utils concept_dag` first"
                )
            elif DERIVED_SCHEMA in found:
                derived_tables = set(list_tables(con, DERIVED_SCHEMA))
                result.concepts_found = [c for c in concepts if c in derived_tables]
                result.concepts_missing = [
                    c for c in concepts if c not in derived_tables
                ]
                if result.concepts_missing:
                    result.errors.append(
                        f"{len(result.concepts_missing)} DAG concept table(s) "
                        f"missing from {DERIVED_SCHEMA}: "
                        f"{result.concepts_missing[:10]}"
                    )
                for concept in result.concepts_found:
                    try:
                        n = con.execute(
                            f'SELECT COUNT(*) FROM "{DERIVED_SCHEMA}"."{concept}"'
                        ).fetchone()[0]
                    except Exception as exc:
                        result.errors.append(f"Cannot count {concept}: {exc}")
                        continue
                    if n:
                        continue
                    if concept in EXPECTED_EMPTY_CONCEPTS:
                        result.expected_empty_concepts.append(concept)
                    else:
                        result.unexpected_empty_concepts.append(concept)

    except OracleError as exc:
        result.errors.append(str(exc))
    except Exception as exc:
        result.errors.append(f"Preflight runtime error: {exc}")

    return result


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_report(result: PreflightResult, *, color: bool = True) -> str:
    """Render *result* as a human-readable report string."""
    lines: List[str] = []
    GREEN = "\033[92m" if color else ""
    RED = "\033[91m" if color else ""
    YELLOW = "\033[93m" if color else ""
    RESET = "\033[0m" if color else ""

    def gate_mark(passed: bool) -> str:
        return f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"

    lines.append("=" * 68)
    lines.append("  MIMIC-IV 2.2 Demo Oracle Preflight (DuckDB, read-only)")
    lines.append(f"  File:    {result.path}")
    lines.append(f"  DuckDB:  {result.duckdb_version}")
    if result.sha256:
        lines.append(f"  SHA256:  {result.sha256}")
    lines.append("=" * 68)
    lines.append("")

    lines.append(f"  Gate 1 — Open read-only ..... {gate_mark(result.opened_read_only)}")
    if not result.opened_read_only:
        for e in result.errors:
            lines.append(f"    {RED}x{RESET} {e}")
        lines.append("")
        lines.append(f"  {RED}Overall: FAIL{RESET}")
        return "\n".join(lines)

    # -- schemas --
    lines.append(f"  Gate 2 — Required schemas ... {gate_mark(result.schemas_ok)}")
    lines.append(f"    Found:   {result.schemas_found or '(none)'}")
    if result.schemas_missing:
        lines.append(f"    Missing: {result.schemas_missing}")

    # -- exact counts --
    lines.append("")
    lines.append(f"  Gate 3 — Exact row counts ... {gate_mark(result.counts_ok)}")
    if result.count_checks:
        lines.append(
            f"    {'Schema':<16} {'Table':<22} {'Count':>9}  {'Expected':>9}  Match"
        )
        lines.append(f"    {'-' * 62}")
        for cc in result.count_checks:
            err = cc.get("error")
            if err:
                lines.append(
                    f"    {cc['schema']:<16} {cc['table']:<22} {'ERROR':>9}  "
                    f"{cc['expected']:>9}  {RED}ERR{RESET}  ({err})"
                )
                continue
            flag = f"{GREEN}ok{RESET}" if cc["match"] else f"{RED}x{RESET}"
            lines.append(
                f"    {cc['schema']:<16} {cc['table']:<22} {cc['count']:>9,}  "
                f"{cc['expected']:>9,}  {flag}"
            )
    else:
        lines.append("    (no count checks executed)")

    # -- concepts --
    lines.append("")
    lines.append(f"  Gate 4 — DAG concept tables . {gate_mark(result.concepts_ok)}")
    lines.append(
        f"    Present: {len(result.concepts_found)}/{result.concepts_expected} "
        f"in {DERIVED_SCHEMA}"
    )
    if result.concepts_missing:
        lines.append(f"    Missing: {result.concepts_missing}")
    if result.expected_empty_concepts:
        lines.append(
            f"    Empty (expected on demo): {result.expected_empty_concepts}"
        )
    if result.unexpected_empty_concepts:
        lines.append(
            f"    {YELLOW}Empty (unexpected){RESET}: "
            f"{result.unexpected_empty_concepts}"
        )

    lines.append("")
    lines.append("=" * 68)
    if result.passed:
        lines.append(f"  {GREEN}Overall: PASS{RESET}")
        if result.unexpected_empty_concepts:
            lines.append(
                f"  {YELLOW}Warning{RESET}: "
                f"{len(result.unexpected_empty_concepts)} concept table(s) are "
                f"empty but not known-empty on the demo dataset."
            )
    else:
        lines.append(f"  {RED}Overall: FAIL{RESET}")
        for err in result.errors:
            lines.append(f"    - {err}")
    lines.append("=" * 68)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def preflight_cli(args: Optional[List[str]] = None) -> int:
    """Run the preflight from an argument list.  Returns a process exit code.

    Usage::

        mimic_utils preflight [--duckdb PATH] [--no-color]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Read-only MIMIC-IV 2.2 demo DuckDB oracle preflight check."
    )
    parser.add_argument(
        "--duckdb",
        default=None,
        help=f"Path to the DuckDB oracle (default from ${ENV_KEY} or built-in).",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colours.")
    opts = parser.parse_args(args)

    resolved = resolve_duckdb_path(opts.duckdb)
    print(f"Opening {resolved} read-only ...")
    result = run_preflight(resolved)
    print(format_report(result, color=not opts.no_color))
    return 0 if result.passed else 1
