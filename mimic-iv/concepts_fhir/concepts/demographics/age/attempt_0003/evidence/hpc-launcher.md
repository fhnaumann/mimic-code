# Evidence: hpc-launcher

`uv run mimic_utils hpc-launch age` launched the full-data run for attempt
0003. Login-node smoke tests passed for the warehouse, oracle, staged
manifest, and imports (`duckdb`, `pathling`, `pyspark`, and
`mimic_utils.full_runner`).

- Slurm job: `30054194`
- Local attempt: `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003`
- Script: `.../attempt_0003/submit.slurm`
- Job record: `.../attempt_0003/hpc_job.json`

No verdict was made by the launcher and no artifacts were edited or committed.
