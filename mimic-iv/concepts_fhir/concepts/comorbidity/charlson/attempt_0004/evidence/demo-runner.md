# Demo gate evidence — charlson attempt 0004

The frozen attempt's embedded Spark demo execution had already completed before the demo-runner stage. A second `uv run mimic_utils run-demo charlson` was correctly refused by the write-once guard because `candidate.demo.parquet` and `shape.demo.json` already existed; this was not a shape failure. Direct verification of the cached gate artifact and Parquet schema found `shape_ok`, execution successful, 275 rows, all 21 oracle columns present, no unexpected or missing columns, and compatible types. The two additional string columns `patient_key` and `encounter_key` are required FHIR key columns, not unexpected outputs. All compared columns are integer-typed and both key columns are strings.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/candidate.demo.parquet`
