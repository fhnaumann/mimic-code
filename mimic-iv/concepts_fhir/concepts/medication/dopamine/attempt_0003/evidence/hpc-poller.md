# HPC-poller evidence

- Concept: `dopamine`; attempt: `0003`; job `30231139`.
- Poll outcome: `complete`; the full job exited normally and fetched
  `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
- Comparator verdict: `review`, tier `gap_shaped`; schema matched and execution
  succeeded. `judge_required=true`, `diagnostician_required=false`.
- Keyed comparison key: `(stay_id, starttime)`.
- Row counts: oracle 16,892; candidate 16,892; delta 0 (reported, not gated).
- Divergence: `differing_null_only` on `linkorderid`, 16,892 rows; zero
  `only_oracle`, `only_candidate`, and `differing_conflict`; declaration was
  confirmed all-NULL. Representable identity: 16,892/16,892 (100%);
  overall identity is 0 only because the declared column differs.
- Slurm elapsed time: 26 seconds; job state `COMPLETED`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and
  `hpc_accounting.json` in this attempt. The candidate full Parquet remains on
  scratch per the artifact contract.
- Route: equivalence judge only; no diagnostician is required by the artifact.
