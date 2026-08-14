# Concept-implementer evidence — creatinine_baseline attempt_0001

The implementer read the canonical SQL, source and FHIR-prober carryover,
curated notes, relevant fragments, LOOP_CONTRACT, and the ViewDefinition and
Spark SQL authoring conventions. It created five write-once ViewDefinitions
(`patient`, `encounter`, `observation`, `specimen`, and `condition`) plus
`concept.sql` in this attempt directory.

The candidate preserves the seven manifest columns and their required types,
uses hospital Encounter identifier values for `hadm_id`, opaque reference keys
only for equality joins, item-system plus code `50912` for creatinine, numeric
Quantity casts, specimen/admission aggregation, hospital-stream CKD ICD
prefix/version discrimination, and the canonical MDRD and baseline branches.
The served birthDate age approximation is retained without an unrepresentable
declaration or resource-id recovery. `uv run mimic_utils lint-sql
creatinine_baseline` passed cleanly, and JSON structure validation passed.

Artifacts produced:
`ViewDefinition.patient.json`, `ViewDefinition.encounter.json`,
`ViewDefinition.observation.json`, `ViewDefinition.specimen.json`,
`ViewDefinition.condition.json`, and `concept.sql`.
No additional dataset-wide quirk was appended at this stage.
