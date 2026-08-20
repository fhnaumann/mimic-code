Evidence block — `first_day_bg_art`, attempt `0001`.

`uv run mimic_utils run-demo first_day_bg_art` executed successfully with embedded Pathling on Spark. The shape gate passed: all 44 manifest columns matched by name, required `patient_key` and `icu_encounter_key` were present, and all candidate types were compatible (INTEGER identifiers, DECIMAL(38,4) for the `aado2_calc` extrema, DOUBLE for other measures). The demo produced 140 rows; row count was reported only and was not used as a gate. No execution error occurred.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg_art/attempt_0001/`. No dataset-wide quirk was newly reported and no notes fragment entry was appended. The pass grants permission for the full-data run only; it does not establish correctness.
