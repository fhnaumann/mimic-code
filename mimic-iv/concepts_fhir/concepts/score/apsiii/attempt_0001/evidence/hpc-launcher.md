# HPC launcher evidence

Concept: `apsiii`, attempt `0001`.

The mechanical command `uv run mimic_utils hpc-launch apsiii --attempt 1` staged the immutable attempt, dependency artifacts, code, and oracle manifest to `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/score/apsiii/attempt_0001`, passed the login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`), rendered `submit.slurm`, and submitted Slurm job `30512123`. The write-once artifacts are `submit.slurm` and `hpc_job.json` under `mimic-iv/concepts_fhir/concepts/score/apsiii/attempt_0001/`. No equivalence analysis or artifact edits were performed by this stage.
