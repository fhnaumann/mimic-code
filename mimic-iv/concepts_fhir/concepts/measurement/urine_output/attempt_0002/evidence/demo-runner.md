# Demo runner evidence

Concept: `urine_output`; attempt `0002`.

`uv run mimic_utils run-demo urine_output` completed successfully with embedded Pathling on Spark. Both ViewDefinitions registered, SQL executed, and candidate Parquet was written. Shape verdict: `shape_ok` (exit 0). Candidate columns exactly matched `stay_id`, `charttime`, `urineoutput`; types were compatible (`int`, `timestamp_ntz`, `double` against INTEGER, TIMESTAMP, DOUBLE), with no missing, extra, or incompatible columns.

The observed demo row count was 7,317 and is non-gating; demo row count is not correctness evidence and zero rows would be `unsure`, not failure.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0002/shape.demo.json`
