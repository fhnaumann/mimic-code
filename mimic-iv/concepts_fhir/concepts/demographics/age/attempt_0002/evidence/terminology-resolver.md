# Terminology Resolution Evidence: `age` (attempt_0002)

**Stage:** terminology-resolver (RERUN per resume plan)
**Date:** 2026-08-07
**Concept:** demographics/age

## Conclusion

**Not applicable.** The `age` concept is a purely numeric computation with no
coded fields. `mimic-iv/concepts/demographics/age.sql` joins
`mimiciv_hosp.admissions` to `mimiciv_hosp.patients` on `subject_id` and
computes `age = anchor_age + DATETIME_DIFF(admittime, DATETIME(anchor_year,1,1,...), YEAR)`.
It references no `itemid`, `icd_code`, `loinc_code`, or any code system.

## What was read

- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` — governing entry:
  "Code systems are mostly proprietary and flat — except `Condition.code`",
  which reinforces that terminology work matters only where real standard
  codes exist; `age` has none. **No MIMIC_NOTES.md entry added or updated.**
- `mimic-iv/concepts/demographics/age.sql` — confirms no coded fields.
- Carryover `source-analyst.md` (§8) and `fhir-prober.md` (§6) — both
  independently concluded "no terminology resolution is needed".

## Taxonomy operations

None. No Velonto ConceptMap consulted, no `$translate`/`$expand` issued, no
ConceptMap/ValueSet snapshot (`.fhir.json`) applies. No preflight hash because
no terminology resource was fetched.

## Artifacts

- Carryover file written: `mimic-iv/concepts_fhir/carryover/age/terminology-resolver.md`
- `carryover-record` succeeded (ledger now lists `terminology-resolver`,
  written_at_attempt 2).
- Unresolved codes: none. Unmatched codes: none.

## MIMIC_NOTES.md entries consulted or written

Consulted: "Code systems are mostly proprietary and flat — except
`Condition.code`". Written: none (the "not applicable" finding is
concept-specific and belongs in carryover, not the shared notes).
