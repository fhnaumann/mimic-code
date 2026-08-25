# HPC launcher evidence — vasopressin attempt_0003

- Read: replay provenance and HPC transfer/cluster instructions; confirmed the carried SQL and ViewDefinitions were byte-identical and no existing job record was present.
- Ran: `uv run mimic_utils hpc-launch vasopressin`.
- Result: login-node smoke test passed (`warehouse OK`, `oracle OK`, staged manifest and imports OK); Slurm job `30485928` submitted.
- Produced: `submit.slurm` and `hpc_job.json` in this attempt directory; remote staging was under `/scratch3/nau025/mimic-code/.../attempt_0003`.
- No implementation artifacts were edited and no unrelated concept was modified.
