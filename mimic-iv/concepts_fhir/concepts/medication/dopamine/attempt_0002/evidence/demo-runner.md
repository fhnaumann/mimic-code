# Demo runner evidence — dopamine attempt_0002

Ran `uv run mimic_utils validate-demo dopamine` followed by `uv run mimic_utils run-demo dopamine` using embedded Pathling 9.6.0 on Spark 4.0.2 over the demo Delta warehouse. Both ViewDefinitions registered and the SQL executed successfully.

The candidate produced 28 observed rows (row count is not gated). The six expected columns were present with compatible types: `stay_id` INTEGER, `linkorderid` INTEGER, `vaso_rate` FLOAT, `vaso_amount` FLOAT, `starttime` TIMESTAMP_NTZ, and `endtime` TIMESTAMP_NTZ. The shape verdict was `shape_ok`; this only permits the full-data run and does not establish correctness.

Artifacts checked:

- `candidate.demo.parquet`
- `shape.demo.json`
