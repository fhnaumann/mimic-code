Evidence block — demo shape gate, `complete_blood_count`

- Attempt: `attempt_0003`.
- Verdict: `shape_ok` (exit code 0; gate message permits full data).
- Executed successfully with embedded Pathling on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`; four views registered and no execution errors.
- Column names matched all 14 oracle columns. The three extra columns `patient_key`, `encounter_key`, and `specimen_key` are declared resource key columns and were not unexpected.
- Types were compatible; `charttime` was `timestamp_ntz` and normalized against manifest `TIMESTAMP`.
- Candidate demo row count was 2,959 versus the full oracle's 3,362,503; row count is reported only and was not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in `mimic-iv/concepts_fhir/concepts/measurement/complete_blood_count/attempt_0003/`.

No implementation artifacts were edited and no semantic judgment was made.
