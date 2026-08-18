# Demo-runner evidence — blood_differential attempt 0003

The embedded Pathling-on-Spark demo shape gate executed successfully after
setting `SPARK_LOCAL_IP=127.0.0.1`; the earlier unconfigured invocation failed
only because Spark attempted to bind the unreachable hostname address. The
port itself executed and produced `candidate.demo.parquet`.

`shape.demo.json` reports `shape_ok` / `executed: true`. All 20 oracle columns
were present with compatible types: INTEGER identifiers, timestamp_ntz
`charttime`, DOUBLE measurements, and DECIMAL(38,4) rounded absolute values.
The three extra columns `patient_key`, `encounter_key`, and `specimen_key`
were classified as the manifest-required key columns. The 2,763 demo rows
are reported only; row count is not a gate and is not evidence of full-data
correctness.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
