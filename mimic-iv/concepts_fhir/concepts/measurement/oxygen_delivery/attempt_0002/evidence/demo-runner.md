# Evidence: demo-runner

Concept: `oxygen_delivery`; attempt: `0002`.

`uv run mimic_utils run-demo oxygen_delivery` did not execute the ViewDefinitions or SQL. Embedded Spark failed during `JavaSparkContext` initialization because the local executor could not connect to the driver's file-fetch port (`Failed to connect ... Operation timed out`). No candidate parquet or shape artifact was produced, so no schema or row count was available. This is an infrastructure failure, not a port-derived shape verdict.

The first two invocations failed before execution because local Spark selected the host address `140.253.236.26` and the executor could not connect to the driver's file-fetch port. A retry with `SPARK_LOCAL_IP=127.0.0.1 SPARK_LOCAL_HOSTNAME=localhost` executed successfully.

Shape verdict: `shape_ok`. The nine candidate columns exactly matched the manifest names and had compatible types: `subject_id`/`stay_id` integer, `charttime` timestamp_ntz compatible with TIMESTAMP, flow columns float, and four device columns string compatible with VARCHAR. Demo row count was 1,154 and is non-gating. Full target count is 601,546.

Artifacts produced:

- `candidate.demo.parquet`
- `shape.demo.json`

The loopback retry changed no implementation artifacts, state, notes, carryover, or git.
