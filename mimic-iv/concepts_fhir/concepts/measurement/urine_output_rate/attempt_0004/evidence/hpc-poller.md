# Full-data poll and comparator evidence

Slurm job `30491678` completed successfully and its comparison artifacts were fetched. Attempt_0004 is an exact `match`: 3,321,747 candidate rows equal 3,321,747 oracle rows, with 100% identical rows. The keyed diff on `[stay_id, charttime]` has zero `only_oracle`, zero `only_candidate`, zero `differing_null_only`, and zero `differing_conflict` rows. The schema matches, and no judge or diagnostician is required.

Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
