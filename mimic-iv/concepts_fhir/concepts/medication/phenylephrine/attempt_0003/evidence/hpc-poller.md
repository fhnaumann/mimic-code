# HPC poller evidence

- Concept: `phenylephrine`
- Attempt: `0003`
- Checked: fetched full-data schema and keyed/paired residual comparison after Slurm job `30235403` completed; row count reported only, not used as a gate.
- Result: comparator verdict `review`, tier `contested`; schema matched. Oracle and candidate each had 193,260 rows. The comparison reported 1,838 `differing_conflict` rows (46 attributed to the DST replay, 1,792 residual), 191,422 `differing_null_only` rows including the declared all-NULL `linkorderid` gap and one row-level NULL `vaso_rate`, with 0 true unpaired rows. Representable fidelity was 191,421/193,260 rows (99.05%). `diagnostician_required=true`; `judge_required=true`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
- Dataset-wide notes: no new quirk appended at this stage.
