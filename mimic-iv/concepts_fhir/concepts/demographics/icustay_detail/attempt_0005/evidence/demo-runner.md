# Demo runner evidence — `icustay_detail`

The replayed attempt 0005 executed successfully with embedded Pathling on Spark
(exit 0). The shape gate reported `shape_ok`: all 18 manifest columns were
present with compatible types and no incompatible types. The three additive
columns `encounter_key`, `icu_encounter_key`, and `patient_key` are the
manifest-declared key columns. The observed demo row count was 140 versus the
full oracle's 73,181; row count is non-gating. No execution errors occurred.

Artifacts produced:

- `candidate.demo.parquet`
- `shape.demo.json`

The implementation artifacts were not edited; this is a data-rebuild replay
carried byte-identically from attempt 0004.
