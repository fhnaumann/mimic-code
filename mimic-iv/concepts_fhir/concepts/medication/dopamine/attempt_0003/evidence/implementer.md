# Implementer evidence

- Concept: `dopamine`; attempt: `0003`.
- Read the canonical source SQL, dopamine source-analysis and FHIR-prober
  carryover, the curated MIMIC notes, relevant medication fragments, the
  oracle manifest, and the pathling/FHIR mapping conventions.
- Created `ViewDefinition.medication_administration.json`,
  `ViewDefinition.encounter_icu.json`, `concept.sql`, and
  `unrepresentable.json` in this attempt.
- Checked exact ICU medication system/code `221662`, ICU Encounter identifier
  recovery for `stay_id`, typed NULL `linkorderid`, both effective-time choice
  variants, FLOAT quantity casts, bare `TRY_CAST(... AS TIMESTAMP_NTZ)`, and
  manifest resource-key outputs `patient_key` and `icu_encounter_key`.
- `uv run mimic_utils lint-sql dopamine` passed; all JSON artifacts parsed.
- No new dataset-wide quirk was reported; no notes fragment append was needed.
