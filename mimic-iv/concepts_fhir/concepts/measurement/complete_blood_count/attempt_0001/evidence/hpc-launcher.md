Evidence block — Concept: `complete_blood_count`, attempt `0001`.

Command `uv run mimic_utils hpc-launch complete_blood_count --attempt 0001` staged the attempt, source tree, and oracle manifest in the per-attempt remote directory and passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`). Slurm job `29703807` was submitted and recorded write-once in `attempt_0001/hpc_job.json`. No implementation artifacts were modified and no commit was made; polling remains outstanding.
