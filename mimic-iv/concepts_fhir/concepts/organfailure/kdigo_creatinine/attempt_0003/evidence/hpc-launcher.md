## HPC-launcher evidence

- Read: current immutable replay attempt and its write-once launch state.
- Checked: `uv run mimic_utils hpc-launch kdigo_creatinine` staged attempt_0003, the local source tree, and oracle manifest to the per-attempt remote directory; login-node smoke test passed (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`).
- Result: Slurm job `30484719` submitted successfully; no correctness verdict yet.
- Artifacts: `submit.slurm` and `hpc_job.json` in this attempt directory.
- Dataset-wide quirk check: no new dataset/IG-level quirk was reported; no `MIMIC_NOTES.d` entry appended.
