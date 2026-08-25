## HPC-poller evidence

- Read: `hpc_job.json` for the already-submitted job and fetched full-run artifacts.
- Checked: job `30484719` completed without fatal markers; `comparison.full.json` is fresh; schema matched; candidate and oracle both had 599,607 rows; full-tuple multiset diff had zero `only_oracle`, `only_candidate`, or conflicting rows.
- Result: comparator verdict `match`; no judge or diagnostician was required. The artifact notes the concept has no unique key, but there was no residual to classify.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory. Slurm elapsed time was 140 seconds.
- Dataset-wide quirk check: the run reconfirmed the already-recorded UTC rebuild correction for the historical labevents DST behavior; no new `MIMIC_NOTES.d` entry was appended.
