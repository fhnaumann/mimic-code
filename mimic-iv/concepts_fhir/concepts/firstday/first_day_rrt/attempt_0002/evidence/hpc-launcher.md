# HPC-launcher evidence — `first_day_rrt`, attempt 0002

- What was run: `uv run mimic_utils hpc-launch first_day_rrt`.
- What was checked: remote staging, login-node smoke test, warehouse/oracle
  availability, staged manifest, imports, and Slurm submission.
- Result: all smoke checks passed and Slurm job `30486380` was submitted.
- Artifacts: `submit.slurm` and `hpc_job.json` were produced in this attempt;
  the staged remote attempt is under `/scratch3/nau025/.../attempt_0002`.
