# HPC poller evidence

Concept: `dobutamine`  
Attempt: `0002`  
Job: `29724469`  
Outcome: `complete`

The full-data job completed normally in 24 seconds and fetched a fresh
`comparison.full.json`. Schema identity passed and both sides had 8,513 rows
(row count reported only, never gated). The verdict was `review`, not a
machine `mismatch`.

The comparator reported a `contested` tier with both
`judge_required: true` and `diagnostician_required: true`. Divergence included
the declared `linkorderid` gap (1 `only_oracle` and 8,511
`differing_null_only`) and one endtime `only_candidate`; the one conflicting
endtime row was also fully replayed as an upstream DST-shift attribution.
Representable fidelity was 8,511/8,513 (99.98%), excluding the declared
unrepresentable column. Because `diagnostician_required` is true, the
diagnostician must inspect the residual contested classification before the
judge.

Fetched artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
