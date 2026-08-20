# Implementer evidence — neuroblock attempt 0005

The implementer read the canonical source SQL, reusable neuroblock
source-analyst and FHIR-prober carryover, the exact oracle manifest entry,
`MIMIC_NOTES.md`, the reopened resource-key instruction, and relevant ICU
medication fragments. It authored fresh MedicationAdministration and ICU
Encounter ViewDefinitions, `concept.sql`, and `unrepresentable.json`.

The candidate filters the exact ICU medication codes `222062` and `221555` and
non-null rates, recovers `stay_id` through the ICU Encounter identifier,
projects typed-NULL `orderid`, FLOAT Quantity values, and `TIMESTAMP_NTZ`
effective endpoints. It emits the six manifest columns followed by both
manifest-required additive resource keys, `icu_encounter_key` and
`patient_key`; resource IDs remain opaque. The absent orderid declaration
documents the upstream ICU MedicationAdministration representation gap.

JSON validation passed and `uv run mimic_utils lint-sql neuroblock` passed. No
new dataset-wide fragment entry was appended.

Artifacts: `ViewDefinition.medication_administration.json`,
`ViewDefinition.encounter_icu.json`, `concept.sql`, and `unrepresentable.json`
in this attempt directory.
