# HPC-launcher evidence

Concept: `oasis`; attempt: `0001`.

`uv run mimic_utils hpc-launch oasis` staged the immutable attempt, its
dependency/manifest inputs, and the repository runner to the per-attempt
remote directory. The login-node smoke test passed (`warehouse OK`, `oracle
OK`, `staged manifest OK`, and `imports OK`), and Slurm accepted the job.

Job `30537656` was recorded in
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0001/hpc_job.json`.
Remote attempt path: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0001`.
No errors occurred and this stage did not poll or make a terminal transition.
