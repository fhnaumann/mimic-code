## Evidence

HPC job `29952933` completed and produced a fetched comparison, so the outcome was `complete`, not a queue-exit crash. The full comparator returned `review`, tier `contested`, with schema identity across all 15 columns. Oracle rows: 9,745,500; candidate rows: 9,744,737; identical rows: 9,743,636 (99.98%).

Divergence: 1,106 `only_oracle`, 343 `only_candidate`, and 758 `differing_conflict`. All 758 conflicts replay exactly to the upstream `America/New_York` `TIMESTAMPTZ` DST transformation, with zero residual conflict rows and citations in `comparison.full.json`. Key attribution explains 1,105/1,106 oracle-only rows and all 343 candidate-only rows through the same shift, leaving one unexplained oracle-only residual. The comparator requires both diagnostician and judge for this contested review. Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`; Slurm elapsed time was 116 seconds.
