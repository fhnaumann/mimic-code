"""Export finalized FHIR concept mappings as standalone, registerable artifacts.

Each satisfied concept becomes one directory holding everything a SQL-on-FHIR
server needs to serve it as a table:

``<concept>.sql``
    A *readability copy* of the shipped SQL, carrying a banner saying so.  The
    artifact a server actually loads is the Library beside it; this file exists
    because a base64 blob is unreviewable in a diff, and the SQL is the half of
    the experimental claim a reader most needs to see.

    The body is the finalized attempt's ``concept.sql`` with one class of edit
    applied: MIMIC identifier columns are excised from the outermost SELECT
    where the port also projects the paired FHIR resource key (see
    :func:`strip_mimic_ids`).  Nothing else is rewritten -- not the formatting,
    not the comments, not a single byte outside the excised projection items.
    The attempt directory keeps the verbatim record of what the judge signed
    off on, and the oracle comparison runs there, against the manifest columns,
    before any of this happens.

``ViewDefinition.<label>.json``
    Each ViewDefinition the attempt executed, copied verbatim apart from ``id``,
    ``url`` and ``version``.  ``name`` is deliberately left alone: it collides
    wildly across concepts (nine different ``lab_observation`` bodies alone) but
    plays no part in SQL table resolution, so renaming it would churn the
    artifact without buying anything.

``Library.<concept>.json``
    A generated SQL-on-FHIR ``sql-view`` Library, and the authoritative
    artifact.  It carries the SQL twice: base64 in ``content.data``, and as
    plain text in the ``sql-text`` extension the IG defines for exactly this
    purpose.  Both are written from the same string as the sidecar, and the
    export asserts all three agree before it commits.

    This is also what binds the two above together.  Table names in the SQL
    come from ``relatedArtifact.label``,
    scoped to this Library, which is why per-concept ViewDefinitions can share a
    ``name`` without shadowing each other.  Publishing every concept as a
    ``sql-view`` (rather than ``sql-query``) keeps it both runnable and legal as
    another concept's dependency -- a ``sql-query`` may not be depended upon.

Derived dependencies ride the same mechanism: ``charlson`` reads ``FROM age``,
so its Library binds the label ``age`` to ``age``'s own Library canonical.  The
bindings are read out of the SQL rather than off the DAG, because a concept can
declare a DAG dependency it never reads and an over-declared binding would
invent an upload-ordering constraint that does not exist.

Only concepts that are *registerable* are exported.  A port whose outermost
SELECT still carries a MIMIC identifier with no paired resource key cannot be
joined to FHIR data, so publishing it would put a table on a server that no
consumer can use; those are withheld and named in the report, and their SQL
stays visible in its ``attempt_*`` directory.  This is what lets
``register-derived-concepts`` treat the export directory itself as the set of
uploadable concepts instead of maintaining a separate allowlist that would drift
out of date.  See :func:`_withhold_unready`.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional, Union

import sqlglot
from sqlglot import exp
from sqlglot.tokens import TokenType

from mimic_utils.conversion_state import ConversionController, StateError


DEFAULT_EXPORT_DIR = "mimic-iv/concepts_fhir/artifacts"

CANONICAL_BASE = "https://fhnaumann.masters/pathling"
VIEWDEFINITION_BASE = f"{CANONICAL_BASE}/ViewDefinition"
LIBRARY_BASE = f"{CANONICAL_BASE}/Library"

LIBRARY_TYPE_SYSTEM = "https://sql-on-fhir.org/ig/CodeSystem/LibraryTypesCodes"
LIBRARY_TYPE_CODE = "sql-view"

#: The IG's extension for carrying the query as plain text beside the base64
#: ``Attachment.data``.  Sliced as ``Library.content.extension:sqlText``; its
#: declared context is Attachment, so it applies to a ``sql-view`` Library as
#: much as to a ``sql-query`` one.
SQL_TEXT_EXTENSION = "http://hl7.org/fhir/uv/sql-on-fhir/StructureDefinition/sql-text"

#: Bare ``application/sql`` asserts broadly portable ANSI, which this SQL is
#: not: it is Spark, and no ANSI engine will run ``TRY_CAST`` or
#: ``TIMESTAMP_NTZ``.  ``spark-sql`` is a code in the IG's AllSQLContentTypeCodes
#: value set, and its extensible binding says a covering code SHALL be used.
SQL_CONTENT_TYPE = "application/sql;dialect=spark-sql"

VIEWDEFINITION_GLOB = "ViewDefinition.*.json"
VIEWDEFINITION_PREFIX = "ViewDefinition."
CONCEPT_SQL_NAME = "concept.sql"

#: Parsing dialect for reading table references out of a candidate's SQL.  The
#: candidate runs on Spark through Pathling; all finalized concepts parse under
#: it.  Nothing is ever *generated* from the parse tree, only read, so this is a
#: comprehension aid rather than a fidelity requirement.
SQL_DIALECT = "spark"

_ATTEMPT_DIR_RE = re.compile(r"^attempt_(\d+)$")
_FHIR_ID_RE = re.compile(r"[^A-Za-z0-9.-]")
_FHIR_ID_MAX = 64

#: MIMIC identifier columns and the FHIR resource key each is the integer form
#: of.  The same pairing the loop's lint and comparator enforce on the way in
#: (``sql_lint._ID_TO_KEY``, ``compare_port_results._ID_TO_KEY``); this module
#: is where it is spent.
ID_TO_KEY = {
    "subject_id": "patient_key",
    "hadm_id": "encounter_key",
    "stay_id": "icu_encounter_key",
    "specimen_id": "specimen_key",
}

SIDECAR_BANNER = (
    "-- Readability copy -- not the artifact a server loads.\n"
    "--\n"
    "-- Library.{concept}.json in this directory is authoritative. This SQL is\n"
    "-- the decoded form of its content.data, byte-identical to the sql-text\n"
    "-- extension beside it. Edit neither: both are generated by\n"
    "-- `mimic-utils metrics-finalize` from the finalized attempt.\n"
    "\n"
)


# ---------------------------------------------------------------------------
# Table references
# ---------------------------------------------------------------------------


def _sqlglot_tables(concept: str, sql: str) -> set[str]:
    """Table names *sql* reads that are not satisfied by its own CTEs."""
    try:
        tree = sqlglot.parse_one(sql, dialect=SQL_DIALECT)
    except Exception as exc:  # sqlglot raises a family of parse errors
        raise StateError(
            f"Concept '{concept}': cannot parse concept.sql as {SQL_DIALECT}: {exc}"
        ) from exc
    ctes = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    tables = {
        table.name.lower()
        for table in tree.find_all(exp.Table)
        if not table.db and not table.catalog
    }
    return tables - ctes


def _regex_tables(sql: str) -> set[str]:
    """Independent, deliberately naive reading of the same table references.

    Kept only as a cross-check on :func:`_sqlglot_tables`.  It strips comments
    and string literals first, because a viewdef label can appear inside one --
    ``'…/CodeSystem/mimic-medication-name'`` contains ``medication`` -- and a
    reader that misses that would disagree loudly rather than silently.
    """
    body = re.sub(r"--[^\n]*", "", sql)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"'(?:[^']|'')*'", "''", body)
    ctes = {m.lower() for m in re.findall(r"(?:WITH|,)\s*([A-Za-z_]\w*)\s+AS\s*\(", body, re.I)}
    tables = {m.lower() for m in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_]\w*)", body, re.I)}
    return tables - ctes


def _referenced_tables(concept: str, sql: str) -> set[str]:
    """Agreed-upon set of external tables *sql* reads.

    A disagreement between the two readers is fatal rather than resolved in
    favour of either: an over-declared binding invents an upload-ordering edge,
    an under-declared one fails at query time, and neither is worth guessing at.
    """
    parsed = _sqlglot_tables(concept, sql)
    naive = _regex_tables(sql)
    if parsed != naive:
        raise StateError(
            f"Concept '{concept}': table references disagree between readers -- "
            f"sqlglot {sorted(parsed)} vs scan {sorted(naive)}"
        )
    return parsed


# ---------------------------------------------------------------------------
# MIMIC identifier strip
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StripResult:
    """What :func:`strip_mimic_ids` did to one concept."""

    sql: str
    #: Identifier columns removed, because the port projects their paired key.
    dropped: tuple[str, ...] = ()
    #: Identifier columns left in place, because it does not.  Removing these
    #: would leave the table with no way to be joined to anything at all.
    unpaired: tuple[str, ...] = ()


def _tokens(concept: str, sql: str) -> list:
    try:
        return sqlglot.Dialect.get_or_raise(SQL_DIALECT).tokenizer_class().tokenize(sql)
    except Exception as exc:  # sqlglot raises a family of tokenizer errors
        raise StateError(
            f"Concept '{concept}': cannot tokenize concept.sql as {SQL_DIALECT}: {exc}"
        ) from exc


def _projection_region(concept: str, sql: str) -> tuple[int, int, list[int], list[str]]:
    """Character span of the outermost select list, its commas, its comments.

    Worked out from the token stream rather than the parse tree because the
    parse tree has no positions -- projection nodes carry an empty ``meta`` --
    and regenerating SQL from it would reformat the whole file (``INTEGER``
    becomes ``INT``, wrapped CASTs collapse onto one line).  The point of this
    module is to ship the reviewed bytes, so the only safe edit is a textual
    excision the parser is then asked to confirm.

    Tokens are what make the scan safe: a comma inside a string literal or a
    comment never reaches the stream, and a comma between CTEs or inside a
    function call is not at depth 0.
    """
    depth = 0
    select_end: Optional[int] = None
    from_start: Optional[int] = None
    commas: list[int] = []
    comments: list[str] = []

    for token in _tokens(concept, sql):
        if token.token_type is TokenType.L_PAREN:
            depth += 1
            continue
        if token.token_type is TokenType.R_PAREN:
            depth -= 1
            continue
        if depth or from_start is not None:
            continue
        if token.token_type is TokenType.SELECT:
            if select_end is not None:
                raise StateError(
                    f"Concept '{concept}': more than one top-level SELECT; refusing "
                    f"to guess which one projects the output"
                )
            select_end = token.end + 1
            continue
        if select_end is None:
            # Still in the WITH clause: its commas separate CTEs, not columns.
            continue
        if token.token_type is TokenType.FROM:
            from_start = token.start
            continue
        if token.token_type is TokenType.COMMA:
            commas.append(token.start)
        comments.extend(token.comments)

    if select_end is None:
        raise StateError(f"Concept '{concept}': found no top-level SELECT")
    if from_start is None:
        raise StateError(
            f"Concept '{concept}': outermost SELECT has no top-level FROM, so the "
            f"end of its select list cannot be located"
        )
    return select_end, from_start, commas, comments


def strip_mimic_ids(concept: str, sql: str) -> StripResult:
    """Remove MIMIC identifier columns that a FHIR resource key already covers.

    The rule is one line: drop an identifier from the outermost SELECT iff the
    same SELECT projects its paired resource key.  ``subject_id`` beside
    ``patient_key`` is redundant -- consumers join on the key, and the integer
    is there because the oracle comparison needs it, which has already happened
    by the time anything is exported.  ``stay_id`` with no ``icu_encounter_key``
    is the port's only identity column, and dropping it would leave an
    unjoinable bag of measurements; those stay, and the export names them.

    Only the outermost projection is touched.  An identifier consumed inside a
    CTE, a WHERE or a GROUP BY is load-bearing and left exactly where it is --
    ``age`` filters on ``e.hadm_id_str IS NOT NULL`` and still does afterwards.
    """
    try:
        tree = sqlglot.parse_one(sql, dialect=SQL_DIALECT)
    except Exception as exc:  # sqlglot raises a family of parse errors
        raise StateError(
            f"Concept '{concept}': cannot parse concept.sql as {SQL_DIALECT}: {exc}"
        ) from exc

    # For a set operation this is the left arm, which is enough to answer
    # whether anything is droppable at all -- and if nothing is, the shape of
    # the statement never has to be argued about.
    select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    names = [item.alias_or_name for item in select.expressions] if select else []
    projected = set(names)
    dropped = tuple(
        name for name in names if ID_TO_KEY.get(name) in projected
    )
    unpaired = tuple(
        name for name in names if name in ID_TO_KEY and name not in dropped
    )
    if not dropped:
        return StripResult(sql, (), unpaired)

    if not isinstance(tree, exp.Select):
        # One arm of a set operation can project a column the other does not,
        # so there is no single select list whose edit is the whole edit.
        raise StateError(
            f"Concept '{concept}': outermost statement is {type(tree).__name__}, "
            f"not a SELECT, so {', '.join(dropped)} cannot be removed from one "
            f"select list alone"
        )

    if tree.args.get("distinct"):
        # Removing a column from a DISTINCT projection collapses rows that were
        # distinct only in that column, so the strip would change the row count
        # rather than just the shape.
        raise StateError(
            f"Concept '{concept}': outermost SELECT is DISTINCT; dropping "
            f"{', '.join(dropped)} would change its row count"
        )

    region_start, region_end, commas, comments = _projection_region(concept, sql)
    if comments:
        # A comment sits between two columns with nothing to say which one it
        # describes, and the commas move when a column goes. Rather than guess
        # -- and silently reattach a note to the wrong column, or leave one
        # dangling beside SELECT describing a column that is gone -- say so.
        raise StateError(
            f"Concept '{concept}': the outermost select list carries comment(s) "
            f"{comments}, which cannot be reattached unambiguously when "
            f"{', '.join(dropped)} is removed. Move them above the SELECT."
        )
    region = sql[region_start:region_end]
    body = region.rstrip()
    tail = region[len(body) :]

    chunks: list[str] = []
    cursor = region_start
    for comma in commas:
        chunks.append(sql[cursor:comma])
        cursor = comma + 1
    chunks.append(body[cursor - region_start :])

    if len(chunks) != len(names):
        # The two readers disagree about how many columns there are, so no
        # chunk can be trusted to be the column the parser named.
        raise StateError(
            f"Concept '{concept}': select list scans as {len(chunks)} column(s) "
            f"but parses as {len(names)} ({', '.join(names)})"
        )

    # Never empties the list: a column is only dropped because its key is
    # projected, and a key is never dropped.
    kept = [chunk for chunk, name in zip(chunks, names) if name not in dropped]
    stripped = sql[:region_start] + ",".join(kept) + tail + sql[region_end:]

    # The excision is textual, so the parser gets the last word on whether it
    # produced the intended query rather than a plausible-looking one.
    try:
        check = sqlglot.parse_one(stripped, dialect=SQL_DIALECT)
    except Exception as exc:  # sqlglot raises a family of parse errors
        raise StateError(
            f"Concept '{concept}': stripping {', '.join(dropped)} produced SQL that "
            f"no longer parses: {exc}"
        ) from exc
    expected = [name for name in names if name not in dropped]
    actual = [item.alias_or_name for item in check.expressions]
    if actual != expected:
        raise StateError(
            f"Concept '{concept}': stripping {', '.join(dropped)} left columns "
            f"{actual}, expected {expected}"
        )

    return StripResult(stripped, dropped, unpaired)


# ---------------------------------------------------------------------------
# Resource construction
# ---------------------------------------------------------------------------


def _fhir_id(concept: str, suffix: Optional[str] = None) -> str:
    """Build a FHIR ``id`` (which, unlike a URL, may not contain ``_``)."""
    raw = concept if suffix is None else f"{concept}-{suffix}"
    ident = _FHIR_ID_RE.sub("-", raw)
    if not ident or len(ident) > _FHIR_ID_MAX:
        raise StateError(
            f"Concept '{concept}': cannot form a FHIR id from {raw!r} "
            f"(got {ident!r}, limit {_FHIR_ID_MAX} characters)"
        )
    return ident


def _attempt_version(concept: str, attempt_dir: Path) -> str:
    """Read the attempt number off the directory actually being exported.

    Taken from the directory rather than the status report so that the version
    always describes the bytes shipped beside it.
    """
    match = _ATTEMPT_DIR_RE.match(attempt_dir.name)
    if not match:
        raise StateError(
            f"Concept '{concept}': cannot read an attempt number from {attempt_dir.name!r}"
        )
    return str(int(match.group(1)))


def _viewdef_label(path: Path) -> str:
    return path.name[len(VIEWDEFINITION_PREFIX) : -len(".json")]


def _load_viewdef(concept: str, path: Path, label: str, version: str) -> dict:
    """Copy a ViewDefinition, re-identifying it without touching its content."""
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"Concept '{concept}': cannot read {path}: {exc}") from exc
    if body.get("resourceType") != "ViewDefinition":
        raise StateError(
            f"Concept '{concept}': {path.name} has resourceType "
            f"{body.get('resourceType')!r}, expected 'ViewDefinition'"
        )
    body["id"] = _fhir_id(concept, label)
    body["url"] = f"{VIEWDEFINITION_BASE}/{concept}-{label}"
    body["version"] = version
    return body


def _build_library(
    concept: str,
    version: str,
    sql: str,
    bindings: dict[str, str],
) -> dict:
    """Assemble the ``sql-view`` Library that binds table names to canonicals."""
    return {
        "resourceType": "Library",
        "id": _fhir_id(concept),
        "url": f"{LIBRARY_BASE}/{concept}",
        "version": version,
        "name": concept,
        "status": "active",
        "type": {
            "coding": [{"system": LIBRARY_TYPE_SYSTEM, "code": LIBRARY_TYPE_CODE}]
        },
        "relatedArtifact": [
            {"type": "depends-on", "label": label, "resource": bindings[label]}
            for label in sorted(bindings)
        ],
        "content": [
            {
                "extension": [
                    {"url": SQL_TEXT_EXTENSION, "valueString": sql},
                ],
                "contentType": SQL_CONTENT_TYPE,
                "data": base64.b64encode(sql.encode("utf-8")).decode("ascii"),
            }
        ],
    }


def _assert_content_agrees(concept: str, library: dict, sidecar: str, sql: str) -> None:
    """The three copies of the SQL say the same thing.

    Three places to keep in step is two more than anyone can hold in their
    head, and two of them are unreadable by eye -- base64, and JSON-escaped
    text.  The check decodes rather than trusting the writer, so a future edit
    that touches one path and not the others fails here instead of shipping a
    Library whose human-readable half disagrees with what the server runs.
    """
    content = library["content"][0]
    decoded = base64.b64decode(content["data"]).decode("utf-8")
    sql_text = content["extension"][0]["valueString"]
    if decoded != sql:
        raise StateError(f"Concept '{concept}': content.data does not decode to the shipped SQL")
    if sql_text != sql:
        raise StateError(f"Concept '{concept}': sql-text extension differs from the shipped SQL")
    if sidecar != SIDECAR_BANNER.format(concept=concept) + sql:
        raise StateError(f"Concept '{concept}': sidecar SQL is not the banner plus the shipped SQL")


def _write_json(path: Path, body: dict) -> None:
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Bundle assembly
# ---------------------------------------------------------------------------


def _stage_concept(
    ctrl: ConversionController,
    concept: str,
    attempt_dir: Path,
    target_dir: Path,
) -> StripResult:
    """Write one concept's complete bundle into *target_dir*."""
    source_sql = attempt_dir / CONCEPT_SQL_NAME
    if not source_sql.is_file():
        raise StateError(
            f"Finalized concept '{concept}' has no {CONCEPT_SQL_NAME} at {source_sql}"
        )
    strip = strip_mimic_ids(concept, source_sql.read_text(encoding="utf-8"))
    sql = strip.sql
    version = _attempt_version(concept, attempt_dir)

    viewdefs = {
        _viewdef_label(path): path
        for path in sorted(attempt_dir.glob(VIEWDEFINITION_GLOB))
    }
    if not viewdefs:
        raise StateError(
            f"Finalized concept '{concept}' ships no ViewDefinitions in {attempt_dir}"
        )

    dependencies = {
        str(dep) for dep in (ctrl.dag_raw["nodes"][concept].get("dependencies") or [])
    }
    by_lower = {label.lower(): label for label in viewdefs}
    if len(by_lower) != len(viewdefs):
        raise StateError(
            f"Concept '{concept}': ViewDefinition labels differ only by case: "
            f"{sorted(viewdefs)}"
        )
    deps_by_lower = {dep.lower(): dep for dep in dependencies}

    bindings: dict[str, str] = {}
    unresolved: list[str] = []
    for table in sorted(_referenced_tables(concept, sql)):
        if table in by_lower:
            label = by_lower[table]
            bindings[label] = f"{VIEWDEFINITION_BASE}/{concept}-{label}"
        elif table in deps_by_lower:
            dep = deps_by_lower[table]
            bindings[dep] = f"{LIBRARY_BASE}/{dep}"
        else:
            unresolved.append(table)
    if unresolved:
        raise StateError(
            f"Concept '{concept}' reads {unresolved} which is neither a shipped "
            f"ViewDefinition {sorted(viewdefs)} nor a declared dependency "
            f"{sorted(dependencies)}"
        )

    # Ship only the ViewDefinitions the SQL actually binds.  An unread one would
    # be dead weight a consumer still has to register.
    target_dir.mkdir(parents=True, exist_ok=True)
    sidecar = SIDECAR_BANNER.format(concept=concept) + sql
    library = _build_library(concept, version, sql, bindings)
    _assert_content_agrees(concept, library, sidecar, sql)

    (target_dir / f"{concept}.sql").write_text(sidecar, encoding="utf-8")
    for label, path in viewdefs.items():
        if label not in bindings:
            continue
        _write_json(
            target_dir / f"{VIEWDEFINITION_PREFIX}{label}.json",
            _load_viewdef(concept, path, label, version),
        )
    _write_json(target_dir / f"Library.{concept}.json", library)
    return strip


