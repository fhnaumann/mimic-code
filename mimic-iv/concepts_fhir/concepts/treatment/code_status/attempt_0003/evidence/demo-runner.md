Evidence block — `code_status`, attempt 0003

The demo shape gate executed cleanly with embedded Pathling on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`. Verdict: `shape_ok`; execution succeeded, all eight oracle column names matched, and types were compatible (`INTEGER` outputs and `TIMESTAMP_NTZ` charttime). The candidate produced 147 demo rows; row count is observation only and was not gated against the 269072 full oracle rows.

Artifacts produced:
- `shape.demo.json`
- `candidate.demo.parquet/`

This pass only permits the full-data run; it is not correctness evidence.
