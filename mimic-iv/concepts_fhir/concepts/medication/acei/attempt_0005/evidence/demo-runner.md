# Demo shape evidence — `acei`, attempt `0005`

`uv run mimic_utils run-demo acei` executed successfully with embedded
Pathling on Spark and returned `shape_ok`. The candidate Parquet had exactly
the oracle columns `[subject_id, hadm_id, acei, starttime, stoptime]`; types
were compatible (`INTEGER`, `INTEGER`, `VARCHAR`, `TIMESTAMP`, `TIMESTAMP`).
The demo candidate contained 107 rows, while the oracle manifest records
112,014 full rows; row count was reported only and not gated.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
