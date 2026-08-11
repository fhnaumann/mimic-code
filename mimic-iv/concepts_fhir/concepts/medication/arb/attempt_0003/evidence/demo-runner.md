# Demo shape-gate evidence

Attempt 0003 executed successfully with `uv run mimic_utils run-demo arb` using embedded Pathling 9.6.0 on Spark over the local demo Delta warehouse. All five ViewDefinitions registered and `concept.sql` ran successfully. The candidate returned exactly `subject_id`, `hadm_id`, `arb`, `starttime`, and `stoptime`; compatible types were `int`, `int`, `string`, `timestamp_ntz`, and `timestamp_ntz` against the manifest's INTEGER, INTEGER, VARCHAR, TIMESTAMP, and TIMESTAMP. Verdict: `shape_ok`.

The 35 demo rows are observation only; row count is not a gate and the full-data oracle has 39,534 rows. No dataset-wide quirk was discovered or appended. Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0003/`.
