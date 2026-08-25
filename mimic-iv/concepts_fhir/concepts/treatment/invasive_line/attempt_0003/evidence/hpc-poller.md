# Full-data poll evidence

- Concept: `invasive_line`; attempt `0003`; Slurm job `30484720`.
- Poll outcome: `complete`; Slurm state `COMPLETED`; elapsed 23 seconds.
- Comparator verdict: `review`, not `match` or `mismatch`.
- Schema matched and row counts were equal (93,378 candidate and oracle); row count was informational only.
- Divergence: `contested`, `paired_residual`; `differing_conflict` 657 rows (0.704%), all on `line_site`; no gap-shaped or attributed classes.
- Identical rows: 92,721 / 93,378 (99.2964%). Residual pairing was anchored on `stay_id`; substitutions differed only by trailing whitespace in `line_site`.
- Comparator states diagnosis and judge are required. The conflict attribution replay was not attempted because this concept has no datetime column.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`.
