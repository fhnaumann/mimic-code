# Demo-runner evidence

`uv run mimic_utils run-demo weight_durations` executed attempt 0002 successfully with embedded Pathling/Spark and returned `shape_ok`. All five names matched the manifest and types were compatible: integer, timestamp_ntz, timestamp_ntz, decimal(38,3), and string. The demo returned 578 rows; this count was recorded only and was not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under attempt 0002. The pass permits a full run but makes no correctness claim.
