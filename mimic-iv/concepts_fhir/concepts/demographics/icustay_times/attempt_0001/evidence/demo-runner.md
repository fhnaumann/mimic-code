# Demo runner evidence

Concept: `icustay_times`; attempt: `0001`.

Embedded Pathling on Spark executed all four ViewDefinitions and
`concept.sql` successfully. The shape verdict is `shape_ok`: columns are
`subject_id`, `hadm_id`, `stay_id`, `intime_hr`, `outtime_hr`, with compatible
types `INTEGER`, `INTEGER`, `INTEGER`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`.
The demo produced 140 rows; this count is informational and was not gated.

Artifacts produced:
- `candidate.demo.parquet`
- `shape.demo.json`

Both are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_times/attempt_0001/`.
