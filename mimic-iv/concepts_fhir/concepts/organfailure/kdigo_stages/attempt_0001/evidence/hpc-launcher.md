The full-data run was launched successfully. Following the mechanical `hpc-launch` path exactly as the repo requires: the CLI rendered `submit.slurm`, staged this immutable attempt plus completed derived dependency attempts to its own remote directory, ran the login-node smoke test against that staged copy, submitted the Slurm job, and recorded `hpc_job.json`. No artifacts were modified or diagnosed, no other concept launched, no commit made, and (per protocol) I did not poll.

**Evidence block**

- **Concept:** `kdigo_stages`
- **Attempt directory (local):** `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0001/`
- **Remote attempt path:** `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0001`
- **Job id:** `30314664` (host `nau025@petrichor.hpc.csiro.au`, walltime `2:00:00`)
- **Smoke test:** **PASSED** — CLI reported `warehouse OK`, `oracle OK`, `staged manifest OK`, `imports OK`. No staged-copy import or environment problem; submission proceeded.
- **Launch outcome:** full-data Slurm job submitted; `hpc_job.json` written (write-once) at `...attempt_0001/hpc_job.json` recording `concept`, `job_id`, `remote_attempt`, `submitted_at`, and `walltime`.
- **Artifacts/evidence produced:** `submit.slurm` (rendered), `hpc_job.json` (recorded), plus the pre-existing immutable attempt artifacts (`ViewDefinition.*.json`, `concept.sql`, `candidate.demo.parquet`, `shape.demo.json`, `evidence/`). No new verdict, comparator, or diagnosis artifacts were produced — this launch only stages, smoke-tests, submits, and records the job handle. Poll with `uv run mimic_utils hpc-poll kdigo_stages`.
- **No errors:** launch completed without failure, so no engineering/HPC failure to report.
