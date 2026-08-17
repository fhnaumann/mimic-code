# HPC poller evidence

- Concept: `dobutamine`
- Attempt: `0003`
- Job: `30056911`; poll outcome `complete` with Slurm state `COMPLETED`; fresh comparison fetched.
- Comparator verdict: `review`, tier `gap_shaped`; schema matched and row count was 8,513 vs 8,513 (reported, not gated).
- Divergence: 8,511 `differing_null_only` rows for declared `linkorderid` (no FHIR element/ETL representation); 1 `differing_conflict` on `endtime`, plus 1 `only_oracle` and 1 `only_candidate` on the `(stay_id,starttime)` key. All three DST-related rows were machine-attributed completely to `upstream_timestamptz_dst_shift`, with zero residual; `diagnostician_required=false`, `judge_required=true`.
- Representable fidelity: 8,511/8,513 (99.98%); schema/key columns were present.
- Timing: Slurm elapsed 25 seconds; execution 21.695 seconds and comparison 0.889 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`, and `hpc_job.json` in this attempt directory. Because the comparator supplied complete attribution, no diagnostician was spawned; the equivalence judge is still mandatory.
