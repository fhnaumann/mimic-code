# Demo-runner evidence — complete_blood_count, attempt_0002

Embedded Pathling on Spark executed all four ViewDefinitions and concept.sql
successfully. The shape gate reported `shape_ok`: all 14 oracle column names
matched and all types were compatible (`INTEGER`, `TIMESTAMP_NTZ`, and `DOUBLE`).
The demo returned 2,959 rows; this is reported evidence only and was not used as
a correctness gate.

Artifacts produced:
- `shape.demo.json`
- `candidate.demo.parquet/`

The attempt may proceed to full-data validation.
