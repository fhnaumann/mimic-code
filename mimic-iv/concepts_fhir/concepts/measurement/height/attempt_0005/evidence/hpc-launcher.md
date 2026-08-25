# HPC launch evidence — height attempt_0005

Ran `uv run mimic_utils hpc-launch height`. The CLI rendered and staged the attempt, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job `30484312`.

Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0005`.

Artifacts produced locally: `submit.slurm` and write-once `hpc_job.json`. The poller is expected to fetch `comparison.full.json` and `run_meta.full.json`; `candidate.full.parquet` remains on scratch.
