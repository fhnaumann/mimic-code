# Demo-runner evidence — creatinine_baseline attempt_0001

`uv run mimic_utils run-demo creatinine_baseline` executed successfully with
embedded Pathling on Spark over the local demo Delta warehouse. The shape gate
was `shape_ok`: candidate columns exactly matched
`hadm_id, gender, age, scr_min, ckd, mdrd_est, scr_baseline`, and all seven
types were compatible with the oracle manifest. The candidate contained 275
demo rows; this row count was recorded but was not gated, and the demo run was
not treated as correctness evidence.

Artifacts:
`candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
