## Evidence

Ran `uv run mimic_utils run-demo blood_differential` for attempt 0002 using embedded Pathling 9.6.0 on Spark 4.0.2 over the local Delta warehouse, with Parquet output and no HTTP server.

The shape verdict was `shape_ok`: execution succeeded, all 20 manifest column names matched, and all types were compatible (`INTEGER`, `TIMESTAMP`, `DECIMAL(38,4)`, and `DOUBLE` after normalization). The demo produced 2,763 rows, reported only as non-gating evidence.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0002/`. No implementation artifact was modified.
