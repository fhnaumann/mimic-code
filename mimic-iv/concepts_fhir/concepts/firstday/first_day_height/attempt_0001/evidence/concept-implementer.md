# Concept implementer evidence — `first_day_height`

Created the immutable attempt artifacts:

- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.patient.json`
- `concept.sql`

The Encounter view selects ICU encounters by the exact ICU identifier system,
and projects `getResourceKey()` / `subject.getReferenceKey(Patient)` plus
`period.start` and the stay identifier value. The Patient view projects its
resource key and exact patient identifier value. SQL casts numeric identifier
values to INTEGER, parses `period.start` as `TIMESTAMP_NTZ`, joins the
preprocessed `height` temp view by opaque `icu_encounter_key`, preserves the
left-join spine, applies the inclusive `[period_start - 6 hours,
period_start + 1 day]` window, rounds the average to two decimals, and emits
the manifest columns plus `patient_key` and `icu_encounter_key`.

The completed dependency was consumed rather than rederived; resource ids were
not parsed or used as semantic witnesses. `uv run mimic_utils lint-sql
first_day_height` passed cleanly, JSON validation passed, and `git diff --check`
was clean. No `unrepresentable.json` was needed and no notes fragment was
appended. Artifacts are under
`mimic-iv/concepts_fhir/concepts/firstday/first_day_height/attempt_0001/`.
