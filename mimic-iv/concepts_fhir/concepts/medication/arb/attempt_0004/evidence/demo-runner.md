# Evidence — demo-runner

Concept: `arb`; attempt: `0004`.

`uv run mimic_utils run-demo arb` completed successfully using embedded
Pathling on Spark 4.0.2 / Pathling 9.6.0. The candidate executed and registered
the six expected views. The five manifest columns
(`subject_id`, `hadm_id`, `arb`, `starttime`, `stoptime`) were all present with
compatible types; the required opaque `encounter_key` and `patient_key`
key-columns were also present. No incompatible types or missing columns were
reported. Demo row count was 35; it was observed only and not gated.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`

The shape verdict was `shape_ok` and explicitly permits the full-data run; it
does not establish semantic correctness. No implementation artifacts were
modified and no commit was made.
