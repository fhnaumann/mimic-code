**Concept:** `nsaid` (medication category)

**Attempt directory:** `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/medication/nsaid/attempt_0003`

**Remote attempt path:** `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/nsaid/attempt_0003`

**State check before launch:** `mimic_utils status` reported `nsaid -> VALIDATING_FULL`, attempt 0003 current, and no `hpc_job.json` existed in the attempt directory — so the attempt had not yet been launched. Launch proceeded without `--attempt` as the task named attempt_0003 and the current attempt matches.

**Smoke test (login node, against staged copy):** PASSED — `warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK` (duckdb, pathling, pyspark, `mimic_utils.full_runner` all resolved under `PYTHONPATH=<remote_attempt>/src`).

**Slurm job id:** `30485229` (account `OD-221174`, wall time 2:00:00)

**Command run:** `uv run mimic_utils hpc-launch nsaid`

**Artifacts written:** `submit.slurm` and `hpc_job.json` in attempt_0003; `hpc_job.json` records job_id `30485229`, remote_attempt path, and submitted_at `2026-08-25T00:38:23.200127+00:00`.

**Outcome:** launch succeeded; no error. No artifacts edited, no git commit, no diagnosis or judgment performed. Next step is `uv run mimic_utils hpc-poll nsaid`.
