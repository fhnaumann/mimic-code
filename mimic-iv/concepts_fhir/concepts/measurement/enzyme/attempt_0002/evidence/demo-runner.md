## Evidence

Command: `uv run mimic_utils run-demo enzyme` from the repository root.

Embedded Pathling on Spark executed all four ViewDefinitions and `concept.sql` successfully (exit 0). The shape gate is `shape_ok` / `pass`: all 15 oracle column names match, with no missing or extra columns, and every candidate type is compatible with the manifest (`charttime` is `timestamp_ntz`; identifiers are integer; analytes are double). Demo row count is 1,411 and is informational only; it was not used as a gate.

Produced artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0002/shape.demo.json`

This is a shape-only pass and permits, but does not establish, full-data correctness. No implementation artifact was edited and no HPC run was performed.
