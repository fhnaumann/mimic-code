# HPC poller evidence

Concept: `crrt`; attempt: `0005`; job: `29776881`.

- Poll outcome: `complete`; Slurm completed normally.
- Full comparator verdict: `match`.
- Schema matched exactly across 24 columns.
- Keyed diff on `(stay_id, charttime)`: 287,152 candidate rows and 287,152 oracle rows; 0 `only_oracle`, 0 `only_candidate`, 0 `differing_null_only`, and 0 `differing_conflict`.
- Identical fraction: 100%.
- No judge or diagnostician was required.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
