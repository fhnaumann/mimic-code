## Evidence

Concept: `enzyme`, attempt 0001. `uv run mimic_utils run-demo enzyme` executed embedded Pathling on Spark over the demo Delta warehouse and exited successfully.

The shape gate reported `shape_ok`: all 15 expected column names were present with no extras, and all types were compatible (`INTEGER` identifiers, `TIMESTAMP` charttime, `DOUBLE` analytes). The run produced 1,411 demo rows; this is observation only and was not used as a gate.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0001/`. The implementation artifacts were not edited and no commit was made.
