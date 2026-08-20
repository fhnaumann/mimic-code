# HPC launch evidence — vasopressin attempt 0002

The mechanical `mimic_utils hpc-launch vasopressin` stage completed. It
rendered and staged the attempt, passed the login-node smoke checks for the
warehouse, oracle, staged manifest, and imports, submitted the Slurm job, and
wrote `hpc_job.json` once. The job id and submission metadata are recorded in
that controller artifact. The remote attempt was staged under its per-attempt
scratch path. No manual artifact edits or commit were made.

Next action: poll using `uv run mimic_utils hpc-poll vasopressin`. This launch
stage made no semantic judgment.
