# HPC-launcher evidence

The full-data attempt was staged and submitted with
`uv run mimic_utils hpc-launch epinephrine --attempt 1`. Login-node smoke tests
passed (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`). Slurm
job `29714574` was submitted for attempt_0001 and recorded write-once in
`hpc_job.json`; `submit.slurm` and `hpc_job.json` are in the attempt directory.
The remote attempt is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0001`.
No clinical verdict was made by the launcher.
