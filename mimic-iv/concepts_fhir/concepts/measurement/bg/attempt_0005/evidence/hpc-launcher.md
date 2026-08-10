# Evidence: hpc-launcher (`bg`, attempt_0005)

Ran `uv run mimic_utils hpc-launch bg` from the repo root. Staging, the
login-node smoke test, and Slurm submission all succeeded. Smoke output was
`warehouse OK`, `oracle OK`, `imports OK`; job id is `29592332`.

Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005`.

Artifacts created:

- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/submit.slurm`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/hpc_job.json`

No implementation artifacts, `MIMIC_NOTES.md`, or other concept were modified;
the launcher performed no clinical judgment and did not poll.
