# HPC-launcher evidence

The sanctioned `uv run mimic_utils hpc-launch weight_durations` command rendered `submit.slurm`, staged attempt-specific code, manifest, and artifacts, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job `29954821`. The write-once launch artifacts are `submit.slurm` and `hpc_job.json` in this attempt. No sibling job was touched.
