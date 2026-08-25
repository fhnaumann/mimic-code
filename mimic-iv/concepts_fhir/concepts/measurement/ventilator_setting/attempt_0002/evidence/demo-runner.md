Evidence block — demo-runner

Attempt_0002's embedded Spark demo execution had already produced the
write-once Parquet and shape artifact, so a second `uv run mimic_utils run-demo
ventilator_setting` was correctly refused because `candidate.demo.parquet`
exists. This refusal is not a shape failure.

The immutable `shape.demo.json` reports `executed: true`, `verdict:
shape_ok`, and 2,064 candidate rows. All 17 oracle columns are present with
compatible types; no columns are missing or incompatible. The required
`patient_key` and `icu_encounter_key` columns are present as VARCHAR resource
keys, and no required key is missing. Row count was observed but not gated.

Artifacts checked:
- `candidate.demo.parquet/`
- `shape.demo.json`
