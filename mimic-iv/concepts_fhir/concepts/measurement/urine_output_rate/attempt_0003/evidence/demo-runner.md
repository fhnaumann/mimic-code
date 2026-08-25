# Demo shape gate evidence

The replayed attempt_0003 was executed with `uv run mimic_utils run-demo urine_output_rate` over the embedded Pathling/Spark demo warehouse. The carried `concept.sql` and ViewDefinitions were not edited. Execution succeeded and produced 7,317 demo rows (row count is informational only). The candidate returned all 13 oracle columns with compatible types, plus the required `icu_encounter_key` and `patient_key` key columns; no columns were missing and no types were incompatible. The shape verdict is `shape_ok`, so the attempt may proceed to full-data validation.

Artifact: `candidate.demo.parquet`; `shape.demo.json`.
