## Demo runner evidence

`uv run mimic_utils run-demo first_day_urine_output` executed successfully with embedded Pathling 9.6.0 on Spark 4.0.2. The shape verdict was `shape_ok`; all manifest value columns were present with compatible INTEGER/DOUBLE types, and the required `patient_key` and `icu_encounter_key` columns were present. The demo produced 140 rows versus the full manifest's 73,181 rows; this row count is observational only and was not gated. No execution or schema errors occurred.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in attempt 0001. The controller remained `VALIDATING_DEMO`; no transition or implementation artifact was modified.
