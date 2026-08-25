# HPC launcher evidence — weight_durations attempt 0004

`uv run mimic_utils hpc-launch weight_durations` succeeded. The login-node
smoke test passed warehouse, oracle, staged-manifest, and import checks. Slurm
job `30485990` was submitted for the replay attempt and recorded in
`hpc_job.json`; `submit.slurm` was rendered. The staged remote attempt is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0004`.

No carried SQL or ViewDefinition was edited. The next required operation is
the sequential `mimic_utils hpc-poll weight_durations` flow.
