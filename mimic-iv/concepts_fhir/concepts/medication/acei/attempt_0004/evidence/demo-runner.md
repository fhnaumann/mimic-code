Evidence block — concept `acei`, stage `demo-runner`, attempt 0004.

`mimic_utils validate-demo acei` transitioned the attempt to VALIDATING_DEMO.
The implementer had already executed the same embedded Pathling/Spark shape
check and created the write-once demo artifact before the orchestrator's
runner call. Consequently `mimic_utils run-demo acei` refused to overwrite the
existing `candidate.demo.parquet` and reported the write-once guard, rather
than executing a second time.

The existing `shape.demo.json` was inspected and records `executed: true`,
`verdict: shape_ok`, `candidate_row_count: 107`, identical five expected and
actual columns, and no incompatible types. The schema is
`subject_id int`, `hadm_id int`, `acei string`, `starttime timestamp_ntz`, and
`stoptime timestamp_ntz`. Row count was not gated. The implementation therefore
passes the demo shape gate; this earns permission for full data only and does
not establish correctness.

Artifacts used: `candidate.demo.parquet` and `shape.demo.json` in attempt 0004.
