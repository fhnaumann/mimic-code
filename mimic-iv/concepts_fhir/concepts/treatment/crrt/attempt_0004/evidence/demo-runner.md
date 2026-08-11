## Evidence

`uv run mimic_utils run-demo crrt` executed successfully with embedded
Pathling on Spark over the demo Delta warehouse. The result was `shape_ok`:
all 24 oracle column names matched and all types were compatible. The demo
produced 580 rows; row count is explicitly non-gating and the nonzero result
was not treated as correctness evidence.

Artifacts produced:

- `candidate.demo.parquet/`
- `shape.demo.json` (`schema.match: true`)

The attempt may proceed to full-data validation.
