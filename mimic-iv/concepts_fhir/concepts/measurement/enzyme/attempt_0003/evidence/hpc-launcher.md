# HPC launcher evidence — enzyme attempt 0003

- `uv run mimic_utils hpc-launch enzyme` staged the attempt-specific source, manifest, and artifacts after a successful login-node smoke test.
- Slurm job `30105581` was submitted and recorded in `hpc_job.json`; remote attempt path: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0003`.
- Smoke checks passed: warehouse, oracle, staged manifest, and imports. `submit.slurm` and `hpc_job.json` were produced. No implementation artifacts were modified and no commit was made.
