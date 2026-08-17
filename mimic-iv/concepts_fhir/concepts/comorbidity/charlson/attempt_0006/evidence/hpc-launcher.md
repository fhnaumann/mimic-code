## Full-data launch — `charlson` attempt 0006

Ran exactly `uv run mimic_utils hpc-launch charlson` from the repository with the normal smoke test. The CLI rendered and staged the attempt, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), submitted Slurm job `30069960`, and wrote its write-once job record.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/submit.slurm`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/hpc_job.json`

The job was submitted successfully; no polling or semantic judgment was performed in this stage.
