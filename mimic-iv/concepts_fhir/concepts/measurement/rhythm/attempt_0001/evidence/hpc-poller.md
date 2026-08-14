# HPC-poller evidence — rhythm

The existing job `29944380` was polled, not relaunched. Slurm completed it
successfully in 93 seconds. The embedded Pathling/Spark run and comparator
produced `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json`. The comparator returned `review`, tier `attributed`,
not `match` or `mismatch`: 5,872,983 of 5,873,723 oracle rows were identical;
95 value conflicts, 645 oracle-only rows, and 42 candidate-only rows were all
replayed to the upstream New York DST shift. The judge is required and the
diagnostician is not required.
