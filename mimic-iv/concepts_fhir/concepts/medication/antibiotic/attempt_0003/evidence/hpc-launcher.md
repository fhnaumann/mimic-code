# HPC-launcher evidence

The sanctioned `uv run mimic_utils hpc-launch antibiotic` flow staged attempt
0003 to Petrichor, passed the login-node smoke test (`warehouse OK`, `oracle
OK`, `staged manifest OK`, `imports OK`), submitted Slurm job `30230408`, and
recorded the write-once `hpc_job.json` at the attempt root. Remote attempt:
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0003`.

No launch errors, manual edits, or commits. The next required stage is
`uv run mimic_utils hpc-poll antibiotic`.
