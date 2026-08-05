"""Generic Pathling demo runner for a concept-port attempt.

Takes an attempt directory containing the two hand-authored artifacts:

``ViewDefinition.<label>.json``
    One or more SQL-on-FHIR ViewDefinitions.  ``<label>`` in the filename is
    the SQL table name the concept SQL selects from, and must equal the
    ViewDefinition's ``name``.
``concept.sql``
    Spark SQL producing the ported concept, selecting from those labels.

and drives the proven Pathling provisioning flow end to end:

1. PUT each ViewDefinition under an **attempt-scoped** id and canonical, so
   two attempts at the same concept never overwrite each other's definitions.
2. PUT ``concept.sql`` as a stored ``sql-view`` Library labelled with the
   concept name, carrying every ViewDefinition as a ``depends-on``
   relatedArtifact.
3. ``DESCRIBE <concept>`` to get the authoritative column order and Spark
   types.
4. ``SELECT * FROM <concept>`` to get the full result.
5. Write ``candidate.demo.ndjson`` — a DuckDB-scannable result file.
6. Run the **shape gate** against the oracle manifest and write
   ``shape.demo.json``.

This is a **cheap shape gate, not a correctness gate**.  See
``mimic-iv/concepts_fhir/LOOP_CONTRACT.md``, which is authoritative.  It exists
to stop a malformed port from consuming a 10-30 minute HPC run, and checks only:

* did the ViewDefinition and SQL execute at all,
* do the column **names** match the oracle's,
* are the column **types** compatible.

Row count is **not** gated here, and **0 rows yields ``unsure``, never
``fail``** -- the 100-patient demo cohort legitimately contains nothing for
some concepts (``neuroblock`` has 0 demo rows and 14,174 on full data).

Consequently the demo run needs **no oracle export**: the target shape comes
from ``oracle_manifest.full.json``.  Correctness is decided later, on full
data, by the keyed diff.

The verdict is never hand-calculated: it comes from
:func:`mimic_utils.compare_port_results.compare_shape`.

Attempt artifacts are write-once.  A re-run needs a new attempt, so the
runner refuses to overwrite ``candidate.demo.ndjson`` or ``shape.demo.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mimic_utils.compare_port_results import compare_shape, write_comparison
from mimic_utils.export_oracle import _serialise_value
from mimic_utils.pathling import (
    LIBRARY_KIND_SQL_VIEW,
    PathlingClient,
    PathlingError,
    RelatedArtifact,
    build_sqlquery_library,
    resolve_base_url,
)

VIEWDEFINITION_GLOB = "ViewDefinition.*.json"
CONCEPT_SQL_NAME = "concept.sql"
CANDIDATE_NAME = "candidate.demo.ndjson"
SHAPE_NAME = "shape.demo.json"

# Default manifest location, relative to the repo root.
DEFAULT_MANIFEST = Path("mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json")

# Canonical URL namespace for attempt-scoped port resources.
CANONICAL_BASE = "http://mimic.mit.edu/fhir/port"

# FHIR resource ids allow only [A-Za-z0-9-.] and are capped at 64 chars.
_FHIR_ID_ALLOWED = re.compile(r"[^A-Za-z0-9.-]")
_FHIR_ID_MAX = 64


class DemoRunError(RuntimeError):
    """A demo run could not be executed (missing artifacts, bad definitions)."""


def _fhir_id(*parts: str) -> str:
    """Join *parts* into a legal, deterministic FHIR resource id."""
    raw = "-".join(p for p in parts if p)
    cleaned = _FHIR_ID_ALLOWED.sub("-", raw).strip("-")
    if len(cleaned) > _FHIR_ID_MAX:
        # Keep the tail: the discriminating part (label) is at the end.
        cleaned = cleaned[-_FHIR_ID_MAX:].lstrip("-")
    if not cleaned:
        raise DemoRunError(f"Cannot derive a FHIR id from {parts!r}")
    return cleaned


@dataclass
class DemoRunResult:
    """Everything the run produced, plus the comparator's verdict."""

    concept: str
    attempt_dir: str
    base_url: str
    scope: str = ""
    view_definitions: List[Dict[str, str]] = field(default_factory=list)
    library_url: str = ""
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    column_types: Dict[str, str] = field(default_factory=dict)
    candidate_path: str = ""
    shape_path: str = ""
    compared: bool = False
    verdict: Optional[str] = None  # shape_ok | unsure | shape_fail
    schema_diagnostics: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def executed(self) -> bool:
        """True when the concept ran and a candidate artifact was written."""
        return bool(self.candidate_path) and not self.errors

    @property
    def blocked(self) -> bool:
        """True only when the shape gate positively rejected the port.

        This is the ONLY demo outcome that stops a concept. ``unsure`` (0 rows)
        does not block: the demo cohort may legitimately hold nothing, so the
        port proceeds to full-data validation.
        """
        return self.verdict == "shape_fail" or bool(self.errors)

    @property
    def may_proceed_to_full(self) -> bool:
        """True when the port has earned an HPC run.

        Both ``shape_ok`` and ``unsure`` qualify. Note this is *permission to
        spend a full run*, never evidence of correctness -- correctness is
        decided only by the full-data keyed diff.
        """
        return self.executed and self.verdict in ("shape_ok", "unsure")


