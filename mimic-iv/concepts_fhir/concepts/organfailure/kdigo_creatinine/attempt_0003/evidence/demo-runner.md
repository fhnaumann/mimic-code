## Demo-runner evidence

- Read: the replay attempt artifacts and `shape.demo.json` target contract; executed the prescribed embedded Spark/Pathling demo for `kdigo_creatinine`.
- Checked: execution completed successfully; all six oracle columns matched (`hadm_id`, `stay_id`, `charttime`, `creat`, `creat_low_past_48hr`, `creat_low_past_7day`); required resource key columns were present; all types were compatible after normalization.
- Result: `shape_ok`, with 1,272 demo rows. Row count was observed but not gated.
- Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt directory.
- Dataset-wide quirk check: no new dataset/IG-level quirk was reported; no `MIMIC_NOTES.d` entry appended.
