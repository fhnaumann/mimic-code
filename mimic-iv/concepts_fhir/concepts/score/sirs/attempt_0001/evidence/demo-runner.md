# Demo-runner evidence — sirs, attempt_0001

`uv run mimic_utils run-demo sirs` executed successfully with embedded
Pathling on Spark over the local demo Delta warehouse. The shape artifact is
`shape.demo.json`; the candidate is
`candidate.demo.parquet/`. Execution was true, all eight manifest columns were
present, and all eight types were compatible (`incompatible_types: []`). The
three additional columns `encounter_key`, `icu_encounter_key`, and
`patient_key` are the required FHIR key columns and were accepted by the shape
gate. The demo returned 140 rows; row count was explicitly not gated.

Result: `shape_ok`, permission to proceed to the full-data gate. This demo
result is not a correctness verdict.
