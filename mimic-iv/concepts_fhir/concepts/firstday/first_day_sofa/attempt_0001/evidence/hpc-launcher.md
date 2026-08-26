# HPC launcher evidence — `first_day_sofa`

## Result

- Sanctioned command: `uv run mimic_utils hpc-launch first_day_sofa`.
- Attempt: `attempt_0001`; remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_sofa/attempt_0001`.
- Login-node smoke test passed: warehouse, oracle, staged manifest, and imports all verified.
- Slurm job submitted successfully: job id `30511592`; submitted `2026-08-25T09:54:40Z` with walltime `2:00:00`.
- Artifacts written: `submit.slurm` and `hpc_job.json`.

## Evidence block

Read/checks: invoked only the sanctioned CLI, confirmed state was `VALIDATING_FULL`, staged the attempt-specific code/manifest/artifacts, checked the smoke test, and recorded the submitted job. No sibling job, implementation artifact, state other than the controller's launch bookkeeping, or commit was touched. Polling was not performed in this stage.