# ---------------------------------------------------------------------------
# Attempt-directory discovery
# ---------------------------------------------------------------------------


def resolve_attempt_dir(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    attempt: Optional[int] = None,
) -> Path:
    """Resolve the attempt directory to run.

    An explicit *attempt_dir* wins, which is how a controlled or temporary
    run is done without touching durable state.  Otherwise the state
    controller supplies the concept's current attempt directory (or the
    explicitly numbered one).
    """
    if attempt_dir is not None:
        resolved = Path(attempt_dir).expanduser().resolve()
        if not resolved.is_dir():
            raise DemoRunError(f"Attempt directory not found: {resolved}")
        return resolved

    # Imported lazily: a temp-dir run should not require initialised state.
    from mimic_utils.conversion_state import ConversionController

    controller = ConversionController(artifact_root=artifact_root)
    if attempt is not None:
        resolved = controller._attempt_dir(concept, attempt)
        if not resolved.is_dir():
            raise DemoRunError(
                f"Attempt {attempt:04d} for '{concept}' not found: {resolved}"
            )
        return resolved

    found = controller.attempt_dir(concept)
    if found is None:
        raise DemoRunError(
            f"No attempt directory for '{concept}'. Run `mimic_utils start "
            f"{concept}` first, or pass --attempt-dir for a controlled run."
        )
    return found


def discover_view_definitions(attempt: Path) -> List[Dict[str, Any]]:
    """Load every ``ViewDefinition.<label>.json`` in *attempt*, sorted by label.

    The filename label is authoritative for the SQL table name, so a
    ViewDefinition whose ``name`` disagrees with its filename is rejected:
    the concept SQL would silently select from a table that was never
    registered.
    """
    definitions: List[Dict[str, Any]] = []
    for path in sorted(attempt.glob(VIEWDEFINITION_GLOB)):
        label = path.name[len("ViewDefinition.") : -len(".json")]
        if not label:
            raise DemoRunError(f"ViewDefinition file has an empty label: {path.name}")
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DemoRunError(f"{path.name} is not valid JSON: {exc}") from exc
        if body.get("resourceType") != "ViewDefinition":
            raise DemoRunError(
                f"{path.name} has resourceType "
                f"{body.get('resourceType')!r}, expected 'ViewDefinition'"
            )
        declared = body.get("name")
        if declared is not None and declared != label:
            raise DemoRunError(
                f"{path.name}: ViewDefinition name {declared!r} does not match "
                f"the filename label {label!r} — the concept SQL selects from "
                f"the label, so these must agree"
            )
        body["name"] = label
        definitions.append({"label": label, "path": path, "body": body})
    if not definitions:
        raise DemoRunError(
            f"No {VIEWDEFINITION_GLOB} files in {attempt} — nothing to register"
        )
    return definitions


