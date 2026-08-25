# HPC poller evidence — enzyme attempt_0004

- Read: `hpc_job.json` for the existing job `30484298`; did not launch a second job.
- Ran the prescribed poll and fetched the full-data artifacts. Slurm completed normally with no fatal markers; elapsed time was 98 seconds.
- Full comparator verdict: `match`. The keyed comparison used natural key `specimen_id`.
- Oracle and candidate each had 1,639,514 rows; all 1,639,514 rows matched identically. `differing`, `differing_conflict`, `differing_null_only`, `only_candidate`, and `only_oracle` were all zero. No unrepresentable exclusions.
- Schema matched, including required FHIR key columns; the extra key columns were non-gating.
- Produced/fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory.
- No judge or diagnostician was required; no implementation artifacts were modified.
