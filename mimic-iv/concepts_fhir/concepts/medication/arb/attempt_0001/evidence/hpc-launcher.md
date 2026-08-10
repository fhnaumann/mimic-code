# HPC launcher evidence

After `validate-full`, `uv run mimic_utils hpc-launch arb` rendered and staged the attempt to Petrichor, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `imports OK`), and submitted Slurm job `29603727`.

Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0001`.

Artifacts created: `submit.slurm` and `hpc_job.json` in the attempt directory. Full-data polling is required; queue submission alone is not a verdict.
