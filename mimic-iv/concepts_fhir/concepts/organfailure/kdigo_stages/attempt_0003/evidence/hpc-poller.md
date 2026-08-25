# Full-data comparison evidence

- Concept: `kdigo_stages`
- Attempt: `attempt_0003`
- Job: Slurm `30486771`; outcome `complete`, Slurm state `COMPLETED`, elapsed 466 seconds.
- Comparator verdict: `match`.
- Execution/schema: executed with embedded Pathling on Spark; schema matched with no missing, unexpected, or incompatible columns. The three resource key columns are present as required.
- Comparison mode: `full_tuple_multiset` (no unique natural key).
- Rows: candidate 4,011,255; oracle 4,011,255; delta 0. Row count is reported, not the correctness gate.
- Diff: `only_oracle=0`, `only_candidate=0`, no conflicts or null-only differences; no residual remained.
- Divergence: tier `none`; no judge or diagnostician required or called.
- Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in the attempt root.

The replayed SQL and ViewDefinitions remained byte-identical. One full run was consumed.
