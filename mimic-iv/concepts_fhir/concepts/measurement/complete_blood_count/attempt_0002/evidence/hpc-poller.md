# HPC-poller evidence — complete_blood_count, attempt_0002

Job `29719894` completed and produced a fetched comparison. Full-data schema
identity held for all 14 columns keyed by `specimen_id`. Oracle and candidate
both had 3,362,503 rows; 3,362,299 were identical.

Comparator verdict: `review`, tier `contested`. There were 204
`differing_conflict` rows, all in `charttime`; no only-oracle, only-candidate,
or differing-null-only rows. Candidate charttimes were consistently one hour
ahead of the oracle, requiring ETL diagnosis before any judge referral.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- `hpc_job.json` (job `29719894`)
