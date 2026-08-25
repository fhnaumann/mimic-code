# Demo shape gate evidence

- Concept: `invasive_line`
- Attempt: `0003` (replay of attempt 0002; carried artifacts were not edited)
- Ran: `uv run mimic_utils run-demo invasive_line`
- Result: `shape_ok`; embedded Pathling on Spark executed successfully and may proceed to full data.
- Candidate columns matched the oracle columns: `stay_id`, `line_type`, `line_site`, `starttime`, `endtime`.
- Required FHIR-side key columns `icu_encounter_key` and `patient_key` were present; no unexpected columns.
- Types were compatible: integer, strings, and timestamp values as required.
- Informational demo row count: 216; row count was not used as a gate.
- Artifacts: `candidate.demo.parquet`, `shape.demo.json`.
