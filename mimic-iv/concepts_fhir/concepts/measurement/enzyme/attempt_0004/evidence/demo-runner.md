# Demo runner evidence — enzyme attempt_0004

- Read: the replayed attempt artifacts and oracle shape manifest.
- Checked: `uv run mimic_utils run-demo enzyme` using embedded Pathling on Spark.
- Result: execution succeeded with exit code 0 and shape verdict `shape_ok`.
- All 15 oracle columns were present with compatible types; the three manifest FHIR key columns (`patient_key`, `encounter_key`, `specimen_key`) were extra non-gating outputs. No columns were missing or type-incompatible.
- Demo row count was 1,411 and was informational only, not a gate.
- Produced: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
