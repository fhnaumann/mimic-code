# HPC launch evidence

- Concept/attempt: `rhythm`, `0003`; controller state was `VALIDATING_FULL` with `hpc_counter=3`.
- Command: `uv run mimic_utils hpc-launch rhythm`.
- Job `30060701` was submitted at `2026-08-17T04:09:41.704022+00:00`.
- The login-node smoke test passed all checks: warehouse, oracle, staged manifest, and imports.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/rhythm/attempt_0003`.
- Artifacts: `submit.slurm` and write-once `hpc_job.json` in the attempt directory.
- No errors, edits, commits, or polling were performed. Next stage is `uv run mimic_utils hpc-poll rhythm`.
