# HPC-launcher evidence — rhythm

`uv run mimic_utils hpc-launch rhythm` staged attempt_0001, passed the remote
smoke test, and submitted Slurm job `29944380` on Petrichor. The write-once
launch record is `hpc_job.json`; the generated script is `submit.slurm`. The
launcher invocation was interrupted after submission, but the job record proves
the job existed and was not relaunched.
