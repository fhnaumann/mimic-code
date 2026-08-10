# Demo shape-gate evidence

- Command: `uv run mimic_utils run-demo bg` using embedded Pathling on Spark.
- Result: execution succeeded; all five ViewDefinitions registered and `concept.sql` ran successfully.
- Shape: `shape_ok`; all 27 column names matched, with no missing or extra columns and no incompatible types. `charttime` was `timestamp_ntz`, `fio2_chartevents` was `float`, `aado2_calc` was `decimal(38,4)`, and remaining numeric columns were compatible doubles.
- Row count: 889 demo rows versus 511,637 full-oracle rows; non-gating context only.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in attempt 0003.
- Shared knowledge: existing `MIMIC_NOTES.md` entries were used; no dataset-wide quirk was added or updated.
