## Evidence

The replayed rhythm attempt_0004 was staged and submitted with `uv run mimic_utils hpc-launch rhythm` without editing carried artifacts. Login-node smoke tests passed for the warehouse, oracle, staged manifest, and imports. Slurm job `30485866` was recorded in `hpc_job.json`; remote attempt path is `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/rhythm/attempt_0004`. The rendered `submit.slurm` pins the expected UTC/Spark execution. Polling remains the next step.
