# Demo runner evidence

Attempt `0002` ran successfully with embedded Pathling on Spark. Shape verdict
was `shape_ok`; columns matched exactly and types were compatible
(`int, int, timestamp_ntz, int, double` against the manifest). Demo returned
42 rows, reported only and not gated. Artifacts are `candidate.demo.parquet/`
and `shape.demo.json` in attempt `0002`.
