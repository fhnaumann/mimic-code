## Evidence

- Concept: dobutamine
- Attempt: attempt_0004
- Stage: hpc-launcher
- Read/checks: Submitted the replay attempt with `uv run mimic_utils hpc-launch dobutamine`; login-node smoke test checked warehouse, oracle, staged manifest, and imports.
- Result: submission succeeded; Slurm job `30484229` was created. Smoke test passed. No carried implementation artifacts were edited.
- Artifacts: `submit.slurm` and write-once `hpc_job.json` in this attempt directory; remote staging used the per-attempt path.
