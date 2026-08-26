# Demo-runner evidence

Concept: `oasis`; attempt: `0002`.

`uv run mimic_utils run-demo oasis` executed successfully with embedded
Pathling 9.6.0 / Spark 4.0.2 over the authoritative demo Delta. The shape
verdict was `shape_ok`: all 25 manifest columns were present with compatible
types, and the required `encounter_key`, `icu_encounter_key`, and
`patient_key` companion keys were present. No execution errors occurred.

The demo produced 140 rows; this count is informational and not gated. Fresh
artifacts are
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0002/candidate.demo.parquet/`
and `shape.demo.json`. The pass only permits the full-data run and does not
establish correctness.