def _library_dependencies(library_path: Path) -> tuple[str, ...]:
    """The concepts whose *Library* this one reads, off its own relatedArtifact."""
    body = json.loads(library_path.read_text(encoding="utf-8"))
    prefix = LIBRARY_BASE + "/"
    return tuple(
        sorted(
            related["resource"][len(prefix) :]
            for related in body.get("relatedArtifact", [])
            if str(related.get("resource", "")).startswith(prefix)
        )
    )


def _withhold_unready(
    staging_dir: Path, staged: dict[str, Path], unpaired: dict[str, tuple[str, ...]]
) -> list[str]:
    """Drop concepts that still project a MIMIC identifier, and return the rest.

    The gate is ``unpaired == ()``: no MIMIC identifier survives into the
    artifact, so every column a consumer joins on is a FHIR resource key.  The
    test is deliberately *not* "something was stripped" -- a port written
    natively against keys, which never projects ``subject_id`` at all, strips
    nothing and is the cleanest case there is.

    A withheld concept is not lost: its verbatim SQL stays in its ``attempt_*``
    directory.  What changes is that ``artifacts/`` becomes exactly the set that
    is registerable, so the uploader needs no allowlist of its own.

    Readiness must also hold across Library dependencies, and that is checked
    rather than filtered.  Holding a concept back because its dependency is not
    ready would silently reorder work; failing loudly says which pair is out of
    step.  The asymmetry is the argument: if dependencies are always fixed first
    this never fires, and if one is ever missed it catches a Library that would
    otherwise register with a 200 and fail at query time with an error naming
    the wrong concept.
    """
    ready = [concept for concept in staged if concept not in unpaired]
    ready_set = set(ready)

    violations = []
    for concept in sorted(ready):
        for dep in _library_dependencies(staged[concept] / f"Library.{concept}.json"):
            if dep not in ready_set:
                reason = (
                    f"keeps {', '.join(unpaired[dep])}"
                    if dep in unpaired
                    else "is not finalized"
                )
                violations.append(f"{concept} reads Library '{dep}', which {reason}")
    if violations:
        raise StateError(
            "Concept(s) are ready but depend on a Library that is not, which would "
            "publish a Library the server accepts and then cannot run:\n  "
            + "\n  ".join(violations)
            + "\nRe-map the dependency first."
        )

    for concept, directory in staged.items():
        if concept in ready_set:
            continue
        shutil.rmtree(directory)
        # A category directory whose every concept was withheld would otherwise
        # survive as an empty directory in the export.
        parent = directory.parent
        while parent != staging_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return ready


