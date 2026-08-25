# Demo runner evidence — `first_day_weight`, attempt 0002

- Read: `oracle_manifest.full.json`; attempt `concept.sql`, `ViewDefinition.icu_encounter.json`, `ViewDefinition.patient.json`, and `replay_provenance.json`.
- Checked: `uv run mimic_utils run-demo first_day_weight` using embedded Pathling on Spark; replayed artifacts were not edited.
- Result: execution succeeded; `shape.demo.json` reports `shape_ok` (`match: true`, `executed: true`). Expected columns and compatible types matched: `subject_id INTEGER`, `stay_id INTEGER`, `weight_admit DOUBLE`, `weight DOUBLE`, `weight_min DECIMAL(38,3)`, and `weight_max DECIMAL(38,3)`. Declared key columns `icu_encounter_key` and `patient_key` were present.
- Row count: 140 demo rows, recorded for context only and not used as a gate.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt.
