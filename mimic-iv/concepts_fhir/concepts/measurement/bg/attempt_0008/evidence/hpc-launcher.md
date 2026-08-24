# HPC launch evidence

Concept: `bg`  
Attempt: `attempt_0008`  
Job: `30483911`

`uv run mimic_utils hpc-launch bg` completed successfully. Per-attempt
staging, the login-node smoke test (`warehouse OK`, `oracle OK`, `staged
manifest OK`, `imports OK`), and Slurm submission all passed. The remote attempt
was staged at `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0008`.

Produced artifacts:

- `submit.slurm`
- `hpc_job.json`

The implementation artifacts were not edited and no commit was made. The next
step is `uv run mimic_utils hpc-poll bg`.
