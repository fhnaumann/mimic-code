## Evidence — hpc-launcher, acei attempt 0007

The replayed attempt was staged and submitted with `uv run mimic_utils
hpc-launch acei`. Remote smoke tests passed (`warehouse OK`, `oracle OK`,
`staged manifest OK`, `imports OK`). Slurm job `30483991` was submitted
successfully.

The carried `concept.sql` and ViewDefinitions remained byte-identical; launch
created the write-once `hpc_job.json` and `submit.slurm` artifacts. Remote
attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0007`.

Artifacts: `hpc_job.json`, `submit.slurm` in this attempt.
