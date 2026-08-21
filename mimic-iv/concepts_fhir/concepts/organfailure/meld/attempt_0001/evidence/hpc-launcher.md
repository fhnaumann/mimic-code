# HPC-launcher evidence — meld

The repository CLI launched the first full-data run for this attempt using
`uv run mimic_utils hpc-launch meld`. Staging and the login-node smoke test
passed: warehouse, oracle, staged manifest, and imports were all OK.

- Local attempt: `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001`
- Slurm job: `30315052`
- Artifacts: `submit.slurm`, `hpc_job.json`

No hand-authored artifacts were changed and no commit was made. The job was
launched but not polled by this stage.
