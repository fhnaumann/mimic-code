## Evidence

Launched `icustay_detail` attempt 0003 from `VALIDATING_FULL` with
`uv run mimic_utils hpc-launch icustay_detail`. No `hpc_job.json` existed for
the attempt before launch.

Per-attempt staging and the login-node smoke test passed `warehouse OK`,
`oracle OK`, `staged manifest OK`, and `imports OK`. Submitted Slurm job
`29735525`; `submit.slurm` and `hpc_job.json` were written. Remote attempt:
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0003`.
Polling was deferred.
