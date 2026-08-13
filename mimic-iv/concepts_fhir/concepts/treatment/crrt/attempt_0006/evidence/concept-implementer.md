# Concept implementer evidence

- Concept: `crrt`; attempt: `0006`.
- Read the canonical source analysis and FHIR probe carryover, `MIMIC_NOTES.md`, the CRRT fragment, the source SQL, the oracle manifest, and prior attempts.
- Authored fresh `ViewDefinition.crrt_observation.json`, `ViewDefinition.crrt_encounter.json`, and `concept.sql`.
- Preserved repeated observations before the `(stay_id, charttime)` pivot and used opaque resource/reference IDs only for equality joins.
- Used explicit output casts and bare `TRY_CAST(... AS TIMESTAMP_NTZ)` for datetime aliases; no UUID recovery or unrepresentable declaration.
- `uv run mimic_utils lint-sql crrt` passed.

Artifacts: `ViewDefinition.crrt_observation.json`, `ViewDefinition.crrt_encounter.json`, `concept.sql`.
