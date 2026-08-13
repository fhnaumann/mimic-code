# Demo runner evidence

- Concept: `phenylephrine`; attempt: `0002`.
- Command: `uv run mimic_utils run-demo phenylephrine`.
- The ViewDefinitions and SQL were not executed: embedded Spark failed during `JavaSparkContext` initialization with a local executor transport timeout (`Failed to connect to /140.253.236.26:59221`, `Operation timed out`).
- No `shape.demo.json` or `candidate.demo.parquet` was produced, so column/type comparison was not evaluated and no HPC run is justified from this attempt.
- This is an engineering/environment failure, not a port verdict; the same engine and warehouse executed attempt 0001 successfully. No implementation artifact was edited.
