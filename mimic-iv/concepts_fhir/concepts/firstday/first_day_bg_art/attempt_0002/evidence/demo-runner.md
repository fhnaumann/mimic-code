# Demo-runner evidence: `first_day_bg_art`

- Concept: `first_day_bg_art`
- Attempt: `0002` (replayed, carried artifacts byte-identical from attempt 0001)
- Command: `uv run mimic_utils run-demo first_day_bg_art`
- Result: embedded Pathling on Spark executed successfully; `shape_ok`.
- Schema: all 44 manifest columns present, with no missing or unexpected columns; required `patient_key` and `icu_encounter_key` columns present.
- Types: all `DOUBLE` columns compatible; `aado2_calc_min` and `aado2_calc_max` are `DECIMAL(38,4)`; no incompatible types.
- Rows: 140 demo rows. Row count is non-gating under the loop contract.
- No SQL or ViewDefinition was edited. No dataset-wide quirk was discovered.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
