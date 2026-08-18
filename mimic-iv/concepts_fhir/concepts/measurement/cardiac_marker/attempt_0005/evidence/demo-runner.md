Evidence block

- Concept: `cardiac_marker`
- Attempt: `0005`
- Verdict: `shape_ok` — embedded Pathling on Spark executed, column names match, and types are compatible.
- Column names: all seven oracle columns match; missing none; `patient_key`, `encounter_key`, and `specimen_key` are the manifest-declared key columns and were not treated as unexpected extras.
- Types: compatible; `timestamp_ntz` is accepted for oracle `TIMESTAMP`, and integer/double columns align.
- Row count: 283 demo rows, observation only and not gated.
- The first invocation failed environmentally with `java.net.BindException: Can't assign requested address: Service 'sparkDriver' failed after 16 retries`; rerun with `SPARK_LOCAL_IP=127.0.0.1` succeeded without changing implementation artifacts.

Artifacts written: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/cardiac_marker/attempt_0005/`.
