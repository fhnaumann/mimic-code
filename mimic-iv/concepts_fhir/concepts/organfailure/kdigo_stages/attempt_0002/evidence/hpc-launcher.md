# HPC launcher — kdigo_stages attempt_0002

## Command
`uv run mimic_utils hpc-launch kdigo_stages --attempt 2`

## Outcome
Launch **succeeded**. Slurm job submitted and recorded.

## Smoke test (login node, against staged copy)
- warehouse: OK
- oracle: OK
- staged manifest: OK
- imports (duckdb, pathling, pyspark, mimic_utils.full_runner): OK

## Job
- job id: **30319339**
- remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002`
- walltime: 2:00:00
- submitted at: 2026-08-21T04:10:54.185094+00:00

## Artifacts written
- `submit.slurm` (rendered from template into attempt dir)
- `hpc_job.json` (job id + remote path, write-once)

## Next step
Poll with: `uv run mimic_utils hpc-poll kdigo_stages`

## Scope
Only `kdigo_stages` touched. No implementation artifacts edited. No commit made.