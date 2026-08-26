# Demo-runner evidence

Concept: `oasis`; attempt: `0001`.

`uv run mimic_utils run-demo oasis` executed successfully with embedded
Pathling 9.6.0 / Spark 4.0.2 over the authoritative demo Delta warehouse.
The runner preprocessed the completed dependency views in DAG order and the
candidate executed without SQL or ViewDefinition errors.

The shape gate verdict was `shape_ok`: all 25 oracle columns were present with
compatible types and no columns were missing. The required companion keys
`encounter_key`, `icu_encounter_key`, and `patient_key` were also present and
accepted as manifest key columns. The candidate produced 140 demo rows; row
count was informational and not gated.

Artifacts produced once:
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0001/candidate.demo.parquet/`
and
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0001/shape.demo.json`.
This pass only permits the HPC full-data run and does not establish
correctness.
