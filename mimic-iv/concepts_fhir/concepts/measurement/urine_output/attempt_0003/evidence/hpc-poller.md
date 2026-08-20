# Evidence: hpc-poller

Polled existing Slurm job `30220232` with `uv run mimic_utils hpc-poll urine_output`. Outcome was `complete`; Slurm state was `COMPLETED` with 91 seconds elapsed. The fetched comparator verdict was `review`, not a crash or mismatch.

Full comparison: oracle 3,321,748 rows, candidate 3,321,512 rows; schema matched. Identical rows: 3,321,123. Divergence classes: `only_oracle` 393, `only_candidate` 157, and `differing_conflict` 232; `differing_null_only` 0. The comparator reports tier `attributed`, replays every divergence to the upstream New York `TIMESTAMPTZ` DST-gap shift with zero residual, and sets `judge_required=true`, `diagnostician_required=false`. The 236 key collisions require the judge to confirm the concept's own aggregation explains the absorbed values.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
