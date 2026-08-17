# Implementer evidence — `bg`, attempt 0007

The concept implementer read the authoritative loop contract, `MIMIC_NOTES.md`,
the reusable `bg` source analysis and FHIR probe, the canonical
`mimic-iv/concepts/measurement/bg.sql`, and the relevant dataset fragments.

It created fresh ViewDefinitions for Patient, hospital Encounter, lab Specimen,
lab Observation, and chart Observation, plus `concept.sql`. The implementation
uses the Observation-to-Specimen grouping spine, exact proprietary code-system
filters, left Encounter joining, source time windows and pivots, `TIMESTAMP_NTZ`
wall-time casts, `NULLIF(value_string, '___')`, and explicit output casts. It
retains the 27 manifest columns and emits the required `patient_key` and
`encounter_key` resource-key columns. No unrepresentable declaration was needed.

The reopened instruction was applied: paired resource keys are projected at the
outermost SELECT and MIMIC identifier columns remain the oracle join values.
`uv run mimic_utils lint-sql bg` passed cleanly; JSON and outer-SELECT manifest
validation also passed. No demo or full-data run was performed by this stage.

Artifacts produced once:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.chart_observation.json`
- `concept.sql`

No new dataset-wide quirk was reported or appended to `MIMIC_NOTES.d/bg.md`.
