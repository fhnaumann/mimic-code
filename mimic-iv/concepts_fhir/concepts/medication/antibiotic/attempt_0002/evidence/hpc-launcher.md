# HPC launcher evidence — antibiotic attempt_0002

Stage: hpc-launcher
Command: `uv run mimic_utils hpc-launch antibiotic --attempt 2`
Run from: `/Users/nau025/Documents/mimic-code`

## Outcome

- Job submitted: **29721291**
- Smoke test: **passed** (all four checks green)
- `hpc_job.json` written once (write-once per attempt)

## CLI output (verbatim)

```
concept:        antibiotic
attempt:        /Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002
remote attempt: /scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002
smoke test:
warehouse OK
oracle OK
staged manifest OK
imports OK
submitted:      job 29721291
poll with:      uv run mimic_utils hpc-poll antibiotic
```

## Artifacts

| Artifact | Path |
|---|---|
| Attempt dir | `mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002/` |
| Job record | `attempt_0002/hpc_job.json` (job_id `29721291`, remote_attempt `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002`, submitted_at `2026-08-11T07:17:18.438738+00:00`, walltime `2:00:00`) |
| Slurm script | `attempt_0002/submit.slurm` (rendered locally at launch) |
| Remote attempt | `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002` |

## Notes

- No `hpc_job.json` existed before launch; written exactly once by the CLI.
- No manual ssh/rsync/sbatch used; the mechanical CLI flow did render → stage → smoke test → submit.
- No polling performed (poller's job).
- No git commit made.
- Result artifacts (`comparison.full.json`, `run_meta.full.json`) are fetched by `hpc-poll`, which is out of scope here.
