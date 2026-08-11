# HPC poller evidence — dopamine attempt_0002

Job `29725936` completed successfully according to Slurm accounting in 28 seconds, and the poller fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The full comparator returned `review`, tier `gap_shaped`, with `judge_required: true` and `diagnostician_required: false`.

The candidate and oracle each had 16,892 rows and identical schemas. All 16,892 divergences were `differing_null_only` on the declared `linkorderid` column; there were no only-oracle, only-candidate, or conflicting rows. Representable columns reproduced identically on all 16,892 rows (100%). The typed NULL declaration was confirmed. Row count was reported, not used as a correctness gate.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
