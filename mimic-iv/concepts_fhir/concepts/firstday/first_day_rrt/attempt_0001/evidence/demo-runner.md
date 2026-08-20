# Demo-runner evidence — `first_day_rrt`

Ran `uv run mimic_utils run-demo first_day_rrt` using embedded Pathling 9.6.0
on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`. The execution
completed without errors and the shape verdict was `shape_ok`.

The five manifest columns were present with compatible types and no columns
were missing or incompatible. Required opaque key columns
`icu_encounter_key` and `patient_key` were also present. The demo candidate
contained 140 rows; row count was reported only and was not used as a gate.

Artifacts produced:

- `candidate.demo.parquet`
- `shape.demo.json`

The shape gate permits a full-data run; it does not establish correctness.
