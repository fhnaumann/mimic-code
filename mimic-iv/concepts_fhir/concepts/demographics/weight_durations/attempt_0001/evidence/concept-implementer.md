# Concept-implementer evidence

The implementer read the canonical SQL, source and FHIR carryover analyses, curated notes and fragments, the oracle manifest, and the ViewDefinition/Pathling conventions. It authored two immutable ViewDefinitions and a self-contained Spark SQL query:

- `ViewDefinition.weight_durations_observation.json`
- `ViewDefinition.weight_durations_icu_encounter.json`
- `concept.sql`

The implementation filters the exact ICU chartevent system/codes, joins opaque encounter keys to ICU Encounter resources, casts the served identifier value to `INTEGER`, casts FHIR datetime strings to `TIMESTAMP_NTZ`, casts Quantity values before three-place rounding, preserves duplicate rows, reproduces the source windows/backfill/two-hour arithmetic and `UNION ALL`, and explicitly casts all five final columns. No unrepresentable declaration was needed. `uv run mimic_utils lint-sql weight_durations` passed cleanly. No additional dataset-wide quirk was found or appended.
