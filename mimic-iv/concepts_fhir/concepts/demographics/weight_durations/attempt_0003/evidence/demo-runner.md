# Demo-runner evidence

`uv run mimic_utils run-demo weight_durations` executed the embedded Pathling
9.6.0/Spark 4.0.2 path successfully after installing the pinned repository
`fhir` extra in the local environment (the first invocation only reported the
missing optional dependency). Both ViewDefinitions registered and
`concept.sql` ran, producing 578 Parquet rows.

The shape artifact reports `shape_ok`, `executed: true`, and compatible types:
`stay_id` INTEGER, `starttime`/`endtime` TIMESTAMP, `weight` DECIMAL(38,3), and
`weight_type` VARCHAR. All five manifest columns were present. The additive
`icu_encounter_key` and `patient_key` columns were present as the required
manifest key columns; they are not compared values. The row count is
informational and was not used as a gate.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/candidate.demo.parquet/`
