Evidence block:

Concept: neuroblock
Attempt: 0002

`uv run mimic_utils run-demo neuroblock` executed successfully using embedded Pathling on Spark. The shape verdict was `unsure` because the demo returned 0 rows; this is not a failure. The schema matched exactly: `stay_id, orderid, drug_rate, drug_amount, starttime, endtime`, with compatible `int, int, float, float, timestamp_ntz, timestamp_ntz` types. No missing or extra columns and no incompatible types were reported.

Produced artifacts:
- `candidate.demo.parquet/`
- `shape.demo.json`

The run reported permission to proceed to full data. No implementation artifacts were modified.
