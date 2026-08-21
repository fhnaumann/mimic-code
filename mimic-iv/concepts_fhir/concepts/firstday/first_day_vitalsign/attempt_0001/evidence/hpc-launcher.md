# HPC launcher evidence

`uv run mimic_utils hpc-launch first_day_vitalsign` staged attempt_0001 and
its completed dependency artifacts to the per-attempt Petrichor directory,
passed the login-node smoke checks (`warehouse OK`, `oracle OK`, `staged
manifest OK`, `imports OK`), and submitted Slurm job `30308135`.

The launcher wrote the immutable job record at
`mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/hpc_job.json`
