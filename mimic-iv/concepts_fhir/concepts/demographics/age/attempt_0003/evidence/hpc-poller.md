# Evidence: hpc-poller

Job `30054194` for attempt_0003 completed cleanly (`complete`, Slurm
COMPLETED; 20 seconds) and fetched a fresh comparison. This is a comparator
review, not a failed port.

- Full verdict: `review`, tier `contested`.
- `schema.match`: true; required FHIR key columns are present.
- Oracle/candidate rows: 431,231 / 431,231 (row count is evidence only).
- `identical_rows`: 0 because the two declared all-NULL columns differ on
  rows where the oracle has values; `identical_representable_rows`: 430,727
  (99.88%).
- `differing_null_only`: 430,727, the declared/confirmed unrepresentable
  `anchor_age` and `anchor_year` gap.
- `differing_conflict`: 504: 460 `age` conflicts and 44 `admittime`
  conflicts. There are no only-oracle or only-candidate rows.
- `conflict_attribution` attempted but incomplete: 44/504 replay the known
  upstream DST cast; 460 age conflicts remain residual and unexplained.
- `divergence.judge_required`: true; `divergence.diagnostician_required`:
  true.

Artifacts fetched:

- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/hpc_accounting.json`

The contested residual must be diagnosed before convening the equivalence
judge. No retry or terminal state transition was made by the poller.
