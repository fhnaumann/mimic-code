# HPC/full-data evidence — milrinone attempt 0003

- Slurm job `30472380` completed normally; full artifacts were fetched.
- Comparator verdict: `review`, tier `gap_shaped`; schema matched and the
  keyed row-level comparison used `(stay_id, starttime)`.
- Oracle and candidate each contained 9,573 rows. The row count was reported,
  not gated.
- The sole divergence was `differing_null_only` on `linkorderid` for 9,573
  rows. `differing_conflict`, `only_oracle`, and `only_candidate` were all 0.
- The declaration was confirmed: `linkorderid` is 100% NULL in the candidate.
  All 9,573 rows matched on the representable columns (100% representable
  fidelity); the all-column identical count is 0 because the declared column
  differs by design.
- `diagnostician_required` was false and `judge_required` true, so this result
  routes directly to the equivalence judge.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
