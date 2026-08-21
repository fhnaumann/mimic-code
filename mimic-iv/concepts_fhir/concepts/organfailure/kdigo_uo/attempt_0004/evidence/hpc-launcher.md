# HPC launcher evidence — kdigo_uo attempt 0004

The repository CLI launched the full-data run successfully with `uv run mimic_utils hpc-launch kdigo_uo --attempt 0004`.

- Local attempt: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004`
- Smoke test: passed warehouse, oracle, staged manifest, and imports checks.
- Slurm job id: `30317129`, recorded in `hpc_job.json`.
- Write-once artifacts: `submit.slurm` and `hpc_job.json`.

The job was submitted and had no comparator verdict at launch; polling is required.
