## Evidence

Slurm job `29950922` completed and the poller fetched a fresh full comparison
for attempt 0003.  The schema matched.  The comparator returned `review`, tier
`contested`, classification `unavailable_no_key`, with both
`judge_required: true` and `diagnostician_required: true`; no comparator
attribution was available.  Oracle rows: 2,827,715.  Candidate rows:
2,827,507 (row count is reported, not gated).  The unkeyed residual contains
449 `only_oracle` and 241 `only_candidate` rows, with no residual pairing.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
