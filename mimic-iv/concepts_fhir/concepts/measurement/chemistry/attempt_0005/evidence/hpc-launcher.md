# HPC launcher evidence

Concept: `chemistry`
Attempt: `attempt_0005`

`uv run mimic_utils hpc-launch chemistry` succeeded. The staged remote attempt
passed warehouse, oracle, manifest, and import smoke checks. Slurm job `30484074`
was submitted with no pre-existing job record; the local attempt now contains
`hpc_job.json` and `submit.slurm`. The replayed SQL and ViewDefinitions were
left byte-identical and were not edited.
