# Demo-runner evidence — creatinine_baseline attempt 0003

- Command: `uv run mimic_utils run-demo creatinine_baseline` using embedded
  Pathling on Spark.
- Verdict: `shape_fail`; the candidate did not execute, so no Parquet or shape
  artifact was produced and no schema/row comparison was possible.
- Spark reported unresolved column `ag.subject_id` at `concept.sql:26`; the
  dependency `age` view exposes `patient_key` and not `subject_id`.
- The runner also observed that the final SELECT includes `patient_key` and
  `encounter_key`, which are not among the seven oracle comparison columns;
  this is a shape issue to correct in a new immutable attempt.
- No implementation artifacts were edited by the runner and nothing was
  committed.
