# Demo runner evidence

Concept: `crrt`; attempt: `0005`.

- Ran `uv run mimic_utils run-demo crrt` with embedded Pathling on Spark.
- Execution succeeded; both ViewDefinitions registered and the candidate Parquet was written.
- Shape verdict: `shape_ok`.
- All 24 expected column names matched; no missing or extra columns.
- All column types were compatible with the oracle manifest.
- Candidate demo row count was 580; row count is observational only under the loop contract.

Artifact: `candidate.demo.parquet` and `shape.demo.json` in the attempt directory.
