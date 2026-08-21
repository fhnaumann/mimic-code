# HPC-launcher evidence — sirs, attempt_0001

`uv run mimic_utils hpc-launch sirs` staged this attempt to its per-attempt
remote directory, passed the login-node smoke test (`warehouse OK`, `oracle
OK`, `staged manifest OK`, and `imports OK`), submitted Slurm job `30318343`,
and wrote `hpc_job.json` once. The rendered submission artifact is
`submit.slurm`; the job record is `hpc_job.json`. No polling was performed in
this stage.
