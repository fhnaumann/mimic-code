# HPC-launcher evidence — charlson attempt 0001

The launcher staged the immutable attempt to the per-attempt remote path,
passed the login-node smoke test (warehouse, oracle, manifest, and imports),
and submitted Slurm job `29957224` while the controller was in
`VALIDATING_FULL`. The write-once artifacts `hpc_job.json` and `submit.slurm`
were created.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0001/hpc_job.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0001/submit.slurm`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0001`

Job id: `29957224`. No clinical analysis or git changes were made by the
launcher.
