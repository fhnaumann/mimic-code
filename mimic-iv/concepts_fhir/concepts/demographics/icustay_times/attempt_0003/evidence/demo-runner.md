Evidence block: Concept `icustay_times`, attempt `0003`.

The demo shape gate executed successfully with embedded Pathling on Spark over the local demo Delta warehouse (`uv run mimic_utils run-demo icustay_times`, exit code 0). Verdict: `shape_ok`. The five expected columns matched exactly: `subject_id`, `hadm_id`, `stay_id`, `intime_hr`, and `outtime_hr`; no expected columns were missing and no incompatible types were reported. Integer identifiers matched oracle `INTEGER`; timestamp outputs were compatible `timestamp_ntz` for oracle `TIMESTAMP`. The three extra resource key columns (`patient_key`, `encounter_key`, `icu_encounter_key`) are the manifest-declared comparison key columns and were accepted by the authoritative shape artifact. Demo row count was 140 and was observational only, not gated.

Artifacts:
- `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_times/attempt_0003/candidate.demo.parquet`
- `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_times/attempt_0003/shape.demo.json`

No implementation artifacts were edited and nothing was committed.
