# Demo runner evidence

Concept: `chemistry`
Attempt: `attempt_0005` (replay/data-rebuild attempt)

The demo runner executed `uv run mimic_utils run-demo chemistry` with embedded
Pathling on Spark. Execution succeeded. The shape gate was `shape_ok`: all 16
oracle columns were present with compatible types, and the required resource
key columns (`patient_key`, `encounter_key`, `specimen_key`) were emitted.
The demo returned 3,289 rows; row count is reported only and was not gated.

Artifacts produced: `candidate.demo.parquet` and `shape.demo.json` in the
attempt directory. This pass is only permission to proceed to full data.
