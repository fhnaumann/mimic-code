# Demo shape-gate evidence

- Concept: `kdigo_stages`
- Attempt: `attempt_0003` (replayed byte-identical port)
- Command: `uv run mimic_utils run-demo kdigo_stages`
- Result: executed successfully with embedded Pathling on Spark; `shape.demo.json` reports `shape_ok` and `schema.match: true`.
- Columns: all 15 oracle columns matched. The three additional columns (`patient_key`, `encounter_key`, `icu_encounter_key`) are the manifest-declared resource key columns.
- Types: compatible; `schema.incompatible_types` is empty.
- Rows: 8,729 demo rows; row count is observational only and is not a gate.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.

The replayed concept SQL and ViewDefinitions were not edited.
