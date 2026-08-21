# HPC launcher evidence

`uv run mimic_utils hpc-launch norepinephrine_equivalent_dose` staged
attempt_0002 and its completed dependencies, passed the login-node smoke test,
and submitted Slurm job `30324549` on Petrichor. Smoke checks all passed:
warehouse, oracle, staged manifest, and imports. The write-once job record is
`attempt_0002/hpc_job.json`; the remote attempt is staged at
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/norepinephrine_equivalent_dose/attempt_0002`.

The next required action is `uv run mimic_utils hpc-poll norepinephrine_equivalent_dose`.
No artifacts were hand-edited and no commit was made.
