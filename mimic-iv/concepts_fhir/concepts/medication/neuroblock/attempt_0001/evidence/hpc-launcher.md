# HPC-launcher evidence — neuroblock

Ran `uv run mimic_utils hpc-launch neuroblock` after the full validation
transition. Render, per-attempt staging, login-node smoke test, and Slurm
submission all passed. The smoke test verified the warehouse, immutable
oracle, staged manifest, and imports. Job `29887633` was submitted for
attempt_0001 and `hpc_job.json` was written. No artifacts were edited and no
commit was made. The deciding comparison remains pending the poll/fetch.
