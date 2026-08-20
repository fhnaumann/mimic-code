# Demo evidence — vasopressin attempt 0002

`uv run mimic_utils run-demo vasopressin` executed successfully with embedded
Pathling on Spark over the demo Delta warehouse. The candidate produced 55
rows and eight columns. All six oracle columns were present with compatible
types: `stay_id` INTEGER, `linkorderid` INTEGER, `vaso_rate` FLOAT,
`vaso_amount` FLOAT, `starttime` TIMESTAMP, and `endtime` TIMESTAMP. The two
additional columns, `icu_encounter_key` and `patient_key`, are the manifest's
declared FHIR key columns and were accepted as such by the shape gate.

Shape verdict: `shape_ok`; no execution, missing-column, or incompatible-type
failure. The row count is non-gating and this pass only permits the full-data
run. Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
