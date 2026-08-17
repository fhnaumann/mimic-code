# HPC-poller evidence

The recorded Slurm job `30058287` for `kdigo_creatinine` attempt 0002 completed normally. A fresh `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` were fetched.

The full comparator returned `review`, tier `contested`, classification `paired_residual`, with both `judge_required: true` and `diagnostician_required: true`. Schema matched, including the six oracle columns; the three required opaque key columns were present as informational extras. Oracle and candidate each had 599,607 rows. There were 599,453 identical rows and 154 `differing_conflict` rows: `charttime` 145, `creat_low_past_48hr` 12, and `creat_low_past_7day` 4. No gap-shaped class was present. Attribution replayed 138 rows to the upstream New York DST cast, leaving 16 residual rows, so the result remains contested and requires diagnosis before the judge.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0002/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0002/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0002/hpc_accounting.json`
