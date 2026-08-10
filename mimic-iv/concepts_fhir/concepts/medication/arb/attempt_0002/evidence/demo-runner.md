# Demo runner evidence

Attempt 0002 ran `uv run mimic_utils run-demo arb` with embedded Pathling on Spark and passed `shape_ok`. Pathling registered all five views and executed without error.

Columns matched exactly: `subject_id, hadm_id, arb, starttime, stoptime`. Types were compatible (`int`, `int`, `string`, `timestamp_ntz`, `timestamp_ntz` against `INTEGER`, `INTEGER`, `VARCHAR`, `TIMESTAMP`, `TIMESTAMP`). Demo returned 35 rows; row count is observation only and not gated. No missing or extra columns occurred.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under attempt 0002. This pass only permits the full-data run and is not a correctness verdict.
