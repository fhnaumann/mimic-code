# HPC launcher evidence — `first_day_weight`, attempt 0002

- Read/checked: current replay attempt and full-run staging inputs; `uv run mimic_utils hpc-launch first_day_weight` rendered the Slurm script, staged the attempt-specific source/manifest/oracle inputs, and passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`).
- Result: submitted successfully as Slurm job `30486471`; this is full run 1 for attempt 0002. No prior `hpc_job.json` existed.
- Artifacts: `submit.slurm` and write-once `hpc_job.json` in this attempt. Remote staging path: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_weight/attempt_0002`.
