# Demo-runner evidence — crrt attempt_0008

This was a data-rebuild replay. `concept.sql` and both ViewDefinitions were
carried forward byte-identically from attempt_0007 and were not edited.

- Command: `uv run mimic_utils run-demo crrt`.
- Embedded Pathling on Spark executed successfully (exit code 0).
- Shape verdict: `shape_ok` / `match: true`.
- All 24 oracle columns were present; the two manifest key columns
  (`icu_encounter_key`, `patient_key`) were tolerated as required extras.
- No incompatible types were reported: INTEGER/int, TIMESTAMP/timestamp_ntz,
  VARCHAR/string, and FLOAT/float were compatible.
- Demo row count was 580; this is informational and not a gate.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt.

The demo shape gate passed, so the replay may proceed to full-data validation.
