# Demo shape gate evidence

Corrected attempt_0004 executed successfully with `uv run mimic_utils run-demo urine_output_rate` over embedded Pathling/Spark. The shape verdict is `shape_ok`; all 13 oracle columns and compatible types were present, with expected `icu_encounter_key` and `patient_key` key columns, and no missing or incompatible columns. The demo produced 7,317 rows, which is informational only and not gated.

Artifacts: `candidate.demo.parquet`; `shape.demo.json`.
