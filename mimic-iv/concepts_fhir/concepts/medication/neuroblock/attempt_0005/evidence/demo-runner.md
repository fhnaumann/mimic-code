# Demo-runner evidence — neuroblock attempt 0005

Command: `uv run mimic_utils run-demo neuroblock`.

Embedded Pathling on Spark executed both ViewDefinitions and `concept.sql`
cleanly over the local demo Delta warehouse. The candidate emitted all six
manifest columns with compatible types and the required additive keys
`icu_encounter_key` and `patient_key`; no expected columns were missing and
there were no incompatible types. The demo row count was zero, so the shape
verdict is `unsure`, not failure, and the attempt may proceed to full data.

Artifacts produced: `shape.demo.json` and `candidate.demo.parquet/` in this
attempt directory. The shape artifact records `schema.match: true` and
`incompatible_types: []`.
