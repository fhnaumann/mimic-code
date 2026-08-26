# Demo-runner evidence — sapsii attempt_0001

`mimic_utils validate-demo sapsii` froze the implementation after SQL lint
passed. The attempt already contained `candidate.demo.parquet` and
`shape.demo.json` from the implementer's completed embedded Pathling/Spark
execution, so the demo runner's repeated `run-demo` invocation was refused by
the write-once guard; this was not a shape or execution failure and no artifact
was modified.

The frozen shape artifact records `executed: true`, `verdict: shape_ok`, all 22
oracle columns present with compatible INTEGER/TIMESTAMP/DOUBLE types, no
missing or incompatible columns, and the three expected FHIR key companions
(`encounter_key`, `icu_encounter_key`, `patient_key`). The observed candidate
row count was 140 versus 73,181 full-oracle rows; row count is explicitly
non-gating. Artifacts checked: `shape.demo.json` and
`candidate.demo.parquet`; no commit was made. This earns permission to spend a
full-data run, not a correctness claim.
