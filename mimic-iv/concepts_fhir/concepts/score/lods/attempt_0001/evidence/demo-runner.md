# Demo-runner evidence — lods attempt_0001

`uv run mimic_utils run-demo lods` executed successfully using embedded
Pathling on Spark over the demo Delta warehouse. The shape verdict was
`shape_ok`; all ten oracle columns were present with compatible `INTEGER`
types, and the three required opaque companion keys were present. There were
no missing, incompatible, or unexpected columns. The candidate produced 140
demo rows; this row count was informational only and was not used as a gate.

Artifacts produced:

- `candidate.demo.parquet` under the attempt directory
- `shape.demo.json` with `verdict: shape_ok`

The demo pass only permitted the full-data run; it was not treated as evidence
of correctness.
