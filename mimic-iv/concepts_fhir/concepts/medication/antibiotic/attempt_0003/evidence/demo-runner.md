# Demo-runner evidence

Command: `uv run mimic_utils run-demo antibiotic` using embedded Pathling
9.6.0 on Spark 4.0.2 over the demo Delta warehouse. The process executed
successfully and wrote Parquet.

Verdict: `shape_ok`; `shape.demo.json` reports `executed: true` and schema
match. All seven oracle columns are present with compatible types:
`subject_id`, `hadm_id`, `stay_id`, `antibiotic`, `route`, `starttime`, and
`stoptime`. The three additional columns `patient_key`, `encounter_key`, and
`icu_encounter_key` are the manifest-required resource-key columns and are
permitted presence-only extras. No incompatible types or unexpected columns
were reported.

Observed demo row count: 903. This is non-gating evidence; the demo was not
empty and row count is not a correctness gate.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
No implementation files were modified and no new dataset-wide quirk was
reported.
