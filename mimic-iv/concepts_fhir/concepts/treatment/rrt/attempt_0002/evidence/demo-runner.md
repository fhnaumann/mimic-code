## Evidence

The embedded Spark demo run executed successfully for `rrt` attempt 0002.
`shape.demo.json` reports `shape_ok`: all five column names match the oracle
manifest and all types are compatible (`stay_id`, `dialysis_present`, and
`dialysis_active` integer-compatible; `charttime` timestamp-compatible;
`dialysis_type` string-compatible).  The 5,130-row demo count is reported only
as non-gating evidence.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
