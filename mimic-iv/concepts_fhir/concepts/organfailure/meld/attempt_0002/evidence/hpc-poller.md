# HPC poller evidence — meld attempt_0002

- Polled Slurm job `30494642` with `uv run mimic_utils hpc-poll meld`; five polls completed normally.
- Full-data outcome was `complete`; `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` were fetched.
- Comparator verdict was `match`, keyed on `stay_id`: 73,181/73,181 oracle rows reproduced identically (100.00%).
- Schema matched; there were zero `differing_conflict`, `differing_null_only`, `only_candidate`, or `only_oracle` rows. Divergence tier was `none`; no judge or diagnostician was required.
- Oracle and candidate row counts were both 73,181 (reported only; not a gate). Slurm elapsed time was 1,099 seconds.
- No implementation artifacts were edited and no commit was performed.
