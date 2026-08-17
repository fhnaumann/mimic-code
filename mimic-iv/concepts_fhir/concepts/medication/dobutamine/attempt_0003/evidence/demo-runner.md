# Demo runner evidence

- Concept: `dobutamine`
- Attempt: `0003`
- Command: `uv run mimic_utils run-demo dobutamine`
- Result: `shape_ok` (exit 0), executed through embedded Pathling on Spark.
- Schema: all six oracle columns matched with compatible types; required key columns `patient_key` and `icu_encounter_key` were present.
- Row count: 44, recorded only and not gated; the full oracle has 8,513 rows.
- No execution errors or incompatible types were reported. This is permission to spend a full-data run, not a correctness result.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt directory.
