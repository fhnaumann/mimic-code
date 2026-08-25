# HPC launcher evidence

Concept: phenylephrine  
Attempt: 0004

The sanctioned `uv run mimic_utils hpc-launch phenylephrine` flow staged the attempt-specific code, warehouse references, oracle, and manifest on Petrichor. The login-node smoke test passed for the warehouse, oracle, staged manifest, and imports. Slurm job `30485281` was submitted successfully. The controller remained `VALIDATING_FULL` pending polling.

Artifacts: `submit.slurm` and `hpc_job.json` in this attempt directory. No carried implementation artifacts were edited and no commit was made.
