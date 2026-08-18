# demo-runner evidence

Concept: `icp`; attempt: `0004`.

The attempt's embedded Pathling/Spark demo execution had already completed
successfully and produced the write-once `candidate.demo.parquet` and
`shape.demo.json` artifacts. A fresh `run-demo` invocation was correctly
refused by the write-once guard; this was not a shape failure. Read-only schema
inspection confirmed the recorded `shape_ok` result.

The candidate had 303 demo rows (row count is non-gating). Compared manifest
columns were `subject_id` INTEGER, `stay_id` INTEGER, `charttime` TIMESTAMP,
and `icp` FLOAT, all compatible. The extra `patient_key` and
`icu_encounter_key` columns are the manifest-declared required resource-key
columns; there were no missing or incompatible columns.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under
`mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0004/`.
