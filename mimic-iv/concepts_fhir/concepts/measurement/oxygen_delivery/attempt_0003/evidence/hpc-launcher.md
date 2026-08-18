Evidence block

- Concept: `oxygen_delivery`, attempt `0003`.
- Attempt was staged to `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/oxygen_delivery/attempt_0003` with the attempt tree, `src/mimic_utils/`, and oracle manifest.
- `submit.slurm` was rendered and the login-node smoke test passed: warehouse, oracle, staged manifest, and imports (`duckdb`, `pathling`, `pyspark`, `mimic_utils.full_runner`) all resolved.
- Slurm job `30111381` was submitted successfully; `hpc_job.json` records the write-once submission.
- Artifacts: `attempt_0003/submit.slurm` and `attempt_0003/hpc_job.json`.
- No errors and no commit performed.
