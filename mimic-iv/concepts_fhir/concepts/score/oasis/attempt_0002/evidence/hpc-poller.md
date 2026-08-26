# HPC-poller evidence

Concept: `oasis`; attempt: `0002`; job: `30542485`.

The sanctioned poll/fetch completed normally. Slurm state was `COMPLETED`,
with no fatal markers, and fresh comparison, run metadata, and accounting
artifacts were fetched. Slurm elapsed time was 679 seconds; execution was
673.804 seconds and comparison 1.734 seconds.

The comparator returned `review`, tier `contested`, with both
`judge_required: true` and `diagnostician_required: true`. Schema identity
passed, and candidate/oracle row counts were both 73,181. There were 73,127
identical rows and 54 `differing_conflict` rows (0.074% of oracle rows), all
on `electivesurgery`, `electivesurgery_score`, `oasis`, and `oasis_prob`; no
only-oracle, only-candidate, or null-only rows remained. Every residual row
had candidate elective flag 0 / score 6 versus oracle flag 1 / score 0, with
the OASIS total/probability differing consequently. Conflict attribution was
not attempted because the final output has no datetime column.

Artifacts fetched once:
`mimic-iv/concepts_fhir/concepts/score/oasis/attempt_0002/comparison.full.json`,
`run_meta.full.json`, and `hpc_accounting.json`. This is a legitimate review,
not a crash or mismatch; diagnosis is required before the judge.
