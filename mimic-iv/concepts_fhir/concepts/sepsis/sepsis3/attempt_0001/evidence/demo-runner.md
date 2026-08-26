Concept `sepsis3`; attempt_0001 demo shape gate.

`uv run mimic_utils run-demo sepsis3` completed successfully through embedded
Pathling on Spark over the demo Delta warehouse; no HTTP server was used. The
dependency views were preprocessed in DAG order, the ViewDefinitions
materialized, and `concept.sql` executed.

Shape verdict: `shape_ok` / `match: true`. All 14 oracle columns are present,
with the required manifest `key_columns` `icu_encounter_key` and `patient_key`
also present. The extra columns are expected key outputs; there are no missing
columns or incompatible types. Oracle INTEGER/TIMESTAMP/BOOLEAN correspond to
candidate int/timestamp_ntz/boolean.

Demo row count was 61 versus the full-oracle count 32,971; row count was
reported only and not gated. The gate explicitly permits proceeding to full
data.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/sepsis/sepsis3/attempt_0001/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/sepsis/sepsis3/attempt_0001/shape.demo.json`

No existing artifact was edited and no note was appended.
