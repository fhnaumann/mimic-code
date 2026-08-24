## Evidence — demo-runner, acei attempt 0007

Ran `uv run mimic_utils run-demo acei` from the repository root against the
replayed attempt. The ViewDefinitions and `concept.sql` executed successfully
with embedded Pathling on Spark, and the runner wrote the demo Parquet output.

The machine shape verdict was `shape_ok` (`schema.match: true`), with no
missing columns and compatible types for `subject_id`, `hadm_id`, `acei`,
`starttime`, and `stoptime`. The detail reported `patient_key` and
`encounter_key` as extra columns; these are the manifest-declared key columns
used by the full comparison. The CLI nevertheless authorized proceeding to
full data. Demo row count was 107 and was not used as a gate.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
