# Demo runner evidence — gcs

`uv run mimic_utils validate-demo gcs` froze the implementation and moved the
concept to `VALIDATING_DEMO`. Embedded Pathling on Spark then executed the
three ViewDefinitions and SQL successfully.

The shape verdict is `shape_ok`: all eight expected column names match and
types normalize compatibly (`INTEGER`, `TIMESTAMP`, `FLOAT`). The demo produced
3,279 rows; this row count is observational only and was not used as a gate.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`

Both are under
`mimic-iv/concepts_fhir/concepts/measurement/gcs/attempt_0005/`.
