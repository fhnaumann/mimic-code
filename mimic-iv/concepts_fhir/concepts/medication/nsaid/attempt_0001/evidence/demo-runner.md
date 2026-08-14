# Evidence — demo-runner

Concept `nsaid`, attempt `0001`.

`uv run mimic_utils validate-demo nsaid` froze the implementation after lint
passed. `uv run mimic_utils run-demo nsaid` executed embedded Pathling on Spark
successfully and produced `shape_ok`. Candidate columns and compatible types
matched the manifest: `subject_id`, `hadm_id`, `nsaid`, `starttime`,
`stoptime`; 202 demo rows were observed, with row count treated as non-gating.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt
directory.
