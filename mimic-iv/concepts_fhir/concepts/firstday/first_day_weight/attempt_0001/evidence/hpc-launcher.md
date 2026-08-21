Evidence block

`uv run mimic_utils hpc-launch first_day_weight` staged attempt_0001 and its
dependency to the per-attempt remote directory, passed the login-node smoke
test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and
submitted Slurm job `30308123`. The controller remained in
`VALIDATING_FULL`; no verdict was inferred from submission. Write-once
artifacts `submit.slurm` and `hpc_job.json` were created in
`mimic-iv/concepts_fhir/concepts/firstday/first_day_weight/attempt_0001/`.
No authored artifact was modified and no commit was made.
