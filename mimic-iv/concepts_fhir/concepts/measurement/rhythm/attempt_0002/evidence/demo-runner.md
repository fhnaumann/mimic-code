# Demo-runner evidence — rhythm attempt 0002

`uv run mimic_utils validate-demo rhythm` passed lint and froze attempt_0002;
`uv run mimic_utils run-demo rhythm` executed embedded Pathling/Spark cleanly.
All seven column names matched the oracle and all types were compatible. The
demo returned 12,437 rows, which was reported only and not gated. Artifacts:
`shape.demo.json` and `candidate.demo.parquet`. The shape gate passed and the
attempt was eligible for a full run.
