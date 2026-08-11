Evidence block — Demo shape gate for `height`, attempt `0001`.

Executed `uv run mimic_utils run-demo height` via embedded Pathling on Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`; exit code 0. Verdict: `shape_ok`, so the attempt may proceed to full data. Candidate columns `[subject_id, stay_id, charttime, height]` match the oracle manifest. Candidate types `int`, `int`, `timestamp_ntz`, `decimal(38,2)` are compatible with oracle `INTEGER`, `INTEGER`, `TIMESTAMP`, `DECIMAL(38,2)`. Demo candidate row count was 69 versus the full-oracle reference 33,474; this count was reported only and not gated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/candidate.demo.parquet` and `shape.demo.json`. Implementation artifacts were not modified and no commit was made.
