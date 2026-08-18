# concept-implementer evidence

Concept: `icp`; attempt: `0004`.

The implementer read the reusable source and FHIR analyses, the manifest,
`AGENTS.md`, `MIMIC_NOTES.md`, the notes protocol, and the ICP fragment. It
authored fresh ViewDefinitions and SQL using exact system/code filtering for
chartevents itemids `220765` and `227989`, the Patient and ICU Encounter
identifier/resource-key spine, paired `patient_key` and `icu_encounter_key`
outputs, `TIMESTAMP_NTZ` datetime handling, Quantity casts, and the strict
range plus grouped `MAX` derivation. Resource-id inversion was not used.

Artifacts produced once:

- `ViewDefinition.icp_observation.json`
- `ViewDefinition.icp_patient.json`
- `ViewDefinition.icp_icu_encounter.json`
- `concept.sql`

`uv run mimic_utils lint-sql icp` passed. The implementer reported the demo
shape gate passed with required key columns, no unrepresentable declaration was
needed, and no new dataset-wide notes fragment entry was identified.
