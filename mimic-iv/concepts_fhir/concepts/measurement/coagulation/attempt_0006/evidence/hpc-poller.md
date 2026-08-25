## Evidence

- Read: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` for replayed attempt `attempt_0006`.
- Checked: embedded Pathling/Spark execution completed; schema identity; keyed diff on natural key `specimen_id`; all divergence classes and required judge/diagnostician flags; Slurm accounting.
- Result: full-data comparator verdict `match`. Candidate and oracle each contain 1,543,003 rows; 1,543,003 identical, zero only-candidate, only-oracle, conflict, or null-only rows; schema matched with no incompatible types. No judge or diagnostician was required. Slurm job `30484151` completed in 99 seconds.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json` under this attempt.
