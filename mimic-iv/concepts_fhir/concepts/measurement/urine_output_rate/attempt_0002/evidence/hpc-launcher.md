# HPC-launcher evidence — `urine_output_rate`, attempt 0002

The CLI staged attempt 0002 and completed dependencies to its own Petrichor
directory, passed the login-node smoke test (`warehouse OK`, `oracle OK`,
`staged manifest OK`, `imports OK`), and submitted Slurm job `30313105`.

Write-once artifacts `hpc_job.json` and `submit.slurm` were created in attempt
0002. The launcher did not poll, edit hand-authored artifacts, touch sibling
jobs, or commit.
