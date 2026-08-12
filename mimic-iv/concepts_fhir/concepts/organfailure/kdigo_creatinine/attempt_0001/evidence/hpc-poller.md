# HPC-poller evidence

Slurm job `29786665` completed normally. The full comparator fetched schema-identical output with 599,607 candidate rows and 599,607 oracle rows. Verdict: `review`, tier `contested`, classification `paired_residual`. There were 160 `differing_conflict` rows: `charttime` 145, `creat_low_past_48hr` 17, `creat_low_past_7day` 9, and `creat` 1; 599,447 rows were identical. The comparator replayed 138 conflicts to the upstream DST cast but left 22 unexplained, so `diagnostician_required` and `judge_required` are both true. No mismatch or execution failure occurred.

Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_creatinine/attempt_0001/`.
