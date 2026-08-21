# HPC-launcher evidence — `urine_output_rate`

The CLI command `uv run mimic_utils hpc-launch urine_output_rate` staged
attempt 0001 and its completed dependencies to the per-attempt Petrichor
directory, passed the login-node smoke test (`warehouse OK`, `oracle OK`,
`staged manifest OK`, `imports OK`), and submitted Slurm job `30312029`.

The write-once launch artifacts are `hpc_job.json` and `submit.slurm` in
attempt 0001. The launcher did not poll, edit hand-authored artifacts, touch
sibling jobs, or commit.
