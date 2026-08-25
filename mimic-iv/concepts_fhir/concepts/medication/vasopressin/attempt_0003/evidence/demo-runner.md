# Demo runner evidence — vasopressin attempt_0003

- Read: replay plan and carried `concept.sql`/ViewDefinitions; no implementation artifact was edited.
- Ran: `uv run mimic_utils run-demo vasopressin` using embedded Pathling on Spark.
- Result: execution succeeded; shape verdict `shape_ok` / may proceed to full data.
- Checked: all six oracle columns were present, declared `key_columns` (`icu_encounter_key`, `patient_key`) were present, and all types were compatible. Demo returned 55 rows versus 25,892 full-oracle rows; row count is non-gating.
- Produced: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
