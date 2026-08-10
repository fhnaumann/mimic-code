# HPC launcher evidence — code_status attempt 0001

Command: `uv run mimic_utils hpc-launch code_status`.

Attempt 0001 was staged to
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001`.
The required login-node smoke test passed: warehouse, oracle, staged manifest,
and imports were all OK. Slurm job `29680054` was submitted successfully.

This is full-data run 1 of the hard cap of 10. No implementation artifact was
modified.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/hpc_job.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/submit.slurm`
