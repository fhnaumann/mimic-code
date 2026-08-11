# HPC-launcher evidence

Ran `uv run mimic_utils hpc-launch dobutamine`. The attempt was staged to its per-attempt remote directory, login-node smoke tests passed for warehouse, oracle, manifest, and imports, and Slurm job `29710383` was submitted. The write-once `hpc_job.json` and rendered `submit.slurm` were produced in attempt 0001. No artifacts were edited manually and no commit was made.

Artifacts: `mimic-iv/concepts_fhir/concepts/medication/dobutamine/attempt_0001/hpc_job.json` and `submit.slurm`.
