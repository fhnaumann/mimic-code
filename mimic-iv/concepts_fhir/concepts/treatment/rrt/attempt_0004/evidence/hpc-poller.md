## Full-data poll — concept `rrt`, attempt 0004

- Poll outcome: `complete`; Slurm job `30237125` ended `COMPLETED` with no fatal markers.
- Runtime: 181 seconds from `hpc_accounting.json`; `run_meta.full.json` reports 177.13 seconds execute and 1.37 seconds compare.
- Comparator verdict: `review`, not a failed port.
- Schema identity: match. The five manifest columns have compatible types; `icu_encounter_key` and `patient_key` are the required extra key columns.
- Row counts (reported, not gated): oracle 2,827,715; candidate 2,827,507; delta -208.
- Classification: `unavailable_no_key`; comparison mode is full-tuple multiset.
- Tier: `contested`.
- Divergence: `only_oracle` 449 (gap-shaped), `only_candidate` 241 (contested/blocking); residual did not pair (`anchored: false`, 0 paired); `attributed: []`; `unresolvable: []`; no declarations.
- Routing flags: `divergence.judge_required: true`; `divergence.diagnostician_required: true`.

Artifacts fetched:
- `mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0004/hpc_accounting.json`

The contested review requires diagnosis before convening the equivalence judge. No new job or implementation change was made by the poller.
