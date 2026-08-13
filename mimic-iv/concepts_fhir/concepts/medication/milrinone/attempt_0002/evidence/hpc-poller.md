# HPC-poller evidence

Attempt 0002 Slurm job `29886910` completed and fetched the full comparison. The verdict is `review`, tier `gap_shaped`, with schema match and equal row counts (9,573 each). Divergence is 9,569 `differing_null_only` rows on declared-unrepresentable `linkorderid`; 2 `differing_conflict` rows on `endtime`, 2 `only_oracle`, and 2 `only_candidate` key rows are all fully attributed to the upstream America/New_York DST shift with zero residual. The corrected citation set now includes `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`. `judge_required` is true and `diagnostician_required` is false.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `attempt_0002/`; Slurm elapsed time was 27 seconds. The review proceeds directly to the equivalence judge.
