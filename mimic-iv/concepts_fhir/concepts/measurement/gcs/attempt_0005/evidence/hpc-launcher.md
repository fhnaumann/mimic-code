# HPC launcher evidence — gcs

`uv run mimic_utils hpc-launch gcs` staged attempt_0005 to its per-attempt
remote directory and passed the login-node smoke test (`warehouse OK`,
`oracle OK`, `staged manifest OK`, `imports OK`). Slurm job `29874287` was
submitted successfully and recorded write-once in `hpc_job.json`.

Artifacts created: `submit.slurm` and `hpc_job.json` in
`mimic-iv/concepts_fhir/concepts/measurement/gcs/attempt_0005/`.
