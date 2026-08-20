# Demo-runner evidence — vitalsign, attempt 0002

`uv run mimic_utils run-demo vitalsign` executed successfully with embedded Pathling 9.6.0 on Spark/PySpark 4.0.2 over the local demo Delta warehouse. All three ViewDefinitions registered and `concept.sql` wrote `candidate.demo.parquet` and `shape.demo.json`.

The shape artifact reports `shape_ok`: all 15 oracle columns are present, the sanctioned `patient_key` and `icu_encounter_key` extras are present, no key columns are missing, and `incompatible_types` is empty. `charttime` is `timestamp_ntz` and `temperature` is `decimal(38,2)`, both compatible with the manifest. The artifact reports 21,084 candidate demo rows; row count was explicitly non-gating. The final runner prose also mentioned 21,067, but `shape.demo.json` is the authoritative machine artifact and the discrepancy has no gate effect.

Artifacts:

- `candidate.demo.parquet/`
- `shape.demo.json`
