# Evidence: demo-runner

Concept: `cardiac_marker`; attempt `0004`.

The embedded Pathling-on-Spark demo execution succeeded. The shape verdict was
`shape_ok`: all seven manifest column names matched and types were compatible
(`INTEGER`, `TIMESTAMP`, and `DOUBLE` equivalents), with no execution errors.
The candidate returned 283 rows; row count was recorded only as evidence and
was not gated.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
