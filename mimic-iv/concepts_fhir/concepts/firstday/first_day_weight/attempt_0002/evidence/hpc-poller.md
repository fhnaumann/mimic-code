# HPC poller evidence — `first_day_weight`, attempt 0002

- Read/checked: existing `hpc_job.json` for job `30486471`; `uv run mimic_utils hpc-poll first_day_weight` polled to terminal completion and fetched the full comparison artifacts.
- Result: job outcome `complete`; deterministic comparator verdict `match`. Candidate and oracle each contain 73,181 rows; all 73,181 rows reproduced identically (100%). `only_oracle`, `only_candidate`, `differing_null_only`, `differing_conflict`, and `differing` are all zero. Schema and execution checks passed; no judge or diagnostician was required.
- Runtime: Slurm elapsed 81 seconds; execute 77.79 seconds and compare 1.22 seconds.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt.
