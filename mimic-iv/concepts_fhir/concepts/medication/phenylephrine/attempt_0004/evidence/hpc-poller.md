# HPC poller evidence

Concept: phenylephrine  
Attempt: 0004  
Slurm job: 30485281

The sanctioned full-data poll completed successfully after four polls. Slurm reported `COMPLETED` with 28 seconds elapsed, and the comparison artifacts were fetched. This was a completed job, not a crash or timeout.

The deterministic comparator returned `review`, not `match` or `mismatch`, with `divergence.tier = gap_shaped`, `judge_required = true`, and `diagnostician_required = false`. The schema matched. Candidate and oracle each had 193,260 rows; row count was reported but not gated. The unkeyed residual paired 1:1 on `(endtime, starttime, stay_id)`. There were no `only_oracle`, `only_candidate`, or `differing_conflict` rows. `differing_null_only` covered 193,260 rows: declared-unrepresentable `linkorderid` was NULL on all rows, and `vaso_rate` was NULL on one row. `identical_representable` was 193,259/193,260 (100.00%) after excluding the confirmed declared gap; raw identical was 0/193,260 because the declared column is NULL throughout. The comparator supplied no remaining diagnostician requirement, so the next stage is the equivalence judge.

Artifacts fetched under this attempt: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The full candidate parquet remains on scratch. No state transition, implementation edit, launch, or commit was performed by the poller.
