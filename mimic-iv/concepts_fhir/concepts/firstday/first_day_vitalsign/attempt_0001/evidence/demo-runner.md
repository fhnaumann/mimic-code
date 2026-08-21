# Demo runner evidence

`uv run mimic_utils run-demo first_day_vitalsign` executed successfully with
embedded Pathling 9.6.0 on Spark 4.0.2 over the demo Delta warehouse. The
shape verdict is `shape_ok`; all manifest data columns have compatible types,
and the required opaque `icu_encounter_key` and `patient_key` key columns are
present with the expected Type/id string shape. There are no missing columns,
unexpected non-key columns, or incompatible types.

The candidate produced 140 demo rows. This row count is reported only and was
not gated. The attempt may proceed to the full-data correctness run.

Artifacts written by the runner:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/shape.demo.json`
