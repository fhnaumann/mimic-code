## Evidence

Concept: `icustay_detail`, attempt 0001; controller state
`VALIDATING_FULL`, first full run.

`uv run mimic_utils hpc-launch icustay_detail` staged the attempt to its
per-attempt remote directory and passed the login-node smoke test:
`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`.

Submitted Slurm job `29732525` (run 1). The CLI recorded the write-once
artifacts `submit.slurm` and `hpc_job.json` under the attempt directory. The
remote attempt is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0001`.
Polling was intentionally deferred to the poller.
