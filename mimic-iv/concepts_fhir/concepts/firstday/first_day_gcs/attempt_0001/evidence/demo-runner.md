Evidence block

Concept: `first_day_gcs`, attempt 0001.

Ran `uv run mimic_utils run-demo first_day_gcs` with embedded Pathling on Spark over the demo Delta warehouse. Execution succeeded; views `gcs`, `icu_encounter`, and `patient` registered and the candidate ran without error.

Shape verdict: `shape_ok` / pass. All seven manifest columns were present with compatible types; no missing or incompatible columns. The two extra columns, `patient_key` and `icu_encounter_key`, are required manifest key companions and were accepted. Demo row count was 140; it was observed only and not gated. The gate reports permission to proceed to full data.

Write-once artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt directory. Demo pass is a shape gate only and is not a correctness result.
