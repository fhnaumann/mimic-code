## Evidence

The existing Slurm job `29949869` completed and the poller fetched a fresh full
comparison.  The schema matched.  The comparator returned `review`, tier
`contested`, classification `unavailable_no_key`, with
`judge_required: true` and `diagnostician_required: true`; no attribution was
attempted by the comparator.  The oracle has 2,827,715 rows and the candidate
2,827,135 (row count is reported, not gated).  The unkeyed residual contains
821 `only_oracle` and 241 `only_candidate` rows, with no residual pairing.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
