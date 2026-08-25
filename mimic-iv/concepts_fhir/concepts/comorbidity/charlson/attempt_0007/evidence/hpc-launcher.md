# HPC launcher evidence

## Concept and attempt

- Concept: `charlson`
- Attempt: `attempt_0007`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007`

## Result

- `uv run mimic_utils hpc-launch charlson` completed successfully.
- Login-node smoke test passed: warehouse, oracle, staged manifest, and imports
  checks all passed.
- Slurm job submitted: `30485985`.
- No SQL or ViewDefinition was modified.

## Artifacts

- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/hpc_job.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/submit.slurm`
