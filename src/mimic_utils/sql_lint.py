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

_REMEDY = (
    "Remedy for every finding above: TRY_CAST(col AS TIMESTAMP_NTZ), with nothing\n"
    "  wrapped around it -- no parser, no fallback, no pinned format. See\n"
    "  MIMIC_NOTES.md 'FHIR datetimes carry an offset' and\n"
    "  .opencode/skills/pathling-sql/SKILL.md 'Datetimes'."
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
