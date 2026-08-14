# Concept implementer evidence

Concept: `urine_output`; attempt `0001`.

Created:
- `ViewDefinition.urine_output_observation.json`
- `ViewDefinition.urine_output_encounter.json`
- `concept.sql`

The Observation view projects ICU Encounter reference, Quantity value, dateTime effective time, and filters the exact twelve source itemids by both coding system and string code. The Encounter view recovers `stay_id` from the ICU identifier value. SQL preserves duplicate observations, applies the positive `227488` negation, groups by `(stay_id, charttime)`, and casts all manifest columns explicitly.

No `unrepresentable.json` is required. No resource IDs are emitted or decoded. Applied identifier, opaque-key, exact-code, Quantity-string, datetime `TIMESTAMP_NTZ`, and Spark cast guidance from `MIMIC_NOTES.md`. The current notes fragments were read as provisional leads; no new dataset-wide quirk was established or appended by the implementer.

`uv run mimic_utils lint-sql urine_output` passed cleanly. No state transitions or commits were performed.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/ViewDefinition.urine_output_observation.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/ViewDefinition.urine_output_encounter.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/concept.sql`
