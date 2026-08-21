# Concept-implementer evidence — `urine_output_rate`

The implementer created the write-once artifacts:

- `ViewDefinition.urine_output_rate_icu_encounter.json`
- `ViewDefinition.urine_output_rate_observation.json`
- `concept.sql`

The Encounter view filters ICU identifiers and projects the stay identifier,
period endpoints, Encounter resource key, and Patient reference key. The
Observation view constrains the chartevents coding system and exact code
`220045`, projects effective datetime variants, and exposes the Encounter
reference key. SQL preserves the canonical heart-rate gate, `LAG`, 23-hour
self-join, 6/12/24-hour aggregates, `SUM(DISTINCT)`, weight interval bounds,
rounding, and NULL branches. It consumes only the preprocessed `urine_output`
and `weight_durations` dependency views and joins them by opaque
`icu_encounter_key`.

All 13 manifest columns are explicitly cast and required
`icu_encounter_key`/`patient_key` are emitted verbatim. FHIR datetimes use
bare `TRY_CAST(... AS TIMESTAMP_NTZ)`. The implementer ran
`uv run mimic_utils lint-sql urine_output_rate`, which passed. No new
dataset-wide finding was appended to `MIMIC_NOTES.d/urine_output_rate.md` and
no commit was made.
