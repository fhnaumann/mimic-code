Evidence block from demo-runner:

Command: `uv run mimic_utils run-demo ventilation` — exit code `0`.
Verdict: `shape_ok` (per `shape.demo.json` `verdict` and `schema.match: true`).
Executed: embedded Pathling on Spark; ViewDefinitions `oxygen_delivery`, `ventilator_setting`, and `ventilation_encounter` materialised, `concept.sql` ran, and Parquet was written.
Column-name comparison: all four oracle columns present (`stay_id`, `starttime`, `endtime`, `ventilation_status`); no missing columns. Extra `icu_encounter_key` and `patient_key` are manifest `key_columns`.
Type comparison: all matched columns compatible (`int`/`INTEGER`, `timestamp_ntz`/`TIMESTAMP`, `string`/`VARCHAR`); `incompatible_types: []`.
Row count (non-gating observation): 209 candidate demo rows; non-zero, so pass rather than `unsure`.
Artifacts: `mimic-iv/concepts_fhir/concepts/treatment/ventilation/attempt_0001/candidate.demo.parquet/` and `shape.demo.json`. No implementation artifacts modified; no commit made.
