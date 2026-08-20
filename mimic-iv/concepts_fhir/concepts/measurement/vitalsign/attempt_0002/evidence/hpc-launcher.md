# HPC-launcher evidence — vitalsign, attempt 0002

The sanctioned `uv run mimic_utils hpc-launch vitalsign` flow staged the current attempt at `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/vitalsign/attempt_0002`, passed the login-node smoke tests (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job `30221058`.

The CLI wrote `submit.slurm` and `hpc_job.json`. The remote run will produce `candidate.full.parquet`; polling will fetch `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. Submission is not a verdict.
