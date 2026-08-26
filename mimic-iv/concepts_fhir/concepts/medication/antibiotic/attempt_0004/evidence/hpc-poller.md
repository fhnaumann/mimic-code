## Evidence

- Read: attempt_0004 replay artifacts and the full-run job record; polled job `30483909` with `uv run mimic_utils hpc-poll antibiotic`.
- Checked: Slurm completed successfully (68 seconds), and fresh `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` were fetched; this was not inferred from queue exit alone.
- Result: comparator verdict `review`, tier `gap_shaped`, classification `paired_residual`, `judge_required=true`, `diagnostician_required=false`. Schema matched. Oracle and candidate each had 735,462 rows (row count non-gating). The paired residual had 43,453 `differing_null_only` rows: candidate NULLs in `stoptime` (43,422), `starttime` (43,369), and `stay_id` (13,494); no conflicts or candidate-only/oracle-only rows after pairing. Identical rows: 692,009/735,462 (94.09%).
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory.
