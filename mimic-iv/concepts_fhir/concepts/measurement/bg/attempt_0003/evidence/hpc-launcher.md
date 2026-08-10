# HPC launch evidence

- Command: `uv run mimic_utils hpc-launch bg`.
- Result: attempt 0003 staged successfully; login-node smoke tests passed for warehouse, oracle, and imports; Slurm job submitted as `29589053` with walltime `2:00:00`.
- Full-run count: run 2 of the 10-run cap.
- Artifacts: `submit.slurm` and `hpc_job.json` in attempt 0003; remote `candidate.full.parquet` and comparison metadata will be fetched by polling.
- No source or prior attempt was modified.
