# HPC poller evidence

- Concept: `phenylephrine`; attempt: `0002`; job `29938368`.
- Poll outcome: complete; Slurm state: COMPLETED.
- Comparator verdict: `review`, tier `contested`, classification `paired_residual`; both judge and diagnostician are required.
- Oracle and candidate each have 193,260 rows. The declared `linkorderid` gap is typed NULL; representable-column identity is 191,421/193,260 (99.05%).
- Remaining classes: 1,838 `differing_conflict` rows (starttime 1,821; endtime 1,820; vaso_amount 1,748), plus one row-level `vaso_rate` `differing_null_only`; 46 conflicts were attributed to the known DST cast and 1,792 remained unexplained.
- Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
