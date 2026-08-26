# Demo-runner evidence

Concept: `apsiii`, attempt `0002`.

Command: `uv run mimic_utils run-demo apsiii`.

The embedded Pathling-on-Spark demo run completed successfully with exit code
0. The shape verdict is `shape_ok`; all 21 oracle content columns are present
with compatible integer/double types, and the three additional columns
`encounter_key`, `icu_encounter_key`, and `patient_key` are the manifest's
declared FHIR key columns. No incompatible or missing columns were reported.

The demo produced 140 rows. This is an observation only: row count is not a
demo gate and is not evidence of full-data correctness. No semantic or
terminal decision was made.

Artifacts:
- `candidate.demo.parquet/`
- `shape.demo.json`

Routine Spark/Pathling warnings were non-fatal. No dataset-wide quirk was
reported or appended by this stage.
