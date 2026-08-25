# Demo shape gate evidence

- Concept: `rrt`
- Attempt: `attempt_0005` (replay/data-rebuild attempt; carried SQL and ViewDefinitions were not edited)
- Command: `uv run mimic_utils run-demo rrt`
- Result: `shape_ok`; embedded Pathling 9.6.0 on Spark executed successfully.
- Columns: oracle columns `stay_id`, `charttime`, `dialysis_present`, `dialysis_active`, and `dialysis_type` matched. The required `icu_encounter_key` and `patient_key` key columns were present.
- Types: compatible; no incompatible types. `charttime` materialized as `timestamp_ntz` and normalized compatibly with oracle `TIMESTAMP`.
- Demo row count: 5,134; observed only and not gated by contract.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.

The demo gate is a shape gate only and authorizes the full-data run; it is not evidence of semantic correctness.
