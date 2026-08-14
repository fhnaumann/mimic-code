# Concept-implementer evidence — rhythm

The implementer read the canonical SQL, both reusable analyses, the curated
notes and rhythm fragment, the oracle manifest, and the ViewDefinition/Pathling
conventions. It created three ViewDefinitions and `concept.sql` in this
write-once attempt. The implementation filters the exact chartevents system
and five codes, joins opaque Patient and ICU Encounter reference keys to their
identifier values, preserves the `(subject_id, charttime)` grain and repeated
rows, and replays the distinct sorted `heart_rhythm` aggregation and lexical
ectopy maxima. It uses `TRY_CAST(... AS TIMESTAMP_NTZ)` and bounded VARCHAR
casts. No resource-id inversion or unrepresentable declaration was used.

`uv run mimic_utils lint-sql rhythm` was clean. Artifacts:
`ViewDefinition.rhythm_observation.json`, `ViewDefinition.rhythm_patient.json`,
`ViewDefinition.rhythm_encounter.json`, and `concept.sql`.
