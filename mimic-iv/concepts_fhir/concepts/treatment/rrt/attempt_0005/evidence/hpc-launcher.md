# HPC launcher evidence

- Concept: `rrt`; attempt: `attempt_0005`.
- Command: `uv run mimic_utils hpc-launch rrt`.
- Job: Slurm job `30485855`, submitted `2026-08-25T01:06:01Z`.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0005`.
- Login-node smoke test passed: warehouse, oracle, staged manifest, and imports all verified.
- The replay-carried SQL and ViewDefinitions were not edited. Launch added only the write-once `submit.slurm` and `hpc_job.json` artifacts.
