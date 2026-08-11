## Evidence

Attempt 0003 passed the demo shape gate with
`uv run mimic_utils run-demo icustay_detail` using embedded Pathling 9.6.0 on
Spark 4.0.2.

All three ViewDefinitions registered and SQL executed cleanly. The candidate
returned exactly the 18 manifest columns, with no missing or extra names and
no incompatible types. Types matched the expected INTEGER, VARCHAR, DATE,
TIMESTAMP_NTZ, BIGINT, SMALLINT, BOOLEAN, and DECIMAL(38,2) categories.

The demo returned 140 rows versus 73,181 full oracle rows; this was an
observation only and was not gated. Shape verdict: `shape_ok`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0003/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0003/shape.demo.json`
