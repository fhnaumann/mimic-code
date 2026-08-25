# HPC launcher evidence

- Concept: `oxygen_delivery`, attempt `0004`; controller was `VALIDATING_FULL`.
- Checked: canonical `uv run mimic_utils hpc-launch oxygen_delivery`.
- Result: login-node smoke test passed (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`); Slurm submission succeeded with job `30485304`.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/oxygen_delivery/attempt_0004`.
- Artifacts: `submit.slurm` and `hpc_job.json`.
- Next action: poll job `30485304` with `uv run mimic_utils hpc-poll oxygen_delivery`.
