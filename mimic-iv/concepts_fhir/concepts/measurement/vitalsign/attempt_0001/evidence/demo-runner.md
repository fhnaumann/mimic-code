## Evidence

`validate-demo` froze attempt `0001` successfully. The demo runner inspected the existing embedded-Spark artifacts because the implementer had already run the demo and the write-once guard refused a second `run-demo` execution. `shape.demo.json` records `executed: true`, `shape_ok`, 15 matching column names/types, and 21,084 candidate rows. Candidate Parquet types match the manifest: INTEGER identifiers, TIMESTAMP charttime, DOUBLE numeric outputs, DECIMAL(38,2) temperature, and VARCHAR temperature_site.

The second invocation's write-once refusal was an artifact guard, not a shape failure. Row count is recorded only as evidence; it is not a gate. Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/measurement/vitalsign/attempt_0001/`.
