# Evidence: demo-runner

Concept `invasive_line`, attempt `0001`.

The embedded Pathling-on-Spark demo shape gate executed successfully. `shape.demo.json` records `executed: true`, verdict `shape_ok`, and the contract note that this is only permission to spend an HPC run. Candidate Parquet contains 216 rows with columns `stay_id`, `line_type`, `line_site`, `starttime`, and `endtime`; names match the oracle shape and types are compatible: `INTEGER`, `VARCHAR`, `VARCHAR`, `TIMESTAMP`, `TIMESTAMP`. Row count is observed but not used as a correctness gate.

Artifacts inspected:
- `candidate.demo.parquet/`
- `shape.demo.json`

A subsequent mechanical rerun was correctly refused because the write-once `candidate.demo.parquet` already existed; this was not a gate failure and no artifact was replaced.
