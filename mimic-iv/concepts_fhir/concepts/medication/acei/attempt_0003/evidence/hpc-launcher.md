Evidence block — concept `acei`, stage `hpc-launcher`, attempt 0003.

`uv run mimic_utils hpc-launch acei` staged the immutable attempt to
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0003`,
passed the login-node smoke checks (`warehouse OK`, `oracle OK`, `imports OK`),
and submitted Slurm job `29599602`.

Launch artifacts created once in the attempt directory:

- `submit.slurm`
- `hpc_job.json`

The attempt remained in VALIDATING_FULL. Queue submission is not a verdict;
the fresh full comparison must be fetched by hpc-poll.
