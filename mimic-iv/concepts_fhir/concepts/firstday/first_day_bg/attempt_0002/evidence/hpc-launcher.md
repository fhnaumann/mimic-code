# Evidence: hpc-launcher (`first_day_bg`, attempt 0002)

Command: `uv run mimic_utils hpc-launch first_day_bg`.

The attempt and completed `bg` dependency were staged to Petrichor, the
login-node smoke test passed (`warehouse OK`, `oracle OK`, `staged manifest
OK`, `imports OK`), and Slurm job `30238491` was submitted. The controller
recorded the write-once launch metadata.

Artifacts:

- `submit.slurm`
- `hpc_job.json`

Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0002`.
No correctness verdict was made at launch and no commit occurred.
