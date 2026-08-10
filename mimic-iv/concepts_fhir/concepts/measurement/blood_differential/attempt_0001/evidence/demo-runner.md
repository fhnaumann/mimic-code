## Evidence

Ran `uv run mimic_utils run-demo blood_differential` with embedded Pathling 9.6.0 on Spark 4.0.2 over the local demo Delta warehouse. No HTTP server was used. Four ViewDefinitions were registered as temp views, `concept.sql` executed, and Parquet output was written.

The shape verdict was `shape_ok`: execution succeeded; all 20 returned column names matched the oracle manifest; and all types were compatible, including `timestamp_ntz`, `decimal(38,4)`, and `double`. The demo produced 2,763 rows; this is reported evidence only and was not used as a gate.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0001/`. No artifacts required modification.
