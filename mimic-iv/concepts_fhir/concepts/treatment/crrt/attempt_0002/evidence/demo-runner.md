## Evidence

Attempt 0002's embedded Spark demo artifacts already existed when the demo
runner was invoked, so the write-once guard refused a second execution. The
existing `shape.demo.json` records `executed: true` and `verdict: shape_ok`,
and the Parquet was independently checked.

The shape matches all 24 oracle column names with no missing or extra columns.
All types are compatible: INTEGER `stay_id`, TIMESTAMP `charttime`, FLOAT
numeric measures, VARCHAR string measures, and INTEGER flags. The candidate
has 580 demo rows; this count is reported only and is not a gate.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0002/shape.demo.json`
