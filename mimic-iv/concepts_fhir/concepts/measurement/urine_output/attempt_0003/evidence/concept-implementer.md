# Evidence: concept-implementer

Read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the urine-output fragment, the source/prober carryover, the canonical SQL, and the manifest. Applied the reopened instruction to retain `stay_id` as the compared integer and emit `icu_encounter_key` plus `patient_key` as opaque resource-key outputs.

Authored once in this immutable attempt:
- `ViewDefinition.urine_output_observation.json`
- `ViewDefinition.urine_output_encounter.json`
- `concept.sql`

The implementation filters the exact twelve item codes, joins Observation encounter references to ICU Encounter keys, preserves dateTime with `TIMESTAMP_NTZ`, applies the positive `227488` negation, preserves duplicate rows before `SUM`, and groups by stay/time plus required keys. `uv run mimic_utils lint-sql urine_output` passed cleanly. No resource-id parsing or reconstruction was used; no notes fragment was appended.
