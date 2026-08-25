# Full-data poll and comparator evidence

Slurm job `30486709` completed successfully and the comparison artifacts were fetched. The candidate schema matched the oracle and row counts were equal at 3,321,747 (reported, not a gate). The comparator verdict is `review`, tier `contested`: 3,321,746 rows are identical and one row differs only in `uo_mlkghr_24hr`, candidate `0.0312` versus oracle `0.0313`, at `stay_id=31463721`, `charttime=2174-05-12T20:40:00`. `judge_required` and `diagnostician_required` are true; `attributed` is empty and conflict attribution was not attempted because the concept has no datetime output column. The judge bar requires a cited upstream ETL transformation proving the oracle value is unrecoverable, otherwise this is a port bug.

Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
