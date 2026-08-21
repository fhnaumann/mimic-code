# HPC launcher evidence — icustay_hourly

`uv run mimic_utils hpc-launch icustay_hourly` staged the current attempt,
completed derived dependencies, source, and oracle manifest into the attempt's
own remote directory. The login-node smoke test passed warehouse, oracle,
manifest, and staged-import checks. Slurm submission succeeded.

- Local attempt: `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/`
- Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001`
- Job id: `30309334`
- Artifacts: `submit.slurm`, `hpc_job.json`

Polling remains required; queue exit alone is not a verdict.
