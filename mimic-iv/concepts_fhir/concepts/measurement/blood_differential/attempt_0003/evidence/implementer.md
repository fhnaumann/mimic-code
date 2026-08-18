# Implementer evidence — blood_differential attempt 0003

The implementation stage read the reusable source analysis and FHIR probe in
`mimic-iv/concepts_fhir/carryover/blood_differential/`, the curated
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and the owned
`MIMIC_NOTES.d/blood_differential.md` fragment. It applied the reopened
resource-key instruction by retaining opaque `patient_key`, `encounter_key`,
and `specimen_key` columns beside the compared MIMIC identifier columns.

It created four ViewDefinitions for the lab Observation, Patient, Specimen,
and hospital Encounter streams, plus `concept.sql`. The SQL uses the exact
23-item lab code set and coding system, comparator-aware numeric filtering,
specimen grouping, source pivots and `/1000.0` conversions, absolute-value
imputation, and four-decimal rounding. It uses equality joins only for FHIR
resource/reference keys, a LEFT JOIN for Encounter, `TIMESTAMP_NTZ` datetime
handling, and typed output casts. Resource IDs are not parsed or regenerated.

JSON validation passed and `uv run mimic_utils lint-sql blood_differential`
reported clean. No new dataset-wide quirk was discovered, so the notes
fragment was not changed and `MIMIC_NOTES.md` was not edited.

Artifacts:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.encounter.json`
- `concept.sql`
