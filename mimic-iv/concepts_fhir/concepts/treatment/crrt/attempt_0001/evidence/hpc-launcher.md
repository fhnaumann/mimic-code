## Evidence

The full-data attempt was staged and submitted successfully. Login-node smoke
tests passed for the warehouse, oracle, staged manifest, and imports. Slurm
job `29710188` was submitted at `2026-08-11T03:44:40Z` and is recorded
write-once in `hpc_job.json`.

Artifacts produced for the HPC leg include `submit.slurm` and `hpc_job.json`
in the attempt directory. The remote job will produce
`candidate.full.parquet`, `comparison.full.json`, and `run_meta.full.json`;
the candidate Parquet remains on scratch. No implementation artifacts were
changed.
