# HPC launcher evidence

Launch complete. The mechanical CLI flow ran to completion with no failure markers: the login-node smoke test passed across all four checks (warehouse, oracle, staged manifest, imports), `submit.slurm` was rendered into the attempt directory, the attempt was staged to its own remote path, and the job reached the queue as `30315061` with `hpc_job.json` recorded. `hpc_job.json` was confirmed absent before launch (write-once respected), so this is attempt_0001's single, first full run. No clinical judgment or artifact edits were performed.

- **Concept:** `vasoactive_agent`
- **Attempt directory:** `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/`
- **Remote attempt path:** `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001`
- **Job id:** `30315061`; submitted `2026-08-21T02:41:00.997626+00:00`; walltime `2:00:00`
- **Smoke test:** PASSED — `warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`
- **Artifacts:** `submit.slurm`, `hpc_job.json`
- **Failure markers:** none — no `Traceback`, OOM, smoke-test refusal, queue error, or submission failure
- **Next:** `uv run mimic_utils hpc-poll vasoactive_agent`

No commits made.
