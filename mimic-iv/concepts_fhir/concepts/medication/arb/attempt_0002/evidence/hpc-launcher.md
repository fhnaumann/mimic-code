# HPC launcher evidence

Attempt 0002 was transferred and launched with `uv run mimic_utils hpc-launch arb`. The login-node smoke test passed all checks: `warehouse OK`, `oracle OK`, `imports OK`. The job was submitted exactly once as Slurm job `29605737`.

Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0002`.

Artifacts: `submit.slurm` and `hpc_job.json` in attempt 0002. This fresh write-once attempt avoids the cancelled attempt 0001 job record; polling is required for the deciding verdict.
