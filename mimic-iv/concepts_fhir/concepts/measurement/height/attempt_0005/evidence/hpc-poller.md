# HPC poll evidence — height attempt_0005

Polled Slurm job `30484312` with `uv run mimic_utils hpc-poll height`. Poll outcome was `complete`, with Slurm state `COMPLETED`; this was distinguished from the comparator verdict.

`comparison.full.json` reports `match` on keyed join key `stay_id`. Schema matched, and the keyed diff was empty: candidate 33,474 rows, oracle 33,474 rows, `only_oracle=0`, `only_candidate=0`, `differing_null_only=0`, and `differing_conflict=0`. Thus 33,474/33,474 rows matched identically (100%). No divergence tier, diagnostician, or judge was required.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory. The embedded Pathling execution took 115.821 seconds and comparison 1.022 seconds; Slurm elapsed time was 119 seconds.
