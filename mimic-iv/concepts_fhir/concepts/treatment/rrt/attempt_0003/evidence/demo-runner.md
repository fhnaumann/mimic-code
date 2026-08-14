## Evidence

The corrected attempt 0003 executed successfully through embedded Pathling on
Spark.  The shape gate reports `shape_ok`: all five expected column names are
present with no extras, and candidate `int`, `timestamp_ntz`, and `string`
types are compatible with the oracle's INTEGER, TIMESTAMP, and VARCHAR types.
The 5,130-row demo count is reported only as non-gating evidence.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
