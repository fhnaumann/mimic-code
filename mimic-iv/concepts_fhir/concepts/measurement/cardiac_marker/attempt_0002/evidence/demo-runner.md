## Demo-runner evidence

Command: `uv run mimic_utils run-demo cardiac_marker`.

Attempt 2 executed successfully through embedded Pathling 9.6.0 on Spark. The shape gate reports `shape_ok`; all four ViewDefinitions registered and `concept.sql` completed without error. The seven output names exactly match the oracle: `subject_id`, `hadm_id`, `charttime`, `specimen_id`, `troponin_t`, `ck_mb`, `ntprobnp`. Candidate types `int, int, timestamp_ntz, int, double, double, double` are compatible with the manifest types. The demo produced 283 rows, which is informational only and not a gate.

Artifacts produced: `candidate.demo.parquet/` and `shape.demo.json` under `attempt_0002`. No implementation artifacts were edited and state remained at `VALIDATING_DEMO` until the orchestrator's full-data transition.
