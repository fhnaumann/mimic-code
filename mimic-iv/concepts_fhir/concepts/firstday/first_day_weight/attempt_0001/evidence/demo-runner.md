Evidence block

`uv run mimic_utils run-demo first_day_weight` completed successfully using
embedded Pathling 9.6.0 on Spark 4.0.2 over the local Delta warehouse. The
candidate executed with `weight_durations`, `icu_encounter`, and `patient`
views registered. All six manifest columns were present with compatible types:
INTEGER/INTEGER, DOUBLE/DOUBLE, and DECIMAL(38,3)/DECIMAL(38,3); the required
`icu_encounter_key` and `patient_key` key columns were also present. There were
no execution or schema errors. The demo returned 140 rows, recorded only as
observation and not used as a correctness gate.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in
`mimic-iv/concepts_fhir/concepts/firstday/first_day_weight/attempt_0001/`.
Verdict: `shape_ok`; proceed to full-data validation. No authored artifact was
modified and no commit was made.
