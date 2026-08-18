Evidence block

Concept: `oxygen_delivery`; attempt: `0003`.

Created:
- `attempt_0003/ViewDefinition.oxygen_delivery_observation.json`
- `attempt_0003/ViewDefinition.oxygen_delivery_patient.json`
- `attempt_0003/ViewDefinition.oxygen_delivery_encounter.json`
- `attempt_0003/concept.sql`

Implemented Observation, Patient, and ICU Encounter projections with exact chartevents coding filters, identifier/resource-key joins, issued/storetime ranking, flow-code merging, flow-driven patient/charttime joins, four device slots, and explicit manifest casts. Added `patient_key` and `icu_encounter_key` outputs. No `unrepresentable.json` is needed.

Read the canonical SQL, source analyst, FHIR prober, full manifest oxygen_delivery entry, prior attempts, `MIMIC_NOTES.md`, and the requested sibling fragments. Applied identifier-spine, opaque-key, datetime `TIMESTAMP_NTZ`, choice-type, Quantity casting, categorical `valueString`, chartevents coding, repeated-row, and DST notes. Sibling fragments were treated as provisional; oxygen_delivery’s own findings were verified in its prober evidence. No new dataset-wide quirk was discovered or appended.

`uv run mimic_utils lint-sql oxygen_delivery` passed cleanly.
