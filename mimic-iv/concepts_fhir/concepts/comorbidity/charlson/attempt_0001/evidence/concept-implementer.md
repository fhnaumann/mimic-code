# Concept-implementer evidence — charlson attempt 0001

The implementer read both reusable analyses, the canonical Charlson SQL,
`MIMIC_NOTES.md`, relevant fragments, the manifest, LOOP_CONTRACT, and the
FHIR/Pathling authoring conventions. It created three ViewDefinitions for
Condition, hospital Encounter, and Patient, and a Spark SQL port preserving all
17 literal ICD flag branches, age thresholds, and weighted index arithmetic.
Hospital diagnosis rows are selected by joining opaque Condition encounter
references to hospital Encounter resources; IDs are not parsed or regenerated.
The final query emits all 21 manifest columns as INTEGER, with `hadm_id` as the
admission grain. The available transformed Patient.birthDate is used for the
age-derived score; no unrepresentable declaration or estimate of anchor fields
was emitted.

Artifacts:
- `ViewDefinition.condition.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.patient.json`
- `concept.sql`

The implementer reports `uv run mimic_utils lint-sql charlson` clean and a demo
shape execution of 275 rows with 21 integer columns. No new notes fragment was
appended at this stage.
