## Demo runner evidence

Concept `sofa`, attempt `0002`. `uv run mimic_utils run-demo sofa` executed
successfully with embedded Pathling on Spark and returned `shape_ok` (exit
code 0). All 29 oracle columns were present with no missing or unexpected
columns; the two extra columns, `icu_encounter_key` and `patient_key`, are the
manifest-required key columns. All types were compatible and
`incompatible_types` was empty.

The demo produced 12,255 rows. This is observational only; row count is not a
demo gate. The gate result is `MAY PROCEED TO FULL DATA`.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under
`mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0002/`. No implementation
artifact, state transition, full run, or commit was modified by the runner.
