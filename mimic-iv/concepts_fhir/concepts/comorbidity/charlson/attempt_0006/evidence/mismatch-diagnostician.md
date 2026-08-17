## Diagnosis — `charlson` attempt 0006

Root cause: the 61 conflicts are inherited upstream transformation loss from the completed `age` dependency, not a fixable Charlson SQL bug.

The canonical age formula is `mimic-iv/concepts/demographics/age.sql:30`, using the original `anchor_age`/`anchor_year` pair. Upstream MIMIC-on-FHIR instead computes `Patient.birthDate` in `mimic-fhir/sql/fhir_patient.sql:15` and writes it at line 108 from `MIN(transfers.intime) - anchor_age`. The FHIR representation carries neither `anchor_year` nor `anchor_age` as separate exact fields or extensions, so the oracle age is unrecoverable by any defensible FHIR query. Resource IDs remain opaque and were not used semantically.

Count reconciliation:
- age dependency: 460 age conflicts, plus 44 separate `admittime` DST conflicts;
- Charlson: 61 `age_score` conflicts, exactly the threshold crossings among the age conflicts, and the same 61 `charlson_comorbidity_index` conflicts because the score adds `age_score` once;
- 399 remaining age differences stay within the same threshold band;
- all 17 comorbidity flags match, with zero only-oracle, only-candidate, and null-only rows.

The reopened fix is correct: `com` groups by `e.encounter_key` at `concept.sql:124-128`; `ag` projects `src_age.encounter_key` at `:130-141`; and both joins use opaque equality on `e.encounter_key` at `:176-183`. All 431,231 admissions are preserved. No carryover stage should be invalidated and no Charlson fix is recommended.

Classification: upstream transformation loss, cited at `mimic-fhir/sql/fhir_patient.sql:15,108`. Terminal acceptance/blocking remains exclusively for the equivalence judge.
