# Demo runner evidence — gcs attempt 0006

- The mandatory `uv run mimic_utils run-demo gcs` invocation was refused by the
  write-once guard because this frozen attempt already contained
  `candidate.demo.parquet` from the implementer's prior demo execution.
- The existing immutable gate record was independently verified: `shape.demo.json`
  reports `executed: true`, `match: true`, no missing or unexpected columns, and
  no incompatible types (`shape_ok`). Direct Parquet inspection confirmed the
  eight oracle columns with compatible types plus the required FHIR key columns
  `patient_key` and `icu_encounter_key`.
- Existing demo row count is 3,279. It is reported only; row count is not a gate.
  The zero-row unsure rule does not apply.
- No artifact was modified or replaced. The demo artifacts are
  `candidate.demo.parquet/` and `shape.demo.json` under attempt 0006.
- The re-run refusal is an immutable-artifact guard, not a port execution or
  schema failure. Full-data validation may proceed from the existing `shape_ok`
  record.
