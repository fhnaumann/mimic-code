# Demo runner evidence — `gcs`

- Concept: `gcs`; attempt: `0003`.
- Read/checked: existing embedded-Pathling-on-Spark `candidate.demo.parquet` and `shape.demo.json`; the requested rerun was correctly refused by the write-once guard.
- Result: prior demo execution completed (`executed=true`, `_SUCCESS` present); shape verdict `shape_ok`.
- Shape: columns exactly `[subject_id, stay_id, charttime, gcs, gcs_motor, gcs_verbal, gcs_eyes, gcs_unable]`; compatible types `INTEGER, INTEGER, TIMESTAMP, FLOAT, FLOAT, FLOAT, FLOAT, INTEGER`; no missing/extra/incompatible columns.
- Row count: `3,279` demo rows, reported only and not gated.
- Artifacts: `candidate.demo.parquet/`, `shape.demo.json`, and this evidence file. No artifact or state transition was made.
