## Evidence

- Concept: `blood_differential`, attempt_0004; Slurm job `30483916`.
- Ran: `uv run mimic_utils hpc-poll blood_differential`.
- Poll outcome: `complete`; Slurm state `COMPLETED`, elapsed 105 seconds.
- Full comparator verdict: `match`. Keyed comparison on `specimen_id` reproduced 3,171,906/3,171,906 rows identically; `only_oracle`, `only_candidate`, `differing_null_only`, and `differing_conflict` were all zero. Schema matched and row count was reported, not gated.
- No judge or diagnostician was required because the comparator returned `match`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory.
