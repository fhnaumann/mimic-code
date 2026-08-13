# Demo-runner evidence

Attempt 0002 passed the embedded Pathling/Spark demo shape gate via `uv run mimic_utils run-demo milrinone`. Candidate columns exactly matched the six manifest columns, with compatible INTEGER/INTEGER/FLOAT/FLOAT/TIMESTAMP/TIMESTAMP types and no incompatible types. The demo produced 15 rows; row count was recorded only and not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `attempt_0002/`. No implementation files were modified.
