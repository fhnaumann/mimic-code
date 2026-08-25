Concept: `icustay_hourly`
Attempt: `attempt_0002`

The replayed port passed the demo shape gate using embedded Pathling on Spark. Execution succeeded with `executed: true` and exit code 0. The expected columns `stay_id`, `hr`, and `endtime` were present with compatible INTEGER, BIGINT, and TIMESTAMP types. Required resource key columns `icu_encounter_key` and `patient_key` were present; they are reported as extra manifest columns but are required and not value-compared. The candidate produced 15,615 demo rows; row count is non-gating and the result was nonzero.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt. The carried `concept.sql` and `ViewDefinition.icustay_hourly_icu_encounter.json` were not edited.
