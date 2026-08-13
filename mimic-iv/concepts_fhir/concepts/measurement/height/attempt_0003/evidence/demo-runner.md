# Evidence — demo-runner

Executed `uv run mimic_utils run-demo height` using embedded Pathling on Spark.
The three ViewDefinitions and SQL executed successfully. Candidate columns
exactly matched the oracle shape (`subject_id`, `stay_id`, `charttime`,
`height`), with compatible types `int`, `int`, `timestamp_ntz`, and
`decimal(38,2)`. The shape verdict was `shape_ok`; demo row count was 69 and
was not used as a gate.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