@dataclass
class ExportReport:
    """Where the export landed, and what the identifier strip did concept by concept."""

    output_dir: Path
    count: int = 0
    #: ``{concept: (column, ...)}`` for identifiers removed.
    stripped: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: ``{concept: (column, ...)}`` for identifiers kept because the port ships
    #: no paired resource key -- and therefore the concepts *withheld* from the
    #: export.  Not a failure: a report on which ports have yet to be re-mapped
    #: onto keys, and the reason their tables still carry an integer a FHIR
    #: consumer cannot join on.
    unpaired: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def summary(self) -> list[str]:
        lines = [
            f"Exported {self.count} registerable mapping bundle(s) -> {self.output_dir}"
        ]
        for concept in sorted(self.stripped):
            lines.append(
                f"  stripped {concept}: {', '.join(self.stripped[concept])}"
            )
        if self.unpaired:
            lines.append(
                f"  withheld {len(self.unpaired)} concept(s): each keeps a MIMIC "
                f"identifier with no paired resource key, so it is unjoinable to FHIR "
                f"data until re-mapped:"
            )
            for concept in sorted(self.unpaired):
                lines.append(
                    f"    {concept}: {', '.join(self.unpaired[concept])}"
                )
        return lines


def export_mappings(
    *, artifact_root: Optional[Union[str, Path]] = None
) -> ExportReport:
    """Rebuild the canonical-layout artifact export from finalized attempts."""
    ctrl = ConversionController(artifact_root=artifact_root)
    output_dir = ctrl.artifact_root / DEFAULT_EXPORT_DIR
    bundles: list[tuple[str, Path, Path]] = []
    destinations: set[Path] = set()
    identifiers: dict[str, str] = {}

    for row in ctrl.status_report().concepts:
        if row["status"] not in ctrl.SATISFYING_STATUSES:
            continue

        concept = row["concept"]
        attempt_dir = ctrl.attempt_dir(concept)
        if attempt_dir is None:
            raise StateError(
                f"Finalized concept '{concept}' has no attempt directory "
                f"(status {row['status']}, attempt {row.get('attempt')})"
            )

        dag_path = PurePosixPath(ctrl.dag_raw["nodes"][concept]["path"])
        if dag_path.is_absolute() or ".." in dag_path.parts:
            raise StateError(
                f"Concept '{concept}' has unsafe DAG path {str(dag_path)!r}"
            )
        if dag_path.stem != concept:
            raise StateError(
                f"Concept '{concept}' has DAG path {str(dag_path)!r} whose stem "
                f"does not name the concept"
            )
        # measurement/chemistry.sql -> measurement/chemistry/
        destination = Path(*dag_path.parent.parts, concept)
        if destination in destinations:
            raise StateError(f"Duplicate mapping export path: {destination}")
        destinations.add(destination)

        # FHIR ids fold '_' to '-', so two concepts could collide where their
        # canonical URLs would not.
        ident = _fhir_id(concept)
        if ident in identifiers:
            raise StateError(
                f"Concepts '{identifiers[ident]}' and '{concept}' both reduce to "
                f"FHIR id {ident!r}"
            )
        identifiers[ident] = concept

        bundles.append((concept, Path(attempt_dir), destination))

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() and not output_dir.is_dir():
        raise StateError(f"Mapping export path is not a directory: {output_dir}")

    report = ExportReport(output_dir=output_dir)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=".artifacts-staging-", dir=output_dir.parent)
    )
    backup_dir: Optional[Path] = None
    try:
        staged: dict[str, Path] = {}
        for concept, attempt_dir, destination in bundles:
            target = staging_dir / destination
            strip = _stage_concept(ctrl, concept, attempt_dir, target)
            staged[concept] = target
            if strip.dropped:
                report.stripped[concept] = strip.dropped
            if strip.unpaired:
                report.unpaired[concept] = strip.unpaired

        # Everything is staged before anything is judged, because readiness is a
        # property of the whole set: a concept can only be cleared once the
        # Libraries it reads have been.
        report.count = len(_withhold_unready(staging_dir, staged, report.unpaired))

        if output_dir.exists():
            backup_dir = output_dir.with_name(
                f".{output_dir.name}.backup-{uuid.uuid4().hex}"
            )
            os.replace(output_dir, backup_dir)

        try:
            os.replace(staging_dir, output_dir)
        except Exception:
            if backup_dir is not None:
                os.replace(backup_dir, output_dir)
                backup_dir = None
            raise

        if backup_dir is not None:
            shutil.rmtree(backup_dir)
            backup_dir = None
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    return report
