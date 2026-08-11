# HPC launcher evidence

Concept: `dobutamine`  
Attempt: `0002`  
Slurm job: `29724469`

`uv run mimic_utils hpc-launch dobutamine` completed successfully. The
login-node smoke test passed all checks: warehouse, oracle, staged manifest,
and imports. Submission was permitted and the attempt was staged at
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/dobutamine/attempt_0002`.

Write-once artifacts recorded by the CLI:
- `submit.slurm`
- `hpc_job.json`

No launch error occurred; polling is the next step.
