# Demo-runner evidence — vitalsign, attempt 0003

The replayed attempt passed the embedded Pathling/Spark demo shape gate. `uv run mimic_utils run-demo vitalsign` executed the three carried ViewDefinitions and `concept.sql`, wrote `candidate.demo.parquet`, and produced `shape.demo.json` with `verdict: shape_ok`, `executed: true`, no missing columns, and no incompatible types. The 15 manifest columns were present; `patient_key` and `icu_encounter_key` were the declared resource-key columns. Demo row count was 21,086 and was not used as a correctness gate. No dataset-wide quirk was reported.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt directory.
