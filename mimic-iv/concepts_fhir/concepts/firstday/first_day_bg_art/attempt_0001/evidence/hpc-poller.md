Evidence block — `first_day_bg_art`, attempt `0001`.

Job `30241548` completed normally and the fresh full-data artifacts were fetched. `comparison.full.json` is a deterministic `match`: schema matched, all 46 expected/output columns including the two required FHIR resource keys were present, and the keyed comparison on `stay_id` reproduced 73,181/73,181 rows identically. There were zero `only_oracle`, `only_candidate`, `differing_conflict`, or `differing_null_only` rows; `identical_fraction` was 1.0 and no judge or diagnostician was required. Slurm accounting reports 224 seconds elapsed; `run_meta.full.json` reports 219.118 seconds execute and 1.717 seconds compare.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg_art/attempt_0001/`. No notes fragment entry was needed.
