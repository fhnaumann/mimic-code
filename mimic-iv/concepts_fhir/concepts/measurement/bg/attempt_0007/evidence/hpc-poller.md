# Full-data poll evidence — `bg`, attempt 0007

Slurm job `30061464` completed successfully after the sanctioned polling flow;
no replacement job was launched. The fetched comparator verdict is `review`,
tier `contested`, with `diagnostician_required: true` and
`judge_required: true`. This is a semantic review, not a queue or execution
failure.

The candidate and oracle each contain 511,637 rows. The comparator reports
511,567 identical rows (99.9863%). It classified 70 value conflicts, including
70 on `charttime`, 6 on `fio2_chartevents`, 5 on `aado2_calc`, and 5 on
`pao2fio2ratio` (overlapping row incidences). The unkeyed residual was paired
and the 74 candidate-only tuples are substitution halves, not evidence of
invented rows.

The comparator replay attributed 64/70 conflicts to the known upstream
`TIMESTAMPTZ` DST transformation but marked attribution incomplete, leaving six
unexplained residual rows. Therefore the contested residual requires a
mismatch diagnostician before the equivalence judge.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- `hpc_job.json`
