## Evidence

The embedded Spark demo gate had already executed for attempt 0001 before the
runner's invocation; the runner's second invocation was correctly refused by
the write-once guard because `candidate.demo.parquet` and `shape.demo.json`
already existed. The existing artifacts record `executed: true` and
`verdict: shape_ok`.

The Parquet output has 579 demo rows (reported only, not gated), exactly the
24 oracle column names, and compatible types: INTEGER `stay_id`, TIMESTAMP
`charttime`, FLOAT numeric measures, VARCHAR string measures, and INTEGER
flags. `heparin_concentration` is all-null in demo but remains correctly typed
VARCHAR. The shape artifacts are:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0001/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0001/shape.demo.json`

This is a shape pass and permission to spend an HPC run, not a correctness
claim. No implementation artifact was changed.
