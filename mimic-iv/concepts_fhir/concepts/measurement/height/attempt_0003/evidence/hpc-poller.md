# Evidence — hpc-poller

Polled Slurm job `29856327` to completion. The poll outcome was `complete`,
with `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`
fetched/written. The comparator returned `review`, tier `attributed`, with
`judge_required: true` and `diagnostician_required: false`.

Full comparison: schema exact; oracle and candidate each 33,474 rows; 33,472
identical. The only divergence was 2 `differing_conflict` rows on `charttime`
(0.006%), both fully replayed as the upstream New York `TIMESTAMPTZ`
spring-forward normalization, with zero residual conflicts. The cited ETL
provenance must still be confirmed by the equivalence judge. Slurm elapsed time
was 118 seconds.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
