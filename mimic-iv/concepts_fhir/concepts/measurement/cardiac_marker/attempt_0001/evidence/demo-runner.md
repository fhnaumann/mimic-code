## Demo-runner evidence

Command executed: `uv run mimic_utils run-demo cardiac_marker`.

The embedded Pathling/Spark run registered all four ViewDefinitions and derived a seven-column plan whose names and types matched the oracle manifest, but eager Parquet evaluation failed with `Unknown pattern letter: T`. The failure is in `concept.sql` at the `TRY_TO_TIMESTAMP` fallback pattern: SQL single-quote escaping removed the literal quotes around `T`, yielding `yyyy-MM-ddTHH:mm:ssXXX`. No `candidate.demo.parquet` or `shape.demo.json` was produced, and no row count was measured. This is an execution shape failure, not a row-count verdict. State remains `VALIDATING_DEMO`.

Artifacts: no new runner artifacts; diagnostic evidence is in the demo-runner result and the existing attempt implementation files.
