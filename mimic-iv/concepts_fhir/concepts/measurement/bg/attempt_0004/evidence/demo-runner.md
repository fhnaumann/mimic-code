# Evidence: demo-runner (`bg`, attempt_0004)

Outcome: `fail` at execution/SQL parse time. Ran `uv run mimic_utils run-demo bg`
using embedded Pathling on Spark over the demo Delta warehouse. Spark rejected
`CAST(specimen AS VARCHAR)` at `concept.sql:216` with
`DATATYPE_MISSING_SIZE`: Spark requires a length for `VARCHAR`. The candidate
did not execute, so no shape comparison was reached and row count is not
applicable.

No `shape.demo.json` or `candidate.demo.parquet` was produced. The existing
implementation artifacts remain unchanged in
`mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0004/`. The direct fix
is to replace the bare VARCHAR cast with a sized Spark-compatible type in a new
write-once attempt; no HPC run was spent.
