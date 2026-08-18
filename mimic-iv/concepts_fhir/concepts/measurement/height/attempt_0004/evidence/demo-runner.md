# Demo-runner evidence

The embedded Pathling-on-Spark demo execution succeeded. All three
ViewDefinitions registered, `concept.sql` executed, and
`candidate.demo.parquet` plus `shape.demo.json` were written. The shape
verdict is `shape_ok`: compared columns and types match the manifest, with
`patient_key` and `icu_encounter_key` present as required key columns.

Observed demo row count was 69. Row count is reported only and was not gated.
The candidate types were compatible: INTEGER, INTEGER, TIMESTAMP_NTZ, and
DECIMAL(38,2). No missing or incompatible columns were reported. A subsequent
identical invocation was refused by the write-once guard because the demo
Parquet already existed; this is not a gate failure.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/shape.demo.json`
