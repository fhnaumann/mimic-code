# Demo runner evidence — `first_day_sofa`

## Result

- Command: `uv run mimic_utils run-demo first_day_sofa`.
- Engine: embedded Pathling 9.6.0 on Spark 4.0.2 over the local demo Delta warehouse.
- Execution succeeded; the three ViewDefinitions and `concept.sql` ran, with dependency views preprocessed and registered.
- Shape verdict: `shape_ok` / `match: true`; this is permission to run full data, not a correctness verdict.
- All ten manifest columns were present with compatible IntegerType/INTEGER types; no incompatible types.
- Required manifest key columns `patient_key`, `encounter_key`, `icu_encounter_key` were present as string extras and are non-gating by contract.
- Demo row count was 140; row count is recorded only and was not used as a gate.

## Evidence block

Read/checks: ran `uv run mimic_utils run-demo first_day_sofa` using embedded Spark/Pathling, checked execution, `shape.demo.json`, and the Parquet schema. Artifacts produced: `candidate.demo.parquet/` and `shape.demo.json` under this attempt. No implementation artifacts, state, notes, or commit were changed by the runner.
