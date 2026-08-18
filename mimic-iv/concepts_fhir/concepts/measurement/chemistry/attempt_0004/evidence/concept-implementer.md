# Evidence: concept-implementer — chemistry attempt 0004

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the FHIR mapping and
Pathling SQL conventions, the canonical chemistry SQL, the full chemistry
manifest entry, and the reusable chemistry source-analysis and FHIR-prober
carryover. Existing fragments were treated as provisional leads.

Produced exactly once in this attempt:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

The implementation filters the exact lab coding system and twelve source
itemids, maps specimen and identifier spines, uses a LEFT hospital Encounter
join, preserves typed NULL admission identifiers when the reference is absent,
casts datetime values as `TIMESTAMP_NTZ`, and emits the manifest columns plus
the required opaque resource-key columns. It does not parse, reconstruct,
hash, hardcode, or semantically infer any resource id.

The reopened resource-key instruction was applied: `patient_key` accompanies
`subject_id`, `encounter_key` accompanies `hadm_id`, and `specimen_key`
accompanies `specimen_id`. No `unrepresentable.json` was needed.

Check: `uv run mimic_utils lint-sql chemistry` completed cleanly. No new
dataset-wide quirk was discovered, so no notes fragment was modified.
