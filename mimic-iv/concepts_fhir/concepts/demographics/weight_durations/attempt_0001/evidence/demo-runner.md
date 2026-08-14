# Demo-runner evidence

`uv run mimic_utils run-demo weight_durations` executed successfully with embedded Pathling/Spark. The shape gate reported `shape_ok`: all five columns matched the oracle names and compatible types, with no missing, extra, or incompatible columns. Returned columns were `stay_id` integer, `starttime`/`endtime` timestamp_ntz, `weight` decimal(38,3), and `weight_type` string. The demo produced 578 rows; row count was recorded only and was not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0001/`. This pass is a shape gate only and does not establish correctness.
