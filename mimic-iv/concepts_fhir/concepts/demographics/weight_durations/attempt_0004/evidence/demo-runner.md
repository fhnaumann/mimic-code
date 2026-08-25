# Demo runner evidence — weight_durations attempt 0004

The replay attempt was executed with `uv run mimic_utils run-demo weight_durations`
using embedded Pathling on Spark over the demo Delta warehouse. Execution exited
successfully and `shape.demo.json` reports `shape_ok`.

The candidate schema matched the oracle for `stay_id` (INTEGER), `starttime`
(TIMESTAMP), `endtime` (TIMESTAMP), `weight` (DECIMAL(38,3)), and `weight_type`
(VARCHAR). The required `icu_encounter_key` and `patient_key` columns were
present. The 578 demo rows are observational only; row count is not a gate.

Artifacts checked/produced: `candidate.demo.parquet/` and `shape.demo.json` in
this attempt. The carried `concept.sql` and ViewDefinitions were not modified.