def read_concept_sql(attempt: Path) -> str:
    """Read ``concept.sql`` from *attempt*."""
    path = attempt / CONCEPT_SQL_NAME
    if not path.is_file():
        raise DemoRunError(f"{CONCEPT_SQL_NAME} not found in {attempt}")
    sql = path.read_text(encoding="utf-8").strip()
    if not sql:
        raise DemoRunError(f"{path} is empty")
    return sql


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_demo(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    base_url: Optional[str] = None,
    manifest_path: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    repo_root: Optional[Path] = None,
    attempt: Optional[int] = None,
    skip_compare: bool = False,
    client: Optional[PathlingClient] = None,
) -> DemoRunResult:
    """Register, execute and shape-check one concept-port attempt on demo data.

    The runner never reads an oracle database.  The target shape comes from
    *manifest_path* (default ``oracle_manifest.full.json``), so no
    ``export-oracle`` step is required for the demo gate.

    A ``shape_ok`` or ``unsure`` verdict earns permission to spend a full-data
    HPC run; neither is evidence of correctness.
    """
    resolved_attempt = resolve_attempt_dir(
        concept,
        attempt_dir=attempt_dir,
        artifact_root=artifact_root,
        attempt=attempt,
    )
    resolved_base = resolve_base_url(base_url)
    result = DemoRunResult(
        concept=concept,
        attempt_dir=str(resolved_attempt),
        base_url=resolved_base,
    )

    candidate_path = resolved_attempt / CANDIDATE_NAME
    if candidate_path.exists():
        result.errors.append(
            f"{CANDIDATE_NAME} already exists (attempts are write-once); "
            f"start a new attempt instead of re-running this one"
        )
        return result

    definitions = discover_view_definitions(resolved_attempt)
    sql = read_concept_sql(resolved_attempt)

    # Attempt-scoped identity: <concept>-<attempt dir name>.
    scope = f"{concept}-{resolved_attempt.name}"
    result.scope = scope
    if client is None:
        client = PathlingClient(resolved_base)

    # -- 1. register the ViewDefinitions ------------------------------------
    dependencies: List[RelatedArtifact] = []
    for definition in definitions:
        label = definition["label"]
        vd_id = _fhir_id("port", scope, "vd", label)
        vd_url = f"{CANONICAL_BASE}/{scope}/ViewDefinition/{label}"
        body = {**definition["body"], "url": vd_url}
        try:
            client.put_definitional(
                resource_type="ViewDefinition",
                resource_id=vd_id,
                resource_body=body,
            )
        except PathlingError as exc:
            result.errors.append(f"ViewDefinition {label!r} registration failed: {exc}")
            return result
        result.view_definitions.append({"label": label, "id": vd_id, "url": vd_url})
        dependencies.append(RelatedArtifact(label=label, resource=vd_url))

    # -- 2. register the concept as a stored sql-view Library ----------------
    library_id = _fhir_id("port", scope, "lib")
    library_url = f"{CANONICAL_BASE}/{scope}/Library/{concept}"
    result.library_url = library_url
    library = build_sqlquery_library(
        sql,
        dependencies,
        kind=LIBRARY_KIND_SQL_VIEW,
        url=library_url,
        name=concept,
    )
    try:
        client.put_definitional(
            resource_type="Library",
            resource_id=library_id,
            resource_body=library,
        )
    except PathlingError as exc:
        result.errors.append(f"sql-view Library registration failed: {exc}")
        return result

    library_dep = [RelatedArtifact(label=concept, resource=library_url)]

    # -- 3. authoritative column order and types ----------------------------
    try:
        result.column_types = client.describe_columns(concept, library_dep)
    except PathlingError as exc:
        result.errors.append(f"DESCRIBE {concept} failed: {exc}")
        return result
    if not result.column_types:
        result.errors.append(f"DESCRIBE {concept} returned no columns")
        return result
    result.columns = list(result.column_types.keys())

    # -- 4. execute ---------------------------------------------------------
    try:
        raw_rows = client.sqlquery_run_dicts(f"SELECT * FROM {concept}", library_dep)
    except PathlingError as exc:
        result.errors.append(f"SELECT * FROM {concept} failed: {exc}")
        return result

    # NDJSON omits null-valued keys, so DESCRIBE order is the source of truth.
    unexpected = sorted(
        {key for row in raw_rows for key in row} - set(result.columns)
    )
    if unexpected:
        result.errors.append(
            f"Result rows carry columns absent from DESCRIBE {concept}: {unexpected}"
        )
        return result

    result.row_count = len(raw_rows)

    # -- 5. write the candidate as NDJSON -----------------------------------
    # NDJSON rather than the old rows-in-JSON artifact: DuckDB scans it
    # natively, so the comparator never materialises rows into Python.
    if candidate_path.exists():
        result.errors.append(
            f"{CANDIDATE_NAME} already exists (attempts are write-once)"
        )
        return result
    with candidate_path.open("w", encoding="utf-8") as fh:
        for row in raw_rows:
            fh.write(
                json.dumps(
                    {col: _serialise_value(row.get(col)) for col in result.columns},
                    ensure_ascii=False,
                )
                + "\n"
            )
    result.candidate_path = str(candidate_path)

    # -- 6. shape gate against the oracle manifest --------------------------
    # No oracle export: the target shape comes from the manifest. Row count is
    # NOT gated here and 0 rows is `unsure`, never `fail` -- see LOOP_CONTRACT.
    if skip_compare:
        return result

    manifest = Path(manifest_path) if manifest_path else _default_manifest(repo_root)
    if not manifest.is_file():
        result.errors.append(
            f"Oracle manifest not found: {manifest} — generate it with "
            f"`mimic_utils.oracle_manifest`"
        )
        return result

    shape_path = resolved_attempt / SHAPE_NAME
    if shape_path.exists():
        result.errors.append(f"{SHAPE_NAME} already exists (attempts are write-once)")
        return result

    comparison = compare_shape(concept, manifest, candidate_path)
    result.shape_path = str(write_comparison(comparison, shape_path))
    result.compared = True
    result.verdict = comparison.get("verdict")

    schema = comparison.get("schema") or {}
    for field_name in ("missing_columns", "extra_columns"):
        if schema.get(field_name):
            result.schema_diagnostics.append(f"{field_name}: {schema[field_name]}")
    for bad in schema.get("incompatible_types", []):
        result.schema_diagnostics.append(
            f"column {bad['column']!r}: expected {bad['expected']}, got {bad['actual']}"
        )
    return result


