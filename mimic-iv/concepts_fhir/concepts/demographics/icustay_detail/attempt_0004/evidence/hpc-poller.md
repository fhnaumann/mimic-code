# HPC-poller evidence — `icustay_detail`, attempt 0004

- Slurm job `30072022` completed successfully; accounting recorded 27 seconds elapsed.
- Full candidate and comparator artifacts were fetched. The comparator verdict is `review`, not a mechanical mismatch.
- Candidate and oracle each contain 73,181 rows; row count was reported only and not gated. Schema matched, with the three required paired key columns present.
- Divergence tier: `contested`; `judge_required: true`; `diagnostician_required: true`.
- `differing_conflict`: 11,594 rows: `race` 11,501, `admission_age` 86, `icu_intime` 10, `los_icu` 10, `admittime` 7, and `dischtime` 1.
- `differing_null_only`: 61,587 rows, all on declared typed-NULL `hospital_expire_flag`.
- Comparator DST attribution was incomplete: 2 of 11,594 conflicts replayed; 11,592 remained for diagnosis. No only-oracle or only-candidate rows occurred.
- Representable identical rows: 61,587/73,181 (84.16%), excluding the declared unrepresentable column.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- `hpc_job.json`
