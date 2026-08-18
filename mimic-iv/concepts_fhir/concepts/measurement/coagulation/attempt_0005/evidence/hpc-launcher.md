# HPC launcher evidence — coagulation attempt 0005

Ran `uv run mimic_utils hpc-launch coagulation`. The attempt, staged
`src/mimic_utils`, and oracle manifest were transferred to the per-attempt
Petrichor directory. The login-node smoke test passed (`warehouse OK`, `oracle
OK`, staged manifest and imports OK), and Slurm submission succeeded.

- Job id: `30104201`
- Remote attempt:
  `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005`
- Local artifacts:
  `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/hpc_job.json`
  and `submit.slurm`

No implementation artifact was modified and no polling was performed in this
stage.
