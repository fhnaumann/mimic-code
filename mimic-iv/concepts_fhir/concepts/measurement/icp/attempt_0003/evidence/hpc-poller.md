Evidence block

The full-data job `29853813` completed successfully and the comparison was
fetched. The schema matched. Verdict: `review`, tier `contested`, with
`judge_required: true` and `diagnostician_required: true`.

Reported counts: oracle 173,273; candidate 173,258; identical 173,252
(99.99%); 17 `only_oracle`, 2 `only_candidate`, and 4 `differing_conflict`
rows on `icp`. The comparison notes that two of the 17 oracle-only rows
re-pair under a DST key replay, but attribution was not attempted for a
datetime output and 15 residual oracle-only rows remain. Slurm completed in
84 seconds.

Artifacts: `hpc_job.json`, `hpc_accounting.json`, `comparison.full.json`, and
`run_meta.full.json`.
