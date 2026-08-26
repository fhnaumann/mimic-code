# HPC-launcher evidence

Concept: `oasis`; attempt: `0002`.

`uv run mimic_utils hpc-launch oasis` staged this immutable attempt and its
dependencies/manifest to the per-attempt remote directory. The login-node
smoke test passed all four checks (`warehouse OK`, `oracle OK`, `staged
manifest OK`, `imports OK`), and Slurm accepted job `30542485`.

The job record is
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0002/hpc_job.json`; the
remote attempt is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0002`.
No errors, polling, state transition, or implementation edit occurred here.
