Evidence block:

- HPC job `29603036` completed successfully after four polls; `comparison.full.json` and `run_meta.full.json` were fetched into attempt 0001.
- Comparator verdict: `review`, comparator `full_tuple_multiset`, classification `unavailable_no_key`. Schema matched exactly across all seven columns and the reported row count matched (735,462 vs 735,462); row count is not a gate.
- Diff: 43,576 `only_candidate` and 43,576 `only_oracle` rows (5.925%); with no unique key these cannot be separated into invented rows versus NULL-for-value divergence. Sample candidate rows have NULL `starttime`/`stoptime`/`stay_id` where oracle values exist.
- Tier is `contested` with `judge_required: true`; this must go through mismatch diagnosis before equivalence judging because the no-key classification includes an apparent contested class.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and existing `submit.slurm`/`hpc_job.json` under the attempt directory. No implementation artifacts were modified.
