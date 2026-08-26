# HPC launcher evidence — `first_day_sofa` attempt 0002

## Result

- Sanctioned command: `uv run mimic_utils hpc-launch first_day_sofa`.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_sofa/attempt_0002`.
- Smoke test passed: warehouse, oracle, staged manifest, and imports all verified.
- Slurm job submitted: `30512546`, submitted `2026-08-25T10:59:08Z`, walltime `2:00:00`.
- Artifacts: `submit.slurm` and `hpc_job.json`.

## Evidence block

Read/checks: used only the sanctioned per-attempt HPC launcher, verified no prior job record in attempt 0002, passed the login-node smoke test, and recorded the job. No polling, sibling jobs, implementation artifacts, or commits were touched.
