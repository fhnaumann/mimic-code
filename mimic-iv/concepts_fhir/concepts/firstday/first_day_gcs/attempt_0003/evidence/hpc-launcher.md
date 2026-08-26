# HPC launcher evidence — `first_day_gcs`, attempt 0003

The repository CLI staged the immutable target attempt and completed `gcs`
dependency for the full-data run, rendered `submit.slurm`, passed the
login-node smoke test (`warehouse OK`, `oracle OK`, `staged manifest OK`, and
`imports OK`), and submitted Slurm job `30532631`.

The remote attempt is
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/firstday/first_day_gcs/attempt_0003`.
The local write-once launch artifacts are
`submit.slurm` and `hpc_job.json`; submission time was
`2026-08-26T00:58:42Z` with a two-hour walltime. Queue submission alone is not
a correctness result; the next stage must poll and fetch a fresh full
comparison artifact.
