# Demo-runner evidence — rhythm

`uv run mimic_utils validate-demo rhythm` transitioned the controller to
`VALIDATING_DEMO` after clean SQL lint. `uv run mimic_utils run-demo rhythm`
then executed embedded Pathling on Spark over the local Delta warehouse and
returned `shape_ok`. All seven oracle column names matched and the returned
types were compatible: integer, timestamp-compatible, and six strings. The
demo candidate had 12,437 rows versus 5,873,723 in the full oracle; this count
was reported only and was not gated. Artifacts are
`candidate.demo.parquet` and `shape.demo.json` under attempt_0001. The demo
passed the shape gate and permitted the full-data run.
