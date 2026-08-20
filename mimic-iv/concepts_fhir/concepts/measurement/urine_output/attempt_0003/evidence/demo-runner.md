# Evidence: demo-runner

Ran `uv run mimic_utils run-demo urine_output` using embedded Pathling on Spark. The shape gate returned `shape_ok` and permitted full validation. Candidate output had the manifest columns `stay_id`, `charttime`, and `urineoutput` with compatible `INTEGER`, `TIMESTAMP`, and `DOUBLE` types, plus the required `icu_encounter_key` and `patient_key`; no required key columns were missing. Demo row count was 7,317 and was not used as a gate.

Artifacts:
- `candidate.demo.parquet/`
- `shape.demo.json`
