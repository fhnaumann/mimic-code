## Evidence

Job `29732019` completed normally after two polls; `hpc_accounting.json` records Slurm COMPLETED and 83 seconds elapsed. The fetched full comparator is `comparison.full.json`, with `run_meta.full.json` and accounting metadata. Schema matched exactly for `[subject_id, stay_id, charttime, icp]` and the keyed comparison used `[subject_id, charttime]`. The verdict is `review`, tier `contested`, with diagnostician and judge both required. Oracle rows: 173273; candidate rows: 173239; identical rows: 173223 (99.97%); divergence is 38 `only_oracle`, 4 `only_candidate`, and 12 `differing_conflict` on `icp`. The row count was reported but not gated. No datetime column was present, so DST attribution was not attempted.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0001/`.
