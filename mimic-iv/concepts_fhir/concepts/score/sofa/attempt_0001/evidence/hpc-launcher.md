## HPC launcher evidence

Concept `sofa`, attempt `0001`. `uv run mimic_utils hpc-launch sofa` launched
Slurm job `30534326` successfully. The launcher staged the attempt, embedded
`mimic_utils` source, and oracle manifest into the attempt-specific remote
directory, then passed the login-node smoke test (`warehouse OK`, `oracle OK`,
`staged manifest OK`, `imports OK`).

Remote attempt:
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001`

Artifact `mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001/hpc_job.json`
records job `30534326`, submitted `2026-08-26T01:19:22.998856+00:00`, with a
2-hour walltime. No polling, implementation edits, other concept operations,
or commit were performed.
