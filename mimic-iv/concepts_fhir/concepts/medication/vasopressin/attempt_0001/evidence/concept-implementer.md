Implemented attempt 0001 for `vasopressin`.

Created:
- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

Preserved itemid `222315`, `units/min` × `60.0`, effective[x] variants, Quantity casts, ICU identifier join, and all six manifest columns. Declared `linkorderid` as typed NULL because it is not represented in FHIR. Read the source SQL, both carryover analyses, manifest, canonical ViewDefinition, `MIMIC_NOTES.md`, and `MIMIC_NOTES.d/vasopressin.md`. Lint result: `sql-lint: vasopressin: clean`. No new dataset-wide notes were appended and no commit was made.
