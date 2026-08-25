# Demo runner evidence

Concept: `inflammation`  
Attempt: `attempt_0004`  
Verdict: `shape_ok`

`uv run mimic_utils run-demo inflammation` completed successfully using embedded Pathling on Spark. The returned columns were `subject_id`, `hadm_id`, `charttime`, `specimen_id`, `crp`, plus the required key columns `patient_key`, `encounter_key`, and `specimen_key`. All manifest columns and types were compatible; the extra columns are declared key columns and were accepted as a notice. The demo returned 42 rows; row count was not used as a gate.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory. No files were edited by the replay demo run.
