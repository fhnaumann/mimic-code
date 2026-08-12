# Demo runner evidence

`uv run mimic_utils run-demo inflammation` completed successfully using
embedded Pathling on Spark. The four ViewDefinitions and `concept.sql`
executed cleanly. The shape verdict was `shape_ok`: output columns
`[subject_id, hadm_id, charttime, specimen_id, crp]` matched the manifest and
types `int, int, timestamp_ntz, int, double` were compatible with
`INTEGER, INTEGER, TIMESTAMP, INTEGER, DOUBLE`. The 42-row demo count is
reported only and was not gated.

Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt.
