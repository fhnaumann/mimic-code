## Evidence

The attempt 0003 demo gate ran fresh with embedded Pathling on Spark and
exited successfully. `shape.demo.json` records `executed: true`,
`verdict: shape_ok`, and `schema.match: true`.

The candidate Parquet has exactly the 24 manifest columns with compatible
types: INTEGER identifiers/flags, TIMESTAMP `charttime`, FLOAT numeric
measures, and VARCHAR string measures. It contains 580 demo rows; row count
is reported only and is not a gate. No errors occurred and no implementation
files were modified.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0003/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0003/shape.demo.json`
