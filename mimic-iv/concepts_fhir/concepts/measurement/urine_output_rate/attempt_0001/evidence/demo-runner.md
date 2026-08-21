# Demo-runner evidence — `urine_output_rate`

`uv run mimic_utils run-demo urine_output_rate` completed successfully with
embedded Pathling 9.6.0 on Spark 4.0.2 over the local Delta warehouse. The
dependency views and both target ViewDefinitions registered, and
`concept.sql` executed.

The shape artifact reports `verdict: shape_ok`, execution true, no missing or
incompatible columns, and compatible manifest types for all 13 oracle columns.
The extra `icu_encounter_key` and `patient_key` columns are the required
manifest key columns. The observed demo row count was 7,317; it is explicitly
non-gating. Artifacts written were `candidate.demo.parquet` and
`shape.demo.json` in attempt 0001. This is permission to spend a full run,
not a correctness result.
