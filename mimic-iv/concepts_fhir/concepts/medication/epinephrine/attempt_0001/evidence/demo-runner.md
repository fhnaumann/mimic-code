# Demo-runner evidence

Executed `uv run mimic_utils run-demo epinephrine` using embedded Pathling
9.6.0 on Spark 4.0.2 over the local demo Delta warehouse. The attempt
executed successfully and registered `encounter_icu` and
`medication_administration` without errors.

The shape gate returned `shape_ok`: exact output column names
`[stay_id, linkorderid, vaso_rate, vaso_amount, starttime, endtime]`, compatible
types for INTEGER/INTEGER/FLOAT/FLOAT/TIMESTAMP/TIMESTAMP, and no incompatible
types. It produced 36 demo rows. Row count was recorded only and was not used
as a gate. Artifacts are `candidate.demo.parquet` and `shape.demo.json` in
`attempt_0001/`; the latter records `executed: true`, `schema.match: true`, and
the shape verdict.
