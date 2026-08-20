# Demo evidence — norepinephrine attempt_0003

`uv run mimic_utils run-demo norepinephrine` executed successfully through
embedded Pathling on Spark and returned `shape_ok`. All six manifest columns
were present with compatible INTEGER/FLOAT/TIMESTAMP types, and required
`icu_encounter_key` and `patient_key` columns were present. No execution,
column, or type errors occurred.

The demo observed 947 candidate rows; row count is not gated. The runner wrote
`candidate.demo.parquet` and `shape.demo.json` in this attempt directory. The
pass only permits the full-data run and is not a correctness verdict.
