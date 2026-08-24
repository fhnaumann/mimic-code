# Demo shape gate evidence

Concept: `bg`  
Attempt: `attempt_0008`  
Command: `uv run mimic_utils run-demo bg`

The replayed attempt executed successfully over embedded Pathling on Spark. The
27 oracle data columns are present with compatible types; `patient_key` and
`encounter_key` are also present as the manifest-declared required key columns.
There are no missing columns or incompatible types. The observed demo row count
is 889 and is not gated by contract (the full oracle has 511,637 rows).

Verdict: `shape_ok`; proceed to full data.

Produced artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`

No carried implementation artifacts were edited and no analysis or authoring
stage ran because this is a replayed attempt.
