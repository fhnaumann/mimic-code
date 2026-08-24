# Demo-runner evidence — creatinine_baseline attempt 0004

- `uv run mimic_utils run-demo creatinine_baseline` completed successfully
  with embedded Pathling on Spark; the shape verdict is `shape_ok`.
- Candidate output has 275 demo rows (informational only) and all seven oracle
  columns with compatible types: `hadm_id`, `gender`, `age`, `scr_min`, `ckd`,
  `mdrd_est`, and `scr_baseline`.
- Required candidate-only key columns `encounter_key` and `patient_key` are
  present with string/Type-id-compatible values; they are not unexpected
  columns because they are declared in the manifest.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json`.
- No implementation artifacts were edited and nothing was committed.
