# HPC-launcher evidence — neuroblock attempt 0005

The full-data attempt was staged and smoke-tested successfully. Warehouse,
oracle, staged manifest, and imports checks all passed. Slurm job `30235056`
was submitted to Petrichor with the remote attempt path recorded.

Artifacts: `submit.slurm` and write-once `hpc_job.json` in this attempt
directory. The next required operation is `uv run mimic_utils hpc-poll
neuroblock`.
