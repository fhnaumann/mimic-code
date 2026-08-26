# Demo runner evidence — `first_day_sofa` attempt 0002

## Result

- `uv run mimic_utils run-demo first_day_sofa` executed cleanly with embedded Pathling 9.6.0/Spark over the demo Delta warehouse.
- Shape verdict: `shape_ok`; execution succeeded and all three ViewDefinitions plus `concept.sql` ran.
- All ten manifest columns were present with compatible IntegerType/INTEGER types; no missing or unexpected columns.
- `patient_key`, `encounter_key`, and `icu_encounter_key` were present as the required opaque key columns and are non-gating extras.
- Demo row count was 140, recorded only and not gated.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in attempt 0002.

## Evidence block

Read/checks: checked the first_day_sofa manifest entry and ran the sanctioned embedded Spark demo command once. Verified execution, names, types, required key columns, Parquet output, and shape artifact. No implementation artifacts, state, notes, or commit were modified by the runner.
