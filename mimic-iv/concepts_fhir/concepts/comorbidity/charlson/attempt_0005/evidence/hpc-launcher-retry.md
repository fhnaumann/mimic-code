## Full-data launch retry — `charlson` attempt 0005

The prior launch did not submit because the login-node smoke test found the sanctioned remote environment lacked `sqlglot`. The orchestrator installed `sqlglot~=30.11` in `/scratch3/nau025/mimic-on-fhir-delta` (resolved version `30.17.0`) before retrying. No `hpc_job.json` or job existed at that point.

Ran exactly `uv run mimic_utils hpc-launch charlson` from `/Users/nau025/Documents/mimic-code`, without `--skip-smoke` and without hand submission.

Smoke test passed:
```text
warehouse OK
oracle OK
staged manifest OK
imports OK
```

Submission succeeded with job `30068637`; the CLI wrote `hpc_job.json` with remote attempt `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005`. No polling or commit was performed in this stage.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/submit.slurm`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/hpc_job.json`

This is a successful full-run submission, not yet a full-data verdict.
