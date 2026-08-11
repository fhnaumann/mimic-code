## Evidence

Launched corrected `icustay_detail` attempt 0002 with
`uv run mimic_utils hpc-launch icustay_detail` while the controller was in
`VALIDATING_FULL`. No prior `hpc_job.json` existed for this attempt.

The per-attempt staging and login-node smoke test passed all checks:
`warehouse OK`, `oracle OK`, `staged manifest OK`, and `imports OK`.
Submitted Slurm job `29734517`; the CLI wrote `submit.slurm` and
`hpc_job.json` and staged the attempt-specific source/manifest to
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0002`.
Polling was deferred to the poller.
