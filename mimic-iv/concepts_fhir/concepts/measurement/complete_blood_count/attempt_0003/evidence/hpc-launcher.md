Evidence block — full-data launch, `complete_blood_count`

- Attempt: `attempt_0003`.
- `uv run mimic_utils hpc-launch complete_blood_count` completed successfully using the repository CLI.
- The attempt, staged `mimic_utils` source, oracle manifest, and completed dependencies were staged to the per-attempt remote path `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/complete_blood_count/attempt_0003`.
- Login-node smoke test passed: warehouse, oracle, staged manifest, and imports all green.
- Slurm job submitted: `30105580`; `hpc_job.json` records the job id, remote path, submission timestamp, and walltime.
- No sibling jobs were touched; no implementation artifacts were edited and nothing was committed.
