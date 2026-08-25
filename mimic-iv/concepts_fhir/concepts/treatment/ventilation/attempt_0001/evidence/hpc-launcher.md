Evidence block from hpc-launcher:

Concept: ventilation. Attempt directory: `mimic-iv/concepts_fhir/concepts/treatment/ventilation/attempt_0001`. Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/treatment/ventilation/attempt_0001`. Job id: `30507624`.

`uv run mimic_utils hpc-launch ventilation` executed exactly once. CLI smoke test passed all four checks: warehouse OK, oracle OK, staged manifest OK, imports OK. Submission succeeded; `hpc_job.json` did not exist before launch. Artifacts produced: `submit.slurm` and `hpc_job.json`. Candidate artifacts were not edited and no commit was made. Poll command: `uv run mimic_utils hpc-poll ventilation`.
