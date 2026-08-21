# Demo runner evidence — icustay_hourly

The current immutable attempt already had a successful embedded Pathling/Spark
demo execution from the implementer. A second `uv run mimic_utils run-demo
icustay_hourly` invocation was correctly refused by the write-once guard because
`candidate.demo.parquet` already exists; this is not a demo execution failure.

The existing `shape.demo.json` reports `executed: true`, `verdict: shape_ok`,
matching columns `stay_id`, `hr`, and `endtime`, no missing columns, no
incompatible types, and required opaque key columns `icu_encounter_key` and
`patient_key` present. Candidate types are `INTEGER`, `BIGINT`, and `TIMESTAMP`,
matching the manifest. The 15,615 demo rows versus 7,799,814 full-oracle rows
is informational only; row count is not gated.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/candidate.demo.parquet/`
- Attempt state: `mimic-iv/concepts_fhir/state/icustay_hourly/state.json`
