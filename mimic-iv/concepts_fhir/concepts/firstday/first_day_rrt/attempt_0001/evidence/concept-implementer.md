# Concept-implementer evidence — `first_day_rrt`

Read the canonical SQL, both reusable analyses, the full manifest entry,
`MIMIC_NOTES.md`, relevant fragments, the pathling/fhir mapping conventions,
and completed `rrt` attempt 0004 artifacts.

Created exactly once in attempt_0001:

- `ViewDefinition.first_day_rrt_encounter.json`
- `ViewDefinition.first_day_rrt_patient.json`
- `concept.sql`

The views project opaque ICU Encounter and Patient keys, identifier strings,
and ICU `period.start`. The SQL consumes the preprocessed `rrt` dependency,
joins on `icu_encounter_key`, retains the ICU population with the inclusive
six-hours-before/one-day-after LEFT JOIN, computes MAX dialysis flags, and
uses sorted distinct comma-space aggregation with a typed NULL fallback. It
casts all compared columns to the manifest types while leaving required key
columns verbatim. No resource ID was parsed or used as semantic data.

Both ViewDefinitions parsed as valid JSON and
`uv run mimic_utils lint-sql first_day_rrt` passed cleanly. No dataset-wide
fragment entry was added and no commit was made.
