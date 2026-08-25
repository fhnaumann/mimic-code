# HPC poller evidence

- Concept: `oxygen_delivery`, attempt `0004`; Slurm job `30485304`.
- Checked: canonical `uv run mimic_utils hpc-poll oxygen_delivery`; job completed after 4 polls with no fatal markers.
- Result: full comparator verdict `match`; schema matched, and keyed diff on `[subject_id, charttime]` found 0 `only_oracle`, 0 `only_candidate`, 0 `differing_null_only`, and 0 `differing_conflict` rows. All 601,546 oracle rows reproduced identically.
- Row count: candidate 601,546, oracle 601,546; reported as evidence and not used as an independent gate.
- No judge or diagnostician was required because the comparator returned `match`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` fetched/recorded in this attempt.
