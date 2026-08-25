## Evidence

Concept: rhythm, replayed attempt_0004. The demo runner executed `uv run mimic_utils run-demo rhythm` using embedded Pathling on Spark without editing carried artifacts. Execution succeeded and the shape gate reported `shape_ok`; schema matching was true with no incompatible types. The output had 12,439 demo rows, which is observational only and not a gate. Required key column `patient_key` was present. Artifacts produced: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
