## Evidence

Read the source and FHIR-prober carryover artifacts, `MIMIC_NOTES.md`, the
oxygen_delivery notes fragment, canonical SQL, oracle manifest, and the
ViewDefinition authoring reference.

Created the immutable implementation artifacts:

- `ViewDefinition.oxygen_delivery_observation.json`
- `ViewDefinition.oxygen_delivery_patient.json`
- `ViewDefinition.oxygen_delivery_encounter.json`
- `concept.sql`

The implementation filters exact chartevents systems/codes, joins by opaque
reference identity, casts identifier values to integers, uses
`TIMESTAMP_NTZ`, preserves issued/valuenum/value ranking, and maintains the
source patient/charttime grain. `uv run mimic_utils lint-sql oxygen_delivery`
reported clean. No new dataset-wide quirk was discovered.
