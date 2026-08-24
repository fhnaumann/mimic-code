## Evidence

- Attempt: `blood_differential` attempt_0004 (replay/data-rebuild attempt).
- Read: `shape.demo.json`; the carried `concept.sql` and ViewDefinitions were not edited.
- Ran: `uv run mimic_utils run-demo blood_differential` after `validate-demo`.
- Result: embedded Pathling on Spark executed successfully; verdict `shape_ok`, with compatible types and no missing expected columns. The three extra columns (`patient_key`, `encounter_key`, `specimen_key`) are the required manifest key columns. Demo row count was 2,763 and was not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
