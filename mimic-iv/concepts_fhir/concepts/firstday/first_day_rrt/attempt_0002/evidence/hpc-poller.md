# HPC-poller evidence — `first_day_rrt`, attempt 0002

- What was run: `uv run mimic_utils hpc-poll first_day_rrt`, following Slurm
  job `30486380`.
- What was checked: completed Slurm outcome, full-data schema identity, and the
  keyed row-level comparison against the immutable oracle.
- Result: poll outcome `complete`; comparator verdict `match`. The keyed join on
  `stay_id` reproduced 73,181/73,181 rows identically (100%); row-count delta,
  missing/incompatible columns, and all divergence classes were zero.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and
  `hpc_accounting.json` in this attempt. Slurm elapsed time was 183 seconds.

No diagnostician or equivalence judge was required because the deterministic
full comparator returned an exact match.
