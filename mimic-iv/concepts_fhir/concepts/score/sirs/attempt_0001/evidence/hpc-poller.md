# HPC-poller evidence — sirs, attempt_0001

The poller used the job ID recorded in `hpc_job.json` (`30318343`) and polled
the CLI mechanism until normal completion. The job produced and fetched
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.

Full-data result: `review`, tier `contested`, keyed on `stay_id`; schema matched.
The candidate and oracle each had 73,181 rows. There were 73,177 identical
rows and four `differing_conflict` rows: `sirs` conflicted on four rows,
`heart_rate_score` on two, and `resp_score` on two. There were no
`only_oracle`, `only_candidate`, or `differing_null_only` rows. The artifact
sets `judge_required: true` and `diagnostician_required: true`; attribution was
not attempted because the output has no datetime column. The result requires
diagnosis before the equivalence judge.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
