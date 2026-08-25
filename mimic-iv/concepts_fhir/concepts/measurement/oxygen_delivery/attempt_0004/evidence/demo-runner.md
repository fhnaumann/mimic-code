# Demo runner evidence

- Concept: `oxygen_delivery`, attempt `0004`.
- Read: `LOOP_CONTRACT.md`, the authoritative oxygen_delivery entry in `oracle/oracle_manifest.full.json`, and the replayed attempt's `concept.sql`, ViewDefinitions, and `replay_provenance.json`.
- Checked: `uv run mimic_utils run-demo oxygen_delivery` using embedded Pathling on Spark.
- Result: `shape_ok`; execution succeeded, all 9 manifest columns matched, declared resource-key columns were present, and all types were compatible. Candidate demo row count was 1,154; row count was observed but not gated.
- Artifacts: `candidate.demo.parquet/` and `shape.demo.json` in this attempt.