def _default_manifest(repo_root: Optional[Path]) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    return root / DEFAULT_MANIFEST


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_demo_report(result: DemoRunResult, *, color: bool = True) -> str:
    """Render *result* as a human-readable report string."""
    lines: List[str] = []
    GREEN = "\033[92m" if color else ""
    RED = "\033[91m" if color else ""
    YELLOW = "\033[93m" if color else ""
    RESET = "\033[0m" if color else ""

    lines.append("=" * 68)
    lines.append(f"  Pathling demo run — concept '{result.concept}'")
    lines.append(f"  Attempt: {result.attempt_dir}")
    lines.append(f"  FHIR:    {result.base_url}")
    lines.append("=" * 68)
    lines.append("")

    if result.view_definitions:
        lines.append("  Registered ViewDefinitions:")
        for vd in result.view_definitions:
            lines.append(f"    {vd['label']:<28} {vd['id']}")
    if result.library_url:
        lines.append(f"  sql-view Library: {result.library_url}")
    lines.append("")

    if result.columns:
        lines.append(f"  Result columns ({len(result.columns)}):")
        for col in result.columns:
            lines.append(f"    {col:<28} {result.column_types.get(col, '?')}")
        # Explicitly labelled: the demo gate does not compare row counts.
        lines.append(f"  Result rows: {result.row_count:,}  (observation — not gated)")
        lines.append("")

    if result.candidate_path:
        lines.append(f"  Candidate:  {result.candidate_path}")
    if result.shape_path:
        lines.append(f"  Shape gate: {result.shape_path}")
    lines.append("")

    if result.compared:
        if result.verdict == "shape_ok":
            lines.append(f"  Shape gate: {GREEN}SHAPE OK{RESET}")
            lines.append("    Proceed to full-data validation. This is NOT")
            lines.append("    evidence of correctness.")
        elif result.verdict == "unsure":
            lines.append(f"  Shape gate: {YELLOW}UNSURE{RESET} (0 rows)")
            lines.append("    The demo cohort may legitimately contain nothing")
            lines.append("    for this concept. Not a failure — proceed to full data.")
        else:
            lines.append(f"  Shape gate: {RED}SHAPE FAIL{RESET}")
        for diag in result.schema_diagnostics:
            lines.append(f"    {RED}x{RESET} {diag}")
    elif result.executed:
        lines.append(f"  {YELLOW}Shape gate not run{RESET} (--skip-compare).")

    for err in result.errors:
        lines.append(f"    {RED}x{RESET} {err}")

    lines.append("")
    lines.append("=" * 68)
    if result.blocked:
        lines.append(f"  {RED}Overall: BLOCKED — fix the port before spending an HPC run{RESET}")
    elif result.may_proceed_to_full:
        lines.append(f"  {GREEN}Overall: MAY PROCEED TO FULL DATA{RESET}")
    else:
        lines.append(f"  {YELLOW}Overall: INCOMPLETE{RESET}")
    lines.append("=" * 68)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def run_demo_cli(args: Optional[List[str]] = None) -> int:
    """Run the demo shape gate.

    Exit codes: 0 shape_ok, 1 shape_fail/error, 2 unsure (0 rows -- neither a
    pass nor a failure; proceed to full data).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute a concept-port attempt on the local demo Pathling "
        "instance and check its SHAPE against the oracle manifest. Row count is "
        "not gated; 0 rows yields 'unsure'."
    )
    parser.add_argument("concept", help="Concept stem (e.g. age).")
    parser.add_argument(
        "--attempt-dir", default=None,
        help="Attempt directory to run (default: the concept's current attempt).",
    )
    parser.add_argument(
        "--attempt", type=int, default=None,
        help="Explicit attempt number instead of the current one.",
    )
    parser.add_argument("--base-url", default=None, help="Pathling FHIR base URL.")
    parser.add_argument(
        "--manifest", default=None,
        help="Oracle manifest JSON (default: oracle_manifest.full.json).",
    )
    parser.add_argument("--artifact-root", default=None, help="Artifact root directory.")
    parser.add_argument(
        "--skip-compare", action="store_true",
        help=f"Write {CANDIDATE_NAME} only; do not run the shape gate.",
    )
    parser.add_argument("--no-color", action="store_true")
    opts = parser.parse_args(args)

    result = run_demo(
        concept=opts.concept,
        attempt_dir=opts.attempt_dir,
        attempt=opts.attempt,
        base_url=opts.base_url,
        manifest_path=opts.manifest,
        artifact_root=opts.artifact_root,
        skip_compare=opts.skip_compare,
    )
    print(format_demo_report(result, color=not opts.no_color))
    if result.blocked:
        return 1
    if result.verdict == "unsure":
        return 2
    return 0 if result.may_proceed_to_full else 1
