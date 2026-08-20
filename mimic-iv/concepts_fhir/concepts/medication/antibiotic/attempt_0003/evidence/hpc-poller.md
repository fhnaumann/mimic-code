# HPC-poller evidence

Job `30230408` completed successfully after two polls; Slurm accounting reports
68 seconds elapsed. The fresh full artifacts are
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in
attempt 0003.

Comparator verdict: `review`, not failure. Schema matched and row counts were
oracle 735,462 / candidate 735,462 (delta 0; row count is non-gating). The
candidate had 691,939 identical rows (94.08%) and 43,523 differing rows.

The divergence is `contested`; `judge_required` and
`diagnostician_required` are true. The artifact reports 43,453
`differing_null_only` rows involving omitted prescription validity endpoints
and ICU assignment, plus 70 `differing_conflict` rows (52 start-time and 23
stop-time conflicts). 67 conflicts are attributed by the comparator to the
upstream New York DST cast, leaving 3 unexplained residual conflicts, so this
is not the `attributed` tier. The unkeyed residual was paired by the comparator
and is not evidence of invented rows. No semantic interpretation was made by
the poller.
