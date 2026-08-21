Implemented `kdigo_uo`, attempt `0001`.

Read the source/FHIR carryover analyses, canonical SQL, oracle manifest, loop contract, curated notes, relevant provisional fragments, and completed dependency attempts. The implementation uses the ICU Encounter identifier/resource-key projection, consumes the completed `urine_output` and `weight_durations` temp views, preserves the canonical rolling-window, interval, rate, and natural-grain logic, emits required opaque `icu_encounter_key` and `patient_key` columns, uses `TIMESTAMP_NTZ`, and applies the manifest output casts. No resource-id parsing or reconstruction was used. No `unrepresentable.json` was required and no dataset-wide quirk was discovered.

Artifacts produced:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/concept.sql`

Verification: `uv run mimic_utils lint-sql kdigo_uo` reported clean.
