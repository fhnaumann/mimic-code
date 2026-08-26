## Evidence

- Read: replay attempt_0004 artifacts and the oracle manifest; ran `uv run mimic_utils run-demo antibiotic`.
- Checked: embedded Pathling on Spark executed all five ViewDefinitions and `concept.sql` successfully. All seven oracle columns were present; the three additional resource-key columns were expected manifest key columns. Candidate types were compatible with the oracle (`timestamp_ntz`/`TIMESTAMP` normalized as compatible); no incompatible types were reported.
- Result: `shape_ok`. The demo candidate had 903 rows; row count is observational only and was not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
