# HPC poller evidence

- Concept: `rrt`; attempt: `attempt_0005`; job: `30485855`.
- Outcome: `complete`; Slurm state `COMPLETED`; no crash or timeout.
- Comparator verdict: `match` (exit 0). The equivalence judge was correctly not called.
- Comparison mode: `full_tuple_multiset` for this unkeyed concept.
- Schema: exact and compatible; required key columns `icu_encounter_key` and `patient_key` present; no missing columns or incompatible types.
- Rows: oracle 2,827,715; candidate 2,827,715; delta 0. Row count is reported, not used as a gate.
- Diff: `only_oracle=0`, `only_candidate=0`, no differing values, no divergence tier, and no attribution or judge routing.
- Runtime: 180 seconds Slurm elapsed; `run_meta.full.json` recorded execute-plus-compare timing.
- Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in the attempt directory.
