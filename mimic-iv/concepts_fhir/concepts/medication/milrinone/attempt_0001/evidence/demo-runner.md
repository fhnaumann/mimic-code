# Demo-runner evidence

`uv run mimic_utils run-demo milrinone` executed successfully with embedded Pathling on Spark over the local Delta warehouse. The shape verdict was `shape_ok`: output columns exactly matched `[stay_id, linkorderid, vaso_rate, vaso_amount, starttime, endtime]`, and normalized types were compatible (`int, int, float, float, timestamp_ntz, timestamp_ntz` versus the manifest's INTEGER/FLOAT/TIMESTAMP types). The demo produced 15 rows; this row count is observational only and was not gated.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` under `attempt_0001/`. The demo pass only permits the full-data run and does not establish correctness.
