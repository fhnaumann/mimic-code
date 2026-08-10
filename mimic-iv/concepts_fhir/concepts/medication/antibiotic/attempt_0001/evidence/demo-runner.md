Evidence block:

- Demo executed with embedded Pathling on Spark and produced `shape_ok` for attempt 0001.
- Candidate schema exactly matched the manifest: `subject_id`, `hadm_id`, `stay_id`, `antibiotic`, `route`, `starttime`, `stoptime`; compatible types were INTEGER/INTEGER/INTEGER/VARCHAR/VARCHAR/TIMESTAMP/TIMESTAMP.
- Candidate demo output contained 903 rows. This is informational only; row count is not a demo gate.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0001/`.
- A redundant second `run-demo` invocation was correctly refused by the write-once controller; this was not a shape failure. No implementation artifact was edited and no commit was made.
