# Evidence: demo-runner — chemistry attempt 0004

Command: `uv run mimic_utils run-demo chemistry` using embedded Pathling on
Spark over the local demo Delta warehouse. The authoritative first invocation
executed all four ViewDefinitions and wrote the candidate Parquet; the
subsequent attempted invocation was refused by the write-once guard and did
not modify artifacts.

Result: `shape_ok`; execution succeeded. The shape artifact reports no missing
or unexpected manifest columns, no incompatible types, and all required key
columns (`patient_key`, `encounter_key`, `specimen_key`). The candidate has
3,289 demo rows. This row count is recorded only; row count is not a demo gate.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
- `state/chemistry/state.json` (status `VALIDATING_DEMO`)

The demo pass earns permission to spend a full-data run but is not evidence of
correctness. No implementation artifacts or notes fragments were modified.
