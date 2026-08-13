# Demo runner evidence

- Command: `uv run mimic_utils run-demo crrt`.
- Embedded Pathling on Spark executed both ViewDefinitions and `concept.sql` successfully.
- Shape verdict: `shape_ok`; all 24 expected columns were present with compatible types and no extras or omissions.
- Demo candidate row count: 579. Row count was observed only and was not gated.

Artifacts: `candidate.demo.parquet`, `shape.demo.json`.
