# Concept implementer evidence

- Concept: `phenylephrine`; attempt: `0002`.
- Read the authoritative loop contract, curated MIMIC notes, phenylephrine source analysis and FHIR probe carryover, canonical SQL, and ICU ETL context.
- Created `ViewDefinition.medication_administration.json`, `ViewDefinition.encounter_icu.json`, `concept.sql`, and `unrepresentable.json` in this immutable attempt.
- The implementation filters exact ICU MedicationAdministration system/code `221749`, joins opaque Encounter keys to recover `stay_id`, projects both effective variants, uses `TIMESTAMP_NTZ`, emits typed NULL `linkorderid`, and emits row-level typed NULL `vaso_rate` only for `rate_unit = 'mcg/min'` because `patientweight` is not represented.
- JSON parsing and `uv run mimic_utils lint-sql phenylephrine` passed. No existing attempt artifact was edited and no commit was made.
- No new dataset-wide quirk was established; the phenylephrine notes fragment was not modified.
