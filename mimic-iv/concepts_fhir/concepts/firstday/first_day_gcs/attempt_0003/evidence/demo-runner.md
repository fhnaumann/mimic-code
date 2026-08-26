# Demo runner evidence — `first_day_gcs`, attempt 0003

`uv run mimic_utils run-demo first_day_gcs` executed successfully through
embedded Pathling on Spark, with no HTTP server. The `patient`,
`icu_encounter`, and preprocessed `gcs` views registered and `concept.sql`
completed without error.

The candidate produced 140 rows. This count is observation only and was not
used as a gate; the full oracle has 73,181 rows. The seven oracle columns were
all present with compatible types: `subject_id`, `stay_id`, `gcs_min`,
`gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable`. The required opaque
key companions `patient_key` and `icu_encounter_key` were also present. No
columns were missing and `incompatible_types` was empty. The shape verdict was
`shape_ok`, so the attempt is authorized for the full-data gate.

Artifacts produced:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003/candidate.demo.parquet/`
