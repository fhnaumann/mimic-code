# Demo-runner evidence — `icustay_detail`, attempt 0004

- Ran `uv run mimic_utils run-demo icustay_detail` with embedded Pathling 9.6.0 on Spark over the local demo Delta warehouse.
- Execution succeeded and the shape verdict was `shape_ok`.
- All 18 manifest columns were present with compatible types; the required paired key columns `encounter_key`, `icu_encounter_key`, and `patient_key` were also present.
- The candidate produced 140 demo rows. Row count was observed only and was not gated.
- No SQL or ViewDefinition artifacts were modified by the runner.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
