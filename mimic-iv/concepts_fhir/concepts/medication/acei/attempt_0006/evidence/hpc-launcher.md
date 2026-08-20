# HPC launcher evidence — acei attempt 0006

- Command: `uv run mimic_utils hpc-launch acei`.
- Launch succeeded after the sanctioned login-node smoke test reported
  `warehouse OK`, `oracle OK`, `staged manifest OK`, and `imports OK`.
- Slurm job: `30230354`, submitted 2026-08-20T03:52:45+00:00 with a 2-hour
  walltime.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006`.
- No dependencies were staged.
- Polling was intentionally not performed by this stage; the next command is
  `uv run mimic_utils hpc-poll acei`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/submit.slurm`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/hpc_job.json`
