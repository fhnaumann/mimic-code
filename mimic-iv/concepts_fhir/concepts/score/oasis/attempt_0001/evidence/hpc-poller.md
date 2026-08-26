# HPC-poller evidence

Concept: `oasis`; attempt: `0001`; job: `30537656`.

The sanctioned poll/fetch completed successfully with no fatal markers. The
full embedded Pathling/Spark execution and comparator produced fresh
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
Slurm accounting reports 629 seconds elapsed; execution was 623.385 seconds
and comparison 1.465 seconds.

The full comparator verdict is `review`, tier `contested`, with
`judge_required: true` and `diagnostician_required: true`. Schema identity
passed, with all 25 oracle columns and the three required key columns present
at compatible types. Oracle and candidate each have 73,181 rows. There are
69,465 identical rows (94.922%) and 3,716 `differing_conflict` rows, with no
missing or candidate-only rows. Conflicts are `electivesurgery` (3,349),
`electivesurgery_score` (3,349), `oasis` (3,349), `oasis_prob` (3,349), and
`preiculos` (373). Upstream conflict attribution was not attempted because
the final output has no datetime column.

Artifacts fetched once:
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0001/comparison.full.json`,
`run_meta.full.json`, and `hpc_accounting.json` (with the pre-existing
`hpc_job.json`). A review is not a failure; the next required stage is
diagnosis before convening the equivalence judge.
