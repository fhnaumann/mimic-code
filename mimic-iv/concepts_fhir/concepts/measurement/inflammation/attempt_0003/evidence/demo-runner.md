# Evidence: demo-runner

`uv run mimic_utils run-demo inflammation` executed successfully with embedded Pathling on Spark. The candidate wrote `candidate.demo.parquet` and produced `shape.demo.json` with `verdict: shape_ok`, `match: true`, no missing columns, no unexpected columns, and no incompatible types. The five oracle columns matched: `subject_id` INTEGER, `hadm_id` INTEGER, `charttime` TIMESTAMP-compatible `timestamp_ntz`, `specimen_id` INTEGER, and `crp` DOUBLE. The three additional columns `patient_key`, `encounter_key`, and `specimen_key` are the declared manifest key columns. Demo row count was 42 versus the 117,898 full-oracle rows and was informational only.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/inflammation/attempt_0003/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/measurement/inflammation/attempt_0003/shape.demo.json`
