## Evidence

The full-data attempt was staged per attempt to `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0001`. The launcher rsynced the staged `src/mimic_utils`, oracle manifest, and attempt directory, then passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, and imports OK).

Slurm job `29674397` was submitted successfully. The CLI created `submit.slurm` and `hpc_job.json` once; `hpc_job.json` records the job and submission metadata. Polling remains to be performed with `uv run mimic_utils hpc-poll blood_differential`.
