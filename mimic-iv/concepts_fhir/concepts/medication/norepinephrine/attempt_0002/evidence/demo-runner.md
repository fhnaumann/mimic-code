# Demo evidence — norepinephrine attempt_0002

`uv run mimic_utils run-demo norepinephrine` executed the ViewDefinitions and
`concept.sql` with embedded Pathling on Spark over the local demo Delta
warehouse. The result was `shape_ok`: all six manifest columns were present,
with compatible INTEGER/FLOAT/TIMESTAMP types and no execution error. The two
extra columns, `icu_encounter_key` and `patient_key`, are the manifest-declared
required key columns and were present as required.

The demo produced 947 candidate rows. This count was observed only; row count
is not a demo gate. The output artifact is
`mimic-iv/concepts_fhir/concepts/medication/norepinephrine/attempt_0002/`:
`candidate.demo.parquet` and `shape.demo.json`.
