# HPC-launcher evidence

`uv run mimic_utils hpc-launch weight_durations` staged attempt 0002, passed all login-node smoke tests (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job `29956802`. It wrote `submit.slurm` and `hpc_job.json` in the attempt-specific directory and did not touch sibling jobs.
