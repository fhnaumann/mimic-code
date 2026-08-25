# Demo-runner evidence — `first_day_rrt`, attempt 0002

- What was run: `uv run mimic_utils run-demo first_day_rrt`.
- What was checked: embedded Pathling on Spark execution, expected column names,
  and compatible types against `oracle_manifest.full.json`.
- Result: execution succeeded with `shape_ok`; the five expected columns were
  present and type-compatible. The two declared resource-key columns were also
  present. Demo row count was 140 and was observed only, not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.

The demo gate passed and permits the full-data gate; it does not establish
correctness.
