"""Re-run a finished port against rebuilt data, without re-authoring its SQL.

``reopen`` exists for one case: a human found a defect in the SQL a finished
port shipped.  Everything downstream is built around that reading --
``resume_plan`` prints the reopen reason as "the previous run's SQL was
defective", and the orchestrator skill instructs the implementer to fix the
named construction.  For a defect reopen that is right.

It is the wrong shape for the other case.  When an **upstream** defect is fixed
and MIMIC-on-FHIR is rebuilt, the port's SQL is not what changed -- the data
under it is.  Sending that through the defect route costs an implementer run per
concept to re-author a file that must come out identical, and worse, it *may not*
come out identical: the implementer authors fresh SQL each attempt with no memory
of the last one (the reason ``sql_lint`` exists at all), so the query being
re-measured is not necessarily the query that earned the verdict.  For a claim of
the form "the same port reproduces more rows once upstream is fixed", holding the
query byte-identical is the experiment, not an optimisation.

So: ``replay`` reopens the concept, opens the next attempt, and carries the
previous attempt's ``concept.sql``, ViewDefinitions and unrepresentability
declaration forward byte-identical, recording their hashes in
``replay_provenance.json``.  The analysis stages and the implementer are then not
skipped as an economy -- there is nothing for them to do.  The loop re-enters at
the demo shape gate, which ``resume_plan`` already routes to whenever an attempt
has SQL and no demo verdict.

What it refuses is the load-bearing part.  A fix that *adds a served element* is
not replayable: the port has to select the new element, and a byte-identical
replay will emit the same NULLs, satisfy its own unrepresentability declaration
(the column really is 100% NULL), sail through as ``gap_shaped`` and be accepted
a second time -- the divergence laundered rather than repaired.  ``gcs`` and
``first_day_gcs`` are the worked examples: both declare ``gcs_unable``
unrepresentable "because the No Response-ETT discriminator is discarded", and
upstream now serves exactly that discriminator.  So the registry below records
per fixed defect whether it invalidates a mapping, and a concept whose recorded
verdict or declaration cites a mapping-invalidating defect is refused and sent
down the ordinary ``reopen`` + ``carryover-invalidate --stage fhir-prober``
route.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .conversion_state import (
    REOPEN_ONLY_STATUSES,
    ConversionController,
    StateError,
)
from .sql_lint import format_findings, lint_sql_file

__all__ = [
    "FIXED_UPSTREAM_DEFECTS",
    "PROVENANCE_NAME",
    "CARRIED_GLOBS",
    "FixedDefect",
    "ReplayCheck",
    "ReplayResult",
    "check_replay",
    "read_provenance",
    "replay",
]

PROVENANCE_NAME = "replay_provenance.json"
SQL_NAME = "concept.sql"
UNREPRESENTABLE_NAME = "unrepresentable.json"

#: What a replay carries into the new attempt: the port itself, and nothing it
#: earned.  Results (``shape.demo.json``, ``comparison.full.json``,
#: ``hpc_job.json``, ``run_meta.full.json``, ``candidate.*.parquet``,
#: ``evidence/``) are deliberately absent -- the whole point is to earn them
#: again against the rebuilt data.
CARRIED_GLOBS: Tuple[str, ...] = (SQL_NAME, "ViewDefinition*.json", UNREPRESENTABLE_NAME)

#: The reason prefix, so a reader of ``reopen_history`` -- and ``resume_plan``,
#: which prints it -- can tell a data-rebuild reopen from a defect reopen without
#: parsing prose.
REASON_PREFIX = "[replay:data_rebuild]"


# ---------------------------------------------------------------------------
# The registry of fixed upstream defects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixedDefect:
    """One upstream defect that has been fixed, and what the fix implies here.

    ``invalidates_mapping`` is the only field that decides anything.  ``False``
    means the fix corrects a *value* at a path the port already selects, so the
    same SQL now returns better rows -- replayable.  ``True`` means the fix
    *adds* something to the served data, so a port written against its absence
    is now incomplete and must be re-authored.
    """

    id: str
    fixed_by: str
    summary: str
    invalidates_mapping: bool
    #: Matches the way this defect gets cited in a recorded verdict, a judge
    #: justification, or an ``unrepresentable.json`` reason.
    citation: re.Pattern
    #: For a mapping-invalidating fix: what is served now, named so the refusal
    #: can say where to look instead of only saying no.
    now_served: Optional[str] = None

    def cited_in(self, text: Optional[str]) -> bool:
        return bool(text) and bool(self.citation.search(text))


FIXED_UPSTREAM_DEFECTS: Tuple[FixedDefect, ...] = (
    FixedDefect(
        id="dst-timestamptz-wall-clock",
        fixed_by="mimic-fhir ade10fb (upstream #124), 2026-08-21",
        summary=(
            "The ETL ran under a DST-observing zone, so casting naive MIMIC wall "
            "times through TIMESTAMPTZ normalised spring-forward gap times "
            "forward an hour irreversibly. The FHIR tables are now generated "
            "under UTC, which has no DST in any year, so the cast is an "
            "identity on the wall clock."
        ),
        invalidates_mapping=False,
        citation=re.compile(
            r"timestamptz|dst|spring[- ]forward|America/New_York|"
            r"fhir_encounter\.sql:65|fhir_observation_chartevents\.sql:9,\s*67",
            re.I,
        ),
    ),
    FixedDefect(
        id="patient-birthdate-anchor",
        fixed_by="mimic-fhir 3048c88 (upstream #126, #117), 2026-08-21",
        summary=(
            "Patient.birthDate was synthesised as MIN(transfers.intime) minus "
            "anchor_age, which is not the anchor pair the canonical age "
            "definition uses, and an INNER JOIN on transfers left patients with "
            "no transfer row without a birthDate at all. It is now "
            "MAKE_DATE(anchor_year, 1, 1) minus anchor_age, on the patients row "
            "itself. Same element, same path, corrected value and better "
            "coverage."
        ),
        invalidates_mapping=False,
        citation=re.compile(
            r"fhir_patient\.sql|Patient\.birthDate|MIN\(transfers\.intime\)|"
            r"anchor_year|anchor_age|anchor pair",
            re.I,
        ),
    ),
    FixedDefect(
        id="chartevents-value-text-dropped",
        fixed_by="mimic-fhir e7c326b (upstream #125), 2026-08-21",
        summary=(
            "The chartevents ETL discarded chartevents.value whenever valuenum "
            "was set, so a numeric observation carrying a distinct textual "
            "meaning was served as a bare number -- 'No Response' and "
            "'No Response-ETT' both as Quantity 1. The source text is now "
            "carried in a component, coded with the same d-items coding as "
            "Observation.code, emitted wherever the text is not the number "
            "restated."
        ),
        invalidates_mapping=True,
        now_served="Observation.component.where(code.coding.code = <itemid>).valueString",
        citation=re.compile(
            r"fhir_observation_chartevents\.sql:69-80|"
            r"discards source chartevents\.value|chartevents\.value\b|value_text|"
            r"valueString/value\.ofType\(string\)|Observation\.component|"
            r"No Response|collapses .*to Quantity|valuenum is set",
            re.I,
        ),
    ),
)


def _defects_cited(text: Optional[str]) -> List[FixedDefect]:
    return [d for d in FIXED_UPSTREAM_DEFECTS if d.cited_in(text)]


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------


@dataclass
class ReplayCheck:
    """Whether *concept* can be replayed, and what a replay would carry."""

    concept: str
    status: str
    attempt: int
    source_attempt_dir: Optional[Path] = None
    files: List[Path] = field(default_factory=list)
    refusals: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cleared: List[str] = field(default_factory=list)

    @property
    def replayable(self) -> bool:
        return not self.refusals

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "status": self.status,
            "attempt": self.attempt,
            "source_attempt_dir": str(self.source_attempt_dir) if self.source_attempt_dir else None,
            "files": [f.name for f in self.files],
            "refusals": list(self.refusals),
            "warnings": list(self.warnings),
            "cleared": list(self.cleared),
            "replayable": self.replayable,
        }

    def format(self) -> str:
        lines = [
            f"Replay check for '{self.concept}'",
            f"  status:        {self.status} (attempt {self.attempt})",
            f"  source:        {self.source_attempt_dir or '-'}",
            f"  would carry:   {', '.join(f.name for f in self.files) or '-'}",
        ]
        if self.cleared:
            lines.append(f"  fix applies:   {', '.join(self.cleared)}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        for r in self.refusals:
            lines.append(f"  REFUSED: {r}")
        if self.replayable:
            lines.append("  verdict:       replayable")
        return "\n".join(lines)


def _carried_files(attempt_dir: Path) -> List[Path]:
    out: List[Path] = []
    for pattern in CARRIED_GLOBS:
        if any(ch in pattern for ch in "*?["):
            out.extend(sorted(attempt_dir.glob(pattern)))
        elif (attempt_dir / pattern).is_file():
            out.append(attempt_dir / pattern)
    return out


def check_replay(
    concept: str,
    *,
    artifact_root: Optional[Union[str, Path]] = None,
    controller: Optional[ConversionController] = None,
) -> ReplayCheck:
    """Decide whether *concept* is replayable.  Reads only.

    Every refusal here is one ``reopen`` would not have caught, and it is
    checked *before* the reopen for the same reason ``ConversionController.reopen``
    pre-flights ``start``: a reopen that half-applies leaves a cleared verdict on
    a concept nothing will re-run.
    """
    ctrl = controller or ConversionController(artifact_root=artifact_root)
    state = ctrl._read_state(concept)  # noqa: SLF001 -- same package
    if state is None:
        raise StateError(
            f"Concept '{concept}' has not been initialised; there is no finished "
            f"attempt to replay"
        )

    check = ReplayCheck(concept=concept, status=state.status, attempt=state.attempt)

    # --- is there a recorded verdict to replay at all? ---
    if state.status == "BLOCKED_REPRESENTATION":
        check.refusals.append(
            "the concept is BLOCKED_REPRESENTATION. A block says the served data "
            "cannot carry what the concept needs, so what a rebuild changes is "
            "exactly the premise of the block -- that is a mapping question, not "
            "a rerun. Use `reopen --by human --reason \"...\"` naming what is "
            "served now, and `carryover-invalidate --stage fhir-prober`."
        )
        return check
    if state.status not in REOPEN_ONLY_STATUSES:
        check.refusals.append(
            f"status is {state.status}, not a recorded verdict. replay sets aside "
            f"a finished result; for anything else use `resume` or `retry`."
        )
        return check

    # --- is there a port on disk to carry? ---
    src = ctrl._attempt_dir(concept, state.attempt)  # noqa: SLF001 -- same package
    if not src.exists():
        check.refusals.append(f"attempt directory {src} does not exist")
        return check
    check.source_attempt_dir = src
    check.files = _carried_files(src)
    names = {f.name for f in check.files}
    if SQL_NAME not in names:
        check.refusals.append(
            f"{src.name}/ has no {SQL_NAME}: there is no query to carry forward"
        )
    if not any(n.startswith("ViewDefinition") for n in names):
        check.refusals.append(
            f"{src.name}/ has no ViewDefinition*.json: the SQL selects from views "
            f"that would not exist in the new attempt"
        )

    next_dir = ctrl._attempt_dir(concept, state.attempt + 1)  # noqa: SLF001
    if next_dir.exists():
        check.refusals.append(
            f"{next_dir.name}/ already exists -- either a goal is already running "
            f"against it, or a previous reopen half-applied. Check `status`; do "
            f"not delete it."
        )

    missing = ctrl._missing_dependencies(concept)  # noqa: SLF001 -- same package
    if missing:
        check.refusals.append(
            f"unmet dependencies {sorted(missing)}. A replay wave runs in DAG "
            f"order: a dependency that is itself mid-replay must reach a "
            f"completed status first, because both runners preprocess its "
            f"attempt output."
        )

    # --- would the carried SQL be refused at validate-demo? ---
    sql_path = src / SQL_NAME
    if sql_path.is_file():
        findings = lint_sql_file(sql_path)
        if findings:
            check.refusals.append(
                "the SQL being carried forward does not pass the lint that "
                "`validate-demo` runs, so the replayed attempt would be refused "
                "after the reopen was already spent:\n"
                + format_findings(concept, sql_path, findings)
            )

    # --- does a fix invalidate this port's mapping? ---
    verdict_text = " ".join(
        filter(None, [state.divergence_justification, state.error_message])
    )
    declarations: Dict[str, str] = {}
    decl_path = src / UNREPRESENTABLE_NAME
    if decl_path.is_file():
        try:
            loaded = json.loads(decl_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                declarations = {str(k): str(v) for k, v in loaded.items()}
        except (OSError, json.JSONDecodeError):
            check.warnings.append(f"{UNREPRESENTABLE_NAME} is unreadable; declarations unchecked")

    for defect in FIXED_UPSTREAM_DEFECTS:
        in_verdict = defect.cited_in(verdict_text)
        cited_columns = [c for c, why in declarations.items() if defect.cited_in(why)]
        if not in_verdict and not cited_columns:
            continue
        if defect.invalidates_mapping:
            where = (
                f"declares {', '.join(sorted(cited_columns))} unrepresentable citing it"
                if cited_columns
                else "the recorded verdict cites it"
            )
            check.refusals.append(
                f"{defect.id} is fixed ({defect.fixed_by}) and the fix ADDS a "
                f"served element, but this port {where}. Replaying byte-identical "
                f"SQL emits the same NULLs, satisfies its own declaration -- the "
                f"column really is 100% NULL -- and is accepted a second time "
                f"without the new element ever being read.\n"
                f"    now served: {defect.now_served}\n"
                f"    route:      reopen --by human --reason \"<name the new path>\" "
                f"then carryover-invalidate --stage fhir-prober"
            )
        else:
            check.cleared.append(defect.id)
            if cited_columns:
                check.warnings.append(
                    f"{UNREPRESENTABLE_NAME} declares "
                    f"{', '.join(sorted(cited_columns))} unrepresentable citing "
                    f"{defect.id}, which is fixed. Confirm the declaration's "
                    f"CONCLUSION still holds and rewrite its stated mechanism in "
                    f"the new attempt -- a carried declaration whose reasoning "
                    f"names a repaired defect is evidence nobody re-read it. "
                    f"(For anchor_age/anchor_year it does still hold: birthDate "
                    f"remains a single date, so the pair stays collapsed.)"
                )

    unfixed = _describe_unfixed(verdict_text, declarations)
    if unfixed:
        check.warnings.append(
            "part of this concept's divergence is NOT fixed upstream ("
            + "; ".join(unfixed)
            + "), so expect the replay to return `review` again on that part "
            "rather than `match`. That is the correct outcome, not a regression."
        )

    return check


#: Defects that are measured, documented and still open upstream. Named so a
#: replay can predict which concepts will legitimately come back `review`
#: instead of `match`, and so nobody reads that as the rerun having failed.
_UNFIXED = (
    (
        re.compile(r"linkorderid|\borderid\b", re.I),
        "inputevents.orderid/linkorderid are still only inside the opaque "
        "MedicationAdministration UUID (fhir_medication_administration_icu.sql:20)",
    ),
    (
        re.compile(r"\bpoe\b|poe_detail", re.I),
        "the hospital poe/poe_detail branch is still absent from the served data",
    ),
    (
        re.compile(r"inputevents\.starttime|fhir_medication_administration_icu\.sql:61-69", re.I),
        "inputevents.starttime is still dropped for non-rate administrations "
        "(fhir_medication_administration_icu.sql:61-69)",
    ),
)


def _describe_unfixed(verdict_text: str, declarations: Dict[str, str]) -> List[str]:
    haystack = " ".join([verdict_text, *declarations.values()])
    return [note for pattern, note in _UNFIXED if pattern.search(haystack)]


# ---------------------------------------------------------------------------
# Doing it
# ---------------------------------------------------------------------------


@dataclass
class ReplayResult:
    concept: str
    superseded_status: str
    attempt: int
    source_attempt_dir: Path
    attempt_dir: Path
    carried: List[str]
    cleared: List[str]
    warnings: List[str]

    def format(self) -> str:
        lines = [
            f"Replayed '{self.concept}' from {self.superseded_status} "
            f"(attempt {self.attempt})",
            f"  source:      {self.source_attempt_dir}",
            f"  new attempt: {self.attempt_dir}",
            f"  carried:     {', '.join(self.carried)} (byte-identical)",
        ]
        if self.cleared:
            lines.append(f"  fix applies: {', '.join(self.cleared)}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        lines += [
            "",
            "  The SQL was NOT re-authored and must NOT be. Do not spawn the "
            "source-analyst,",
            "  the fhir-prober or the concept-implementer: this attempt already "
            "holds the port",
            "  that earned the superseded verdict, and holding it byte-identical "
            "is what makes",
            "  the rerun a measurement of the upstream fix rather than of a new "
            "query.",
            "",
            "  Re-enter at Phase 4: validate-demo -> run-demo -> validate-full -> "
            "hpc-launch -> hpc-poll.",
        ]
        return "\n".join(lines)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def replay(
    concept: str,
    *,
    reason: str,
    decided_by: str = "human",
    artifact_root: Optional[Union[str, Path]] = None,
    controller: Optional[ConversionController] = None,
) -> ReplayResult:
    """Reopen *concept* and carry its port forward unchanged.

    ``decided_by`` must be ``"human"`` for the same reason ``reopen`` requires
    it: this sets aside a verdict that is recorded, cited and counted in the
    results table.  A replay is a cheaper reopen, not a weaker one.
    """
    ctrl = controller or ConversionController(artifact_root=artifact_root)
    check = check_replay(concept, controller=ctrl)
    if not check.replayable:
        raise StateError(
            f"Cannot replay '{concept}':\n  - " + "\n  - ".join(check.refusals)
        )
    if not (reason or "").strip():
        raise StateError(
            "replay requires --reason: which upstream fix is being measured, and "
            "which rebuilt warehouse. The superseded verdict was recorded with a "
            "cited justification; replacing it with nothing makes the results "
            "table unreadable at the point a reader would want to check."
        )

    src = check.source_attempt_dir
    assert src is not None  # replayable implies a source attempt
    superseded = check.status
    source_name = src.name

    state = ctrl.reopen(
        concept,
        reason=f"{REASON_PREFIX} {reason.strip()}",
        decided_by=decided_by,
    )
    dst = ctrl.attempt_dir(concept)

    carried: List[Dict[str, str]] = []
    for path in check.files:
        target = dst / path.name
        shutil.copy2(path, target)
        digest = _sha256(path)
        if _sha256(target) != digest:
            raise StateError(
                f"Copy of {path.name} into {dst.name}/ does not hash to the "
                f"source. The replay is void: the point is byte-identity."
            )
        carried.append({"name": path.name, "sha256": digest})

    provenance = {
        "kind": "data_rebuild",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "concept": concept,
        "source_attempt": source_name,
        "superseded_status": superseded,
        "reason": reason.strip(),
        "carried": carried,
        "fixes_measured": [
            {
                "id": d.id,
                "fixed_by": d.fixed_by,
                "summary": d.summary,
            }
            for d in FIXED_UPSTREAM_DEFECTS
            if d.id in check.cleared
        ],
        "warnings": list(check.warnings),
        "authored_by": "mimic_utils replay",
        "note": (
            "The SQL and ViewDefinitions in this attempt were NOT authored for "
            "it. They are the previous attempt's, carried forward byte-identical "
            "so that the only thing that changed between the superseded verdict "
            "and this one is the served data. No implementer ran, and none "
            "should: re-authoring would make this a comparison of two queries "
            "instead of a measurement of the upstream fix."
        ),
    }
    (dst / PROVENANCE_NAME).write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    return ReplayResult(
        concept=concept,
        superseded_status=superseded,
        attempt=state.attempt,
        source_attempt_dir=src,
        attempt_dir=dst,
        carried=[c["name"] for c in carried],
        cleared=list(check.cleared),
        warnings=list(check.warnings),
    )


def read_provenance(attempt_dir: Optional[Union[str, Path]]) -> Optional[Dict[str, Any]]:
    """Return the attempt's replay provenance, or ``None``.

    ``resume_plan`` calls this to decide which instruction block to print: a
    defect reopen tells the implementer what to fix, a replay tells it not to
    run.  Treated as absent when unreadable -- the caller is choosing prose, and
    "cannot read it" and "not there" lead to the same place.
    """
    if attempt_dir is None:
        return None
    path = Path(attempt_dir) / PROVENANCE_NAME
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def check_many(
    concepts: Sequence[str],
    *,
    artifact_root: Optional[Union[str, Path]] = None,
) -> Dict[str, ReplayCheck]:
    """``check_replay`` over a wave, sharing one controller."""
    ctrl = ConversionController(artifact_root=artifact_root)
    out: Dict[str, ReplayCheck] = {}
    for concept in concepts:
        try:
            out[concept] = check_replay(concept, controller=ctrl)
        except StateError as exc:
            out[concept] = ReplayCheck(
                concept=concept, status="?", attempt=0, refusals=[str(exc)]
            )
    return out
