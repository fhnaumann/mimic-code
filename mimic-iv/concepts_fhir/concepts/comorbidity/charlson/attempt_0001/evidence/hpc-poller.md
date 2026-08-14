# HPC-poller evidence — charlson attempt 0001

Slurm job `29957224` completed successfully and produced a fresh full-data
comparison. The candidate executed with embedded Pathling/Spark; schema matched
all 21 INTEGER columns and row counts were 431,231 on both sides (reported,
not gated). The keyed comparator used `hadm_id` and returned `review`, tier
`contested`, with `diagnostician_required: true` and `judge_required: true`.
It found 431,170/431,231 identical rows (99.9859%), no missing or invented
rows, and 61 `differing_conflict` rows affecting only `age_score` and
`charlson_comorbidity_index`; each candidate age score is one higher in the
reported samples. DST attribution was not attempted because no datetime output
column exists.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- `candidate.full.parquet` remains on scratch

The result is a review, not a failure or match. It requires diagnosis before
the equivalence judge under the contested bar.
