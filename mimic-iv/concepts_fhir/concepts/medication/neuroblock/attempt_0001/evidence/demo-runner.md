# Demo-runner evidence — neuroblock

Ran `uv run mimic_utils run-demo neuroblock` with embedded Pathling 9.6.0 on
Spark over the local Delta warehouse. Execution completed successfully and
wrote `candidate.demo.parquet` and `shape.demo.json`. All six candidate column
names matched the oracle manifest and all types were compatible: integer,
integer, float, float, timestamp_ntz, timestamp_ntz versus INTEGER, INTEGER,
FLOAT, FLOAT, TIMESTAMP, TIMESTAMP. The demo has 0 rows because the requested
itemids are absent from the 100-patient cohort; this is `unsure`, not failure,
and row count is explicitly non-gating. The shape gate permits the full run.
