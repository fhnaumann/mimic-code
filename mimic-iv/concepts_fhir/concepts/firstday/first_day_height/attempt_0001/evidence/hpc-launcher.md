# HPC launcher evidence — `first_day_height`

Ran `uv run mimic_utils hpc-launch first_day_height` for attempt_0001.
Staging to Petrichor passed the warehouse, oracle, staged-manifest, and import
smoke tests. Slurm submission succeeded with job ID `30241742`.

The write-once job record is
`mimic-iv/concepts_fhir/concepts/firstday/first_day_height/attempt_0001/hpc_job.json`;
the remote attempt was staged at
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_height/attempt_0001`.
No candidate artifacts were modified and no commit was made. The next required
stage is `uv run mimic_utils hpc-poll first_day_height`.
