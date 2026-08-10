# HPC poll evidence

- Read: `hpc_job.json`, completed job 29589053, `comparison.full.json`, and `run_meta.full.json` for attempt 0003.
- Result: outcome `complete`; the full-data execution and comparator succeeded mechanically. Verdict is `review`, tier `contested`, classification `unavailable_no_key`.
- Checks: row counts match exactly (511,637 each); all 27 columns and types match. The unkeyed full-tuple diff contains 71 `only_oracle` and 71 `only_candidate` rows (0.014% of oracle rows); identical rows cannot be counted with a natural key absent.
- Route: contested review requires diagnosis before the equivalence judge. The 71-row residual is to be checked against the prior diagnosed timestamp/precision causes and upstream ETL citations.
- Full-data runs consumed: 2 of the 10-run cap.
- Artifacts: `comparison.full.json`, `run_meta.full.json`.
- Shared knowledge read: existing `MIMIC_NOTES.md` entries; no new promotion by the mechanical poll stage.
