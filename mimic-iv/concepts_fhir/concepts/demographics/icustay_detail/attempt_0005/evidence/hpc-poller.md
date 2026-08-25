# HPC poller evidence — `icustay_detail`

Slurm job `30484359` completed successfully (three mechanical polls; Slurm
elapsed time 24 seconds) and produced a valid full comparison. The verdict was
`review`, tier `contested`, with both `diagnostician_required` and
`judge_required` true. The schema matched and both sides had 73,181 rows.

The keyed diff used `stay_id` and reported:

- 11,501 `differing_conflict` rows on `race`;
- 61,680 `differing_null_only` rows on the declared unrepresentable
  `hospital_expire_flag`;
- no only-oracle or only-candidate rows;
- 0/73,181 total identical rows, and 61,680/73,181 (84.28%) identical on
  representable columns.

DST conflict attribution was attempted but explained zero rows; the residual
  is the race conflict. Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
