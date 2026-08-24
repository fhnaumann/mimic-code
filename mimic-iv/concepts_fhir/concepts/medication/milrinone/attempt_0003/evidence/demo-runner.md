# Demo shape-gate evidence — milrinone attempt 0003

- Executed `uv run mimic_utils run-demo milrinone` with embedded Pathling on
  Spark over the demo Delta warehouse.
- Verdict: `shape_ok`; execution succeeded with no errors.
- All six oracle columns matched by name and compatible type. The extra
  `icu_encounter_key` and `patient_key` columns are the manifest-declared key
  columns and were accepted by the shape gate.
- Demo row count was 15; this is reported only and was not gated.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
