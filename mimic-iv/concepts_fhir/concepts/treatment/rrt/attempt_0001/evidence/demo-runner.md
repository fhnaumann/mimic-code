## Evidence

`uv run mimic_utils run-demo rrt` executed embedded Pathling on Spark and
returned `shape_ok`. The candidate columns exactly matched
`[stay_id, charttime, dialysis_present, dialysis_active, dialysis_type]`; all
types were compatible with the oracle manifest. The demo produced 5,130 rows,
which is reported only and was not used as a gate.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
