Evidence block — hpc-poller

Polled job `30049268` for `first_day_bg`, attempt `0001`, with `uv run mimic_utils hpc-poll first_day_bg`; outcome `complete` after 2 polls. The full run succeeded but comparator verdict was `review` (exit class 2), not failure.

Full comparison:
- Tier: `contested`
- `judge_required: true`; `diagnostician_required: true`
- Candidate rows 73,181; oracle rows 73,181; delta 0 (row count not gated)
- Schema matched: 44 columns, no missing/extra/incompatible types
- Keyed diff on `[stay_id]`: 73,180/73,181 identical (`identical_fraction: 0.999986`)
- One `differing_conflict` (0.001%) at `stay_id=33143532`, affecting `baseexcess_min`, `pco2_min`, `ph_max`, `po2_max`, and `totalco2_min` (one row each); no gap-shaped classes
- DST conflict attribution was not attempted because this concept has no datetime output
- Judge bar requires an upstream `mimic-fhir` ETL file/line citation and proof the oracle value is unrecoverable; without that citation the result is a bug

Slurm accounting: `hpc_accounting.json` reports 222 seconds elapsed, COMPLETED via `slurm_sacct`; `run_meta.full.json` reports 218.322 seconds execute and 1.799 seconds compare.

Artifacts:
- `attempt_0001/comparison.full.json`
- `attempt_0001/run_meta.full.json`
- `attempt_0001/hpc_accounting.json`

No implementation artifacts, notes, or commits were changed.
