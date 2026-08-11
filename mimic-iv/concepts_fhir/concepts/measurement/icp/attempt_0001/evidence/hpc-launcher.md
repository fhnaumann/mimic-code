## Evidence

`uv run mimic_utils hpc-launch icp` staged attempt_0001, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), and submitted Slurm job `29732019`. The local immutable artifacts are `submit.slurm` and `hpc_job.json`; the remote attempt is `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0001`. Full candidate Parquet remains on scratch and comparison/run metadata will be fetched by polling. No manual edits or commit were made.
