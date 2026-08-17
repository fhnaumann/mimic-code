# HPC launch evidence — `bg`, attempt 0007

The sanctioned `uv run mimic_utils hpc-launch bg` flow staged the immutable
attempt and embedded runner to Petrichor, passed the login-node smoke test
(`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted
Slurm job `30061464`. The remote attempt path is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0007`.

Write-once artifacts produced:

- `submit.slurm`
- `hpc_job.json`

No implementation artifact was edited, and no full verdict was available at
launch; polling is the next stage.
