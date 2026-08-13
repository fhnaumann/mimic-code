# Evidence: hpc-poller

Concept `invasive_line`, attempt `0001`, full run `1`, job `29786620`.

The poll outcome was `complete`; Slurm completed in 24 seconds and the embedded Pathling/Spark runner produced a fresh comparison. Schema matched all five columns and types. Candidate and oracle both had 93,378 rows; row count was observed but not gated. There were 92,714 identical rows and 664 residual-paired `differing_conflict` rows: `line_site` 657, `starttime` 7, `endtime` 1. The comparator attributed 7 starttime rows to an upstream DST cast but left 657 residual conflicts, so the verdict was `review`, tier `contested`, with both diagnostician and judge required.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
