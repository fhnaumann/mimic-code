## Demo runner evidence

Concept `sofa`, attempt `0001`. The embedded Pathling-on-Spark demo execution
completed successfully and registered the derived dependency views. The shape
artifact reports `verdict: "shape_ok"`, `executed: true`, `schema.match: true`,
with no incompatible types or missing columns.

All 29 oracle columns were present in order. The two additional string columns,
`icu_encounter_key` and `patient_key`, are the manifest-required provenance
`key_columns` and are accepted by the shape gate. Types were compatible:
integer score/id columns, bigint `hr`, timestamp_ntz time columns, doubles for
numeric measurements, and float medication/GCS values. Demo output contained
12,255 rows; row count is observational only and was not gated.

Result: `Shape gate: SHAPE OK` / may proceed to full data. Artifacts:
`mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001/candidate.demo.parquet/`
and `.../shape.demo.json`. No implementation artifact or state transition was
modified by the runner.
