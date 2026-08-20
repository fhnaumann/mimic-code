# Demo runner evidence — `first_day_height`

Ran `uv run mimic_utils run-demo first_day_height` using embedded
Pathling/Spark with dependency preprocessing. Execution completed cleanly and
registered `height`, `icu_encounter`, and `patient` views.

The shape verdict was `shape_ok`. Candidate semantic columns were
`subject_id` (int), `stay_id` (int), and `height` (decimal(38,2)), compatible
with the manifest's INTEGER, INTEGER, and DECIMAL(38,2) types. The additional
`patient_key` and `icu_encounter_key` columns were the manifest-declared
required key columns, not unexpected output. The candidate returned 140 demo
rows; this count was recorded only as evidence and was not gated.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json` (`shape_ok`)

Both are under
`mimic-iv/concepts_fhir/concepts/firstday/first_day_height/attempt_0001/`.
