Evidence block from concept-implementer:

Concept: ventilation; attempt: 0001.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/ventilation/attempt_0001/ViewDefinition.ventilation_encounter.json`
- `mimic-iv/concepts_fhir/concepts/treatment/ventilation/attempt_0001/concept.sql`

The implementation consumes `oxygen_delivery` and `ventilator_setting` by their published stems, recovers `stay_id` through ICU Encounter identifiers, preserves the event grid, exact CASE literals and priority, LEFT joins, boundary-based 14-hour rules, windows, sequence, grouping, and manifest casts. Required opaque `patient_key` and `icu_encounter_key` columns are retained only as join/provenance keys. No `unrepresentable.json` was needed.

Read the canonical SQL, ventilation carryover analyses, completed dependency artifacts/evidence, full manifest, `MIMIC_NOTES.md`, and fragments `ventilator_setting.md`, `oxygen_delivery.md`, and `ventilation.md`. Applied identifier-spine, opaque-key, exact coding-system, categorical component text, datetime `TIMESTAMP_NTZ`, UTC rebuild, and bounded `VARCHAR` guidance. Provisional fragment claims were checked against the completed dependency probes and exact full comparisons. No new dataset-wide quirk was discovered; no fragment was appended.

`uv run mimic_utils lint-sql ventilation` passed cleanly.
