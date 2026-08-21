Evidence block

Concept: `first_day_gcs`, attempt 0002.

Ran `uv run mimic_utils run-demo first_day_gcs` with embedded Pathling on Spark. Execution succeeded and registered `gcs`, `icu_encounter`, and `patient` views. Shape verdict was `shape_ok`: all seven manifest columns were present with compatible INTEGER/FLOAT types, and required `patient_key` / `icu_encounter_key` companions were accepted. Demo returned 140 rows; row count was observed only and not gated.

Write-once artifacts: `candidate.demo.parquet/` and `shape.demo.json` in the attempt directory. No errors and no commit.
