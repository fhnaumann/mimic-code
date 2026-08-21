# Demo runner — kdigo_uo attempt_0003

Command: `uv run mimic_utils run-demo kdigo_uo` (embedded Pathling on Spark
over the demo Delta warehouse; no HTTP server).

## Verdict: shape_ok

- **Executed**: yes. ViewDefinitions `urine_output`, `weight_durations`, and
  `icu_encounter` registered; `concept.sql` ran to completion.
- **Row count**: 7,317 — **observation, not gated** (non-zero, so gate is
  `shape_ok`, not `unsure`).
- **Column names**: all 12 expected oracle columns present and matching;
  only `icu_encounter_key`, `patient_key` extra (the manifest key columns,
  legitimately carried as opaque ids).
- **Column types**: all compatible; `incompatible_types` is empty. The
  DECIMAL(38,3)/(38,4)/(38,6) and DOUBLE columns match manifest exactly, and
  the `uo_rt_*` / `uo_tm_*` all-null-on-demo columns arrived at the gate as
  the declared DECIMAL types (Parquet schema not re-inferred).

## Artifacts produced

- `candidate.demo.parquet` (Parquet, 7,317 rows)
- `shape.demo.json` (verdict `shape_ok`, schema.match true)
- `evidence/demo-runner.md` (this file)

No implementation artifacts were edited; no git commit made.