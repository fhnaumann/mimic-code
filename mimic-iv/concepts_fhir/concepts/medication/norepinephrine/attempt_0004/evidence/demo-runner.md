# Demo runner evidence

- Concept: `norepinephrine`
- Attempt: `0004` replay/data-rebuild attempt; carried artifacts were not edited.
- Command: `uv run mimic_utils run-demo norepinephrine`
- Result: `shape_ok`; embedded Pathling on Spark executed successfully.
- Manifest columns matched: `stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`.
- Required resource-key columns were present: `icu_encounter_key`, `patient_key`.
- Type compatibility passed; no incompatible types.
- Demo row count was 947 and was not used as a gate.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json`.

This is a shape-only pass and permits the full-data gate; it does not establish correctness.
