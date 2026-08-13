# Concept implementer evidence — gcs

The implementer read the canonical GCS SQL, both GCS carryover analyses,
`LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical ViewDefinition example,
and relevant notes fragments.

Created once in this immutable attempt:

- `ViewDefinition.gcs_observation.json`
- `ViewDefinition.gcs_encounter.json`
- `ViewDefinition.gcs_patient.json`
- `concept.sql`

The implementation uses exact chartevents coding system/code filters,
identifier-based Patient and ICU Encounter equality joins, direct served
dateTime parsed as `TIMESTAMP_NTZ`, Quantity component values, the canonical
pivot and six-hour carry-forward, defaults, and typed output casts. Resource
IDs are used only as opaque equality join keys. No UUID reconstruction,
resource-ID parsing, brute force, hardcoded IDs, or Quantity-1 label inference
was used. No unrepresentable declaration was emitted because the missing
label discriminator is essential to the concept rather than an ancillary
nullable output.

`uv run mimic_utils lint-sql gcs` passed cleanly. No dataset-wide note was
appended.
