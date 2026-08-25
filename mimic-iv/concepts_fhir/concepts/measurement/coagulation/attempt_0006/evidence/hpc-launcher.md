## Evidence

- Read: the HPC transfer/cluster skill instructions and the immutable attempt directory.
- Checked: `hpc_job.json` was absent before launch; login-node smoke test passed for warehouse, oracle, staged manifest, and imports.
- Result: `uv run mimic_utils hpc-launch coagulation` submitted Slurm job `30484151` for replayed attempt `attempt_0006`.
- Artifacts: `submit.slurm`, `hpc_job.json`; remote attempt `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0006`.
