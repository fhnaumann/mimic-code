# Demo runner evidence

Concept: `urine_output`; attempt `0001`.

Command: `uv run mimic_utils run-demo urine_output` using embedded Pathling on Spark over the demo Delta warehouse. Exit code `0`; both ViewDefinitions registered and `concept.sql` executed successfully.

Shape verdict: `shape_ok` / pass. Candidate columns exactly matched the oracle: `stay_id`, `charttime`, `urineoutput`. Compatible types were `int` vs INTEGER, `timestamp_ntz` vs TIMESTAMP, and `double` vs DOUBLE. No missing or extra columns and no incompatible types.

Observed demo row count was 7,317. Row count is explicitly not a demo gate; zero rows would be `unsure`, not failure. This non-zero count does not establish correctness.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/shape.demo.json`
