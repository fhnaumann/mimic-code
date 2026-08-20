# Evidence: demo-runner (`first_day_bg`, attempt 0002)

Command: `uv run mimic_utils run-demo first_day_bg`, using embedded Pathling on
Spark over the demo Delta warehouse.

Execution completed successfully. The shape artifact reports `shape_ok`, with
all 44 manifest columns present, no missing columns, no incompatible types,
and the required key columns `patient_key` and `icu_encounter_key` present.
The candidate produced 140 demo rows versus 73,181 full-oracle rows; this row
count is reported only and was not gated.

Artifacts:

- `candidate.demo.parquet/`
- `shape.demo.json`

The demo gate permits the full-data run. No dataset-wide quirk was discovered
or appended to `MIMIC_NOTES.d/first_day_bg.md`.
