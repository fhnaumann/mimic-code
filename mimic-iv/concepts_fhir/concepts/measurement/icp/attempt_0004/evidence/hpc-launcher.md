# hpc-launcher evidence

Concept: `icp`; attempt: `0004`.

`uv run mimic_utils hpc-launch icp --attempt 4` staged only the ICP attempt
and its dependencies (none), passed the login-node smoke test (`warehouse OK`,
`oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job
`30109489`. The remote attempt path is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0004`.

Write-once artifacts produced: `submit.slurm` and `hpc_job.json`. Full result
artifacts are to be fetched by the poll stage. No candidate artifacts, notes,
or git state were modified.
