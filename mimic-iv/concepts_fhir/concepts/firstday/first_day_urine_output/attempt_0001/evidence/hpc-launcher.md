## HPC launcher evidence

The full run was staged and submitted successfully with `uv run mimic_utils hpc-launch first_day_urine_output`. Remote staging, the login-node smoke test, and Slurm submission all passed. Job ID: `30306604`; remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_urine_output/attempt_0001`. The smoke test validated warehouse, oracle, manifest, and imports. The write-once launch record is `attempt_0001/hpc_job.json`. The controller remained `VALIDATING_FULL`; no commit was made.
