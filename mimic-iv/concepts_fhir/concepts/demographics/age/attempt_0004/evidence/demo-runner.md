Evidence block

Concept: `age`, attempt `0004`.

Executed `uv run mimic_utils run-demo age` with embedded Pathling on Spark; exit code 0. The demo shape gate reported `shape_ok` / `SHAPE OK` and permits full-data validation.

Result columns: `subject_id int`, `hadm_id int`, `admittime timestamp_ntz`, `anchor_age smallint`, `anchor_year smallint`, `age bigint`, `patient_key string`, `encounter_key string`. All six manifest columns were present with compatible types; `patient_key` and `encounter_key` are the two required manifest key columns and are not gate failures. No columns were missing or incompatible.

Result rows: 275 demo rows. This is observational only; row count is not a demo gate and does not claim correctness.

Artifacts produced:
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/shape.demo.json`

The attempt may proceed to full-data validation. No dataset-wide quirk was newly established and no notes fragment was appended.
