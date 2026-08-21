# Demo-runner evidence — `urine_output_rate`, attempt 0002

`uv run mimic_utils run-demo urine_output_rate` completed with exit 0 using
embedded Pathling/Spark. Both target ViewDefinitions, the completed dependency
views, and the corrected SQL executed successfully.

`shape.demo.json` reports `shape_ok`: all 13 manifest columns are present and
type-compatible, with no incompatible types. The extra
`icu_encounter_key`/`patient_key` columns are the required manifest key
columns. The 7,317 demo rows are observation only and non-gating. Artifacts
written in attempt 0002 are `candidate.demo.parquet` and `shape.demo.json`.
