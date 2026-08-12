# Demo runner evidence

Concept `gcs`, attempt `0004`.

`uv run mimic_utils run-demo gcs` executed successfully using embedded
Pathling 9.6.0 on Spark over the demo Delta warehouse. The shape verdict was
`shape_ok`: all eight expected column names matched and all types were
compatible (`int, int, timestamp_ntz, float, float, float, float, int`). The
demo produced 3,279 rows; this row count is reported only and was not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in the attempt
directory. No implementation artifact was edited.
