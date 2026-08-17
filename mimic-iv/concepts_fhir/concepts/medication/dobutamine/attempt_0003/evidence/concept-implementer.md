# Concept implementer evidence

- Concept: `dobutamine`
- Attempt: `0003`
- Read: the canonical source analysis and FHIR mapping carryover, `MIMIC_NOTES.md`, and the dobutamine/medication fragments.
- Reopened instruction applied: the outer projection now includes `patient_key` and `icu_encounter_key`; existing value expressions, casts, and ViewDefinition column names were preserved.
- Authored: `ViewDefinition.medication_administration.json`, `ViewDefinition.encounter_icu.json`, `concept.sql`, and `unrepresentable.json`.
- Mapping: exact ICU medication coding system/code `221653`; ICU Encounter identifier supplies `stay_id`; `linkorderid` is a typed NULL because the ETL does not represent it; numeric values are cast to FLOAT; datetimes use `TRY_CAST(... AS TIMESTAMP_NTZ)`.
- Check: `uv run mimic_utils lint-sql dobutamine` completed cleanly. No controller transition or demo/full run was performed by the implementer.
- Dataset-wide notes: no new fragment entry was appended; existing dobutamine findings already record the identifier gap, effective-period behavior, quantity precision, and DST normalization.

Artifacts: this attempt directory, especially `concept.sql`, both ViewDefinitions, and `unrepresentable.json`.
