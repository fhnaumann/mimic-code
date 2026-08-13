# HPC-poller evidence

Slurm job `29883658` completed successfully and fetched a full comparison. The comparator verdict is `review`, tier `gap_shaped`, with schema match and equal reported row counts (oracle 9,573; candidate 9,573). It reports 9,569 `differing_null_only` rows on declared `linkorderid`, which is absent from ICU MedicationAdministration and therefore gap-shaped. It also reports 2 `differing_conflict`, 2 `only_oracle`, and 2 `only_candidate` rows attributed completely to the upstream DST cast; the attributed endtime example is candidate 03:05 versus oracle 02:05. No contested or blocking divergence remains. `diagnostician_required` is false and `judge_required` is true.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `attempt_0001/`. Slurm elapsed time was 27 seconds. The full result must go to the equivalence judge; this review is not a terminal match.
