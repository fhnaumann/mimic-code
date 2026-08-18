# Concept implementer evidence — enzyme attempt 0003

- Read the reusable source analysis and FHIR probe at `mimic-iv/concepts_fhir/carryover/enzyme/source-analyst.md` and `fhir-prober.md`, the curated `MIMIC_NOTES.md`, relevant provisional fragments, the oracle manifest, and prior attempt evidence.
- Authored fresh Observation, Specimen, Patient, and hospital Encounter ViewDefinitions plus `concept.sql` in this write-once attempt.
- Added paired opaque resource-key outputs (`patient_key`, `encounter_key`, `specimen_key`) beside the retained integer MIMIC identifiers, as required by the reopened instruction.
- Preserved exact lab system/code filters, positive numeric Quantity filtering, specimen grouping, independent MAX pivots, LEFT Encounter join, and `TIMESTAMP_NTZ` datetime handling. No resource-id reconstruction or unrepresentable declaration was used.
- `uv run mimic_utils lint-sql enzyme` completed cleanly.
- No new dataset-wide note was appended; known incomplete Encounter references and upstream DST normalization remain documented in curated notes.

Artifacts produced:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`
