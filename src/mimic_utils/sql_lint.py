"""Deterministic checks on an attempt's ``concept.sql`` before it is frozen.

This exists because documentation turned out not to be a control.

The rule "FHIR datetimes carry an offset -- cast to TIMESTAMP_NTZ, never to
TIMESTAMP" is stated in ``MIMIC_NOTES.md``, and ``pathling-sql/SKILL.md`` prints
both wrong constructions as labelled ``-- WRONG`` blocks next to the right one.
The implementer loads that skill. It wrote the forbidden form anyway, in 29 of
56 ``concept.sql`` files across 19 concepts -- and ``gcs`` reintroduced it at
attempt_0003 after attempt_0002 had removed it, then shipped as COMPLETED.

So the check is mechanical and it gates the transition that freezes the
artifacts. An agent cannot reason its way past it, which is the point: every
one of those 29 files was authored by something that had the rule in context.

The second class of rule is newer and has a different cause. Where the datetime
rules catch an implementer that ignored a documented instruction, the resource-id
rules catch one that *succeeded* -- five concepts reached `COMPLETED` (exact
match) by recomputing the ETL's `Observation.id` UUIDv5 to detect and undo a
one-hour timestamp shift, and `code_status` did it with nine hardcoded UUID
literals read straight off its own first divergence report. Those verdicts are
real, and the technique that earned them is not a port: it inverts an
undocumented implementation detail of one ETL version, and it converts "the
served data does not carry this" into "the served data carries this, encoded in
the primary key".

That is the failure mode worth naming, because it is invisible in the metric it
optimises. An agent that cannot reach agreement has two honest moves -- fix the
mapping, or declare the gap and let the row diverge -- and a third dishonest one
that scores better than either. The gate exists to remove the third.

Scope is deliberately narrow. These rules encode *known* defect classes only --
the ones a full-data divergence already taught us. Discovering a new class is
still the mismatch-diagnostician's job; when it finds one, add a rule here so
the next attempt cannot repeat it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

#: Any use of the offset-aware parser. There is no legitimate one: it parses the
#: offset and re-renders the instant in ``spark.sql.session.timeZone``, scoring
#: 0/275 against the oracle at Australia/Sydney and UTC and 275/275 only at
#: America/New_York. Demo runs on a laptop and the full leg runs on Petrichor,
#: so a port carrying it produces two different answers.
#:
#: Matched as a bare token rather than as the nesting from the skill's example:
#: gcs attempt_0003 wrapped an extra REPLACE inside the REGEXP_REPLACE, which a
#: pattern keyed on the example's shape would have sailed past.
_RE_TO_TIMESTAMP = re.compile(r"\b(?:try_)?to_timestamp\s*\(", re.IGNORECASE)

#: ``CAST(x AS TIMESTAMP)`` -- the cast the notes entry is named after. Does not
#: match ``TIMESTAMP_NTZ`` because ``\b`` will not split ``TIMESTAMP_NTZ``.
_RE_BARE_TIMESTAMP = re.compile(r"\bAS\s+TIMESTAMP\b\s*\)", re.IGNORECASE)

#: A literal resource UUID in the SQL. `code_status` attempt_0002 shipped nine
#: of them -- `WHEN 'Observation/1e2075cb-...' THEN TIMESTAMP '2151-10-03 02:16'`
#: -- each mapping one resource id to the oracle value that resource should have
#: had, read straight off attempt_0001's divergence report. That is a query
#: fitted to its own evaluation: inert on the demo leg (those ids do not exist
#: there), pinned to one materialization, and not a mapping of anything.
#:
#: Matched as a bare UUID anywhere in a string literal rather than keyed on the
#: `Observation/` prefix, because the prefix is the incidental part -- the
#: defect is pinning a row by identity at all.
_RE_HARDCODED_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

#: Reconstructing a resource id rather than reading one. Five concepts recompute
#: the ETL's UUIDv5 -- `SHA1(CONCAT(UNHEX('<namespace>'), ENCODE(name,'UTF-8')))`
#: reassembled into 8-4-4-4-12 -- to detect whether an id was derived from a
#: timestamp one hour earlier, and subtract the hour when it was.
#:
#: This inverts the ETL's id-generation function. It is not a FHIR mapping: no
#: consumer of MIMIC-on-FHIR could rely on it, it depends on an undocumented
#: implementation detail of one ETL version, and it converts "this information
#: is absent" into "this information is encoded in the primary key". `gcs` shows
#: where it leads -- it brute-forces a 16-entry label vocabulary through SHA1 to
#: recover a categorical value the ETL discarded.
#:
#: Two independent signals, either of which is enough: a hex namespace constant
#: fed to UNHEX (the UUIDv5 namespace), and a hash function applied to anything.
#: A concept port has no legitimate use for either.
_RE_UUID_NAMESPACE = re.compile(r"\bUNHEX\s*\(\s*'[0-9a-f]{32}'", re.IGNORECASE)
_RE_HASH_CALL = re.compile(r"\b(?:sha1|sha2|md5|hash|xxhash64|crc32)\s*\(", re.IGNORECASE)

_REMEDY = (
    "Remedy for datetime-parser / bare-timestamp-cast: TRY_CAST(col AS TIMESTAMP_NTZ),\n"
    "  with nothing wrapped around it -- no parser, no fallback, no pinned format.\n"
    "  See MIMIC_NOTES.md 'FHIR datetimes carry an offset' and\n"
    "  .opencode/skills/pathling-sql/SKILL.md 'Datetimes'.\n"
    "  Remedy for hardcoded-resource-id / resource-id-inversion: there is none that\n"
    "  keeps the construction. A value the served data does not carry is a\n"
    "  divergence, not a puzzle -- emit the typed NULL for an ancillary column,\n"
    "  or let the row diverge for the judge. If the lost input changes the core\n"
    "  derivation, the whole concept is a representation block, not a partial\n"
    "  port. See LOOP_CONTRACT.md 'Essential loss blocks the concept'."
)


@dataclass
class Finding:
    """One rule violation, located precisely enough to fix without searching."""

    rule: str
    line: int
    text: str
    message: str

    def format(self) -> str:
        return f"  line {self.line:>4}  [{self.rule}]  {self.text.strip()[:80]}"


def _strip_line_comments(line: str) -> str:
    """Blank out a trailing ``--`` comment, ignoring ``--`` inside string literals.

    A commented-out violation is not a violation, and failing an attempt for one
    would be a false rejection that blocks the loop -- the expensive direction of
    error for a gate that cannot be argued with.
    """
    in_single = in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif (
            char == "-"
            and not in_single
            and not in_double
            and line[index + 1 : index + 2] == "-"
        ):
            return line[:index]
    return line


def lint_sql_text(text: str) -> list[Finding]:
    """Return every violation in *text*, in line order."""
    findings: list[Finding] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_line_comments(raw)
        if _RE_TO_TIMESTAMP.search(line):
            findings.append(
                Finding(
                    rule="datetime-parser",
                    line=number,
                    text=raw,
                    message=(
                        "to_timestamp re-renders the instant in the session time zone, "
                        "so demo and full data disagree; a pinned format silently NULLs "
                        "every shape it misses"
                    ),
                )
            )
        if _RE_BARE_TIMESTAMP.search(line):
            findings.append(
                Finding(
                    rule="bare-timestamp-cast",
                    line=number,
                    text=raw,
                    message="CAST(... AS TIMESTAMP) drops to the session zone",
                )
            )
        if _RE_HARDCODED_UUID.search(line):
            findings.append(
                Finding(
                    rule="hardcoded-resource-id",
                    line=number,
                    text=raw,
                    message=(
                        "a literal resource UUID pins one row by identity: it is fitted "
                        "to one comparison run, inert on the demo leg, and pinned to one "
                        "materialization"
                    ),
                )
            )
        if _RE_UUID_NAMESPACE.search(line) or _RE_HASH_CALL.search(line):
            findings.append(
                Finding(
                    rule="resource-id-inversion",
                    line=number,
                    text=raw,
                    message=(
                        "recomputing a resource id inverts the ETL's id-generation "
                        "function; that is an undocumented implementation detail, not a "
                        "FHIR mapping, and no consumer of the IG could reproduce it"
                    ),
                )
            )
    return findings


def lint_sql_file(path: str | Path) -> list[Finding]:
    target = Path(path)
    if not target.is_file():
        return []
    return lint_sql_text(target.read_text(encoding="utf-8", errors="replace"))


def format_findings(concept: str, path: str | Path, findings: Iterable[Finding]) -> str:
    findings = list(findings)
    if not findings:
        return f"sql-lint: {concept}: clean ({path})"
    lines = [f"sql-lint: {concept}: {len(findings)} violation(s) in {path}"]
    lines.extend(finding.format() for finding in findings)
    for rule in dict.fromkeys(finding.rule for finding in findings):
        message = next(f.message for f in findings if f.rule == rule)
        lines.append(f"  [{rule}] {message}")
    lines.append(f"  {_REMEDY}")
    return "\n".join(lines)


def lint_attempt(
    concept: str, *, artifact_root: Optional[str | Path] = None
) -> tuple[Optional[Path], list[Finding]]:
    """Lint the concept's current attempt ``concept.sql``.

    Returns ``(path, findings)``. ``path`` is ``None`` when there is no attempt
    directory or no SQL in it yet -- which is not a violation, just nothing to
    check.
    """
    from mimic_utils.conversion_state import ConversionController

    controller = ConversionController(artifact_root=artifact_root)
    attempt_dir = controller.attempt_dir(concept)
    if attempt_dir is None:
        return None, []
    sql_path = attempt_dir / "concept.sql"
    if not sql_path.is_file():
        return None, []
    return sql_path, lint_sql_file(sql_path)


__all__ = [
    "Finding",
    "format_findings",
    "lint_attempt",
    "lint_sql_file",
    "lint_sql_text",
]
