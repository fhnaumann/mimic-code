# HPC poller evidence

Slurm job `30324549` for attempt_0002 completed cleanly after two mechanical
polls (186 seconds elapsed), and `comparison.full.json` plus
`run_meta.full.json` and `hpc_accounting.json` were fetched. This is a
comparator result, not a crash.

The full schema matched. The candidate had 619,350 rows versus 619,330 oracle
rows; row count is reported but not gated. Because the concept has no unique
key, comparison used a full-tuple multiset. The verdict was `review`, tier
`contested`, classification `unavailable_no_key`, with `judge_required=true`
and `diagnostician_required=true`. Divergence was 1,863 `only_candidate` rows
and 1,843 `only_oracle` rows; no residual pairing or attribution was available.
The comparator explicitly warns that unkeyed only-candidate rows can represent
NULL divergence or invented rows and cannot be separated mechanically. The
judge bar therefore requires an upstream mimic-fhir ETL citation for any
acceptance, and the contested result must be diagnosed before convening it.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in attempt_0002.
