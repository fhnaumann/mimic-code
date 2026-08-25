# Demo runner evidence

Concept: `complete_blood_count`
Attempt: `attempt_0004` (replay/data rebuild)

Command: `uv run mimic_utils run-demo complete_blood_count`

The embedded Pathling-on-Spark demo execution completed successfully. The shape
gate returned `shape_ok`; all oracle columns were present with compatible types,
and the required resource-key columns were present. The reported 2,959 rows
are informational only and were not used as a gate.

Artifacts:

- `candidate.demo.parquet/`
- `shape.demo.json`

No implementation artifacts were edited and no full-data run was performed in
this stage.
