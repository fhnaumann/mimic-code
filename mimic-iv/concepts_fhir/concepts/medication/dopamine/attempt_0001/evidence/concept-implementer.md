Evidence block — Concept: dopamine, attempt 0001.

The implementer read both carryover analyses, the loop contract, curated MIMIC notes, relevant notes fragments, the manifest entry, and canonical ViewDefinition conventions. It produced:

- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

The port filters the exact ICU medication system/code pair for item `221662`, joins MedicationAdministration context UUIDs to ICU Encounter identifier values for `stay_id`, coalesces effective Period/dateTime variants only after `TIMESTAMP_NTZ` casts, casts Quantity aliases numerically, and emits typed NULL for unrepresentable `linkorderid`. JSON parsing, manifest column/order and key-leak checks, and `git diff --check` passed. No new dataset-wide notes entry was needed.
