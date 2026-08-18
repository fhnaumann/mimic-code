# HPC-launcher evidence — blood_differential attempt 0003

The sanctioned full-data launcher staged attempt 0003, its embedded
`src/mimic_utils` copy, the oracle manifest, and dependencies to the
per-attempt Petrichor path. The login-node smoke test passed all checks:
`warehouse OK`, `oracle OK`, `staged manifest OK`, and `imports OK`.

Slurm job `30103841` was submitted successfully and recorded in the
write-once `hpc_job.json`. The launcher produced `submit.slurm` and
`hpc_job.json`; no implementation artifacts were changed and no commit was
made.

Artifacts:

- `submit.slurm`
- `hpc_job.json`
