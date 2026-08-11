## Evidence

Concept: `enzyme`, attempt 0001.

The implementer read the source and FHIR carryover analyses, `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, and relevant lab fragments. It produced the write-once artifacts:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

The implementation filters the exact eleven lab-item codes and excludes comparator/string fallbacks, retains strictly positive Quantity values, groups by `specimen_id`, uses specimen and Patient identifier spines, LEFT joins hospital Encounter for nullable `hadm_id`, and emits all 15 manifest columns with explicit types. Datetimes use `TIMESTAMP_NTZ`; bounded VARCHAR casts are not needed in the final output because all identifier strings are cast to integer. JSON structure and output-column presence were checked. No `unrepresentable.json` was needed and no dataset-wide note was appended.
