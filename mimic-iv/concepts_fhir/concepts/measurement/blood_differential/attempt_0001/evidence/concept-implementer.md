## Evidence

The implementation read `LOOP_CONTRACT.md`, the full curated `MIMIC_NOTES.md`, source and FHIR-prober carryover, the oracle manifest, relevant `bg` attempts/carryover, and the notes protocol. It authored four ViewDefinitions and `concept.sql` in the immutable attempt directory.

The port preserves the exact source itemids and value predicates, specimen-level aggregation, item-specific scaling, percentage-based absolute-value imputation, rounding, nullable `hadm_id` left join, and all 20 manifest columns in the required names/types/order. FHIR UUID keys are used only for joins; emitted IDs come from identifier values. No unrepresentable declaration was required and no dataset-wide note was appended. JSON validation and label/column-order checks passed; demo execution was intentionally left to the demo stage.

Artifacts produced:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

All artifacts are under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0001/`.
