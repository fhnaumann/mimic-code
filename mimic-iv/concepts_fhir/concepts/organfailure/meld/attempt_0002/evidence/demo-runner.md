# Demo runner evidence — meld attempt_0002

- Ran `uv run mimic_utils run-demo meld` with embedded Pathling on Spark; no implementation artifacts were edited.
- The replay attempt's shape gate returned `shape_ok` (exit 0).
- All 10 oracle columns matched by name and compatible type: `subject_id`, `hadm_id`, `stay_id`, `meld_initial`, `meld`, `rrt`, `creatinine_max`, `bilirubin_total_max`, `inr_max`, and `sodium_min`.
- Required resource key columns `encounter_key`, `icu_encounter_key`, and `patient_key` were present with string values.
- Candidate demo row count was 140; row count is informational and not a gate.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
- No new dataset-wide quirk was reported; no `MIMIC_NOTES.d/meld.md` entry was appended.
