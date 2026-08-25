# HPC launcher evidence — meld attempt_0002

- Ran the sanctioned `uv run mimic_utils hpc-launch meld` flow.
- Login-node smoke test passed: warehouse, oracle, staged manifest, and imports were all confirmed.
- Slurm job `30494642` was submitted for the replay attempt; poll with `uv run mimic_utils hpc-poll meld`.
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0002`.
- Artifacts produced: `submit.slurm` and write-once `hpc_job.json`.
- SQL and ViewDefinitions were not edited. No clinical interpretation or commit was performed.
