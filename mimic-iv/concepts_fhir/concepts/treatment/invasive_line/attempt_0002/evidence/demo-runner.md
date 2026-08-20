# Demo-runner evidence — invasive_line attempt_0002

- Ran `uv run mimic_utils run-demo invasive_line` using embedded Pathling on
  Spark; no HTTP server was used.
- Execution succeeded and the shape verdict was `shape_ok`.
- The five manifest columns were present with compatible types: `stay_id`
  INTEGER, `line_type` VARCHAR, `line_site` VARCHAR, `starttime` TIMESTAMP,
  and `endtime` TIMESTAMP. Required opaque key columns `icu_encounter_key` and
  `patient_key` were also present; no key columns were missing.
- The demo produced 216 rows. This row count was reported only and was not a
  gate, as required by the loop contract.
- No implementation artifacts were edited and no errors occurred.

Artifacts:

- `candidate.demo.parquet/`
- `shape.demo.json`
