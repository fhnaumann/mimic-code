# HPC-poller evidence — vitalsign, attempt 0003

Slurm job `30485964` completed and the poller fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The full comparator returned `review`, tier `gap_shaped`, with `judge_required: true` and `diagnostician_required: false`. Schema matched; the oracle had 9,745,500 rows and the candidate 9,745,499, with one `only_oracle` row and no `only_candidate`, `differing_conflict`, or `differing_null_only` rows. The missing row is `(stay_id=34934165, charttime=2151-10-03 05:14:00, glucose=96)`. The keyed DST replay did not close this residual, so the result remains gap-shaped. Slurm elapsed time was 114 seconds. Row count was reported, not gated.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory.
