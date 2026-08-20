# Evidence — hpc-launcher

Concept: `arb`; attempt: `0004`.

Ran `uv run mimic_utils hpc-launch arb`. Staging and login-node smoke test
passed: warehouse, oracle, staged manifest, and imports were all confirmed.
Slurm job `30230384` was submitted for the remote attempt
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0004`.

The write-once artifact
`mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0004/hpc_job.json`
records the job id and submission metadata. No second submission was made; the
next step is polling this job. No implementation artifacts were modified and
no commit was made.
