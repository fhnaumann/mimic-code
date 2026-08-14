Evidence block — demo-runner

`uv run mimic_utils run-demo ventilator_setting` completed successfully with
embedded Pathling on Spark. `shape.demo.json` reports `shape_ok`, execution
success, all 17 expected columns present with no extras or missing columns,
and compatible types (INTEGER/int, TIMESTAMP/timestamp_ntz, FLOAT/float,
VARCHAR/string). Candidate demo row count was 2,064 versus 1,006,127 full
oracle rows; row count was explicitly non-gating. No errors occurred.

Artifacts produced:
`mimic-iv/concepts_fhir/concepts/measurement/ventilator_setting/attempt_0001/candidate.demo.parquet`
and `shape.demo.json`.
