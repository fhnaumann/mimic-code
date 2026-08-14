# HPC-poller evidence — creatinine_baseline attempt_0001

Job `29959342` completed and the poller fetched `comparison.full.json`,
`run_meta.full.json`, and `hpc_accounting.json`; there was no crash evidence.
The full comparator returned `review`, tier `contested`, with
`judge_required: true` and `diagnostician_required: true`.

Schema and row count matched: 431,231 candidate rows versus 431,231 oracle
rows, with the seven expected columns/types. The keyed diff on `hadm_id` found
430,771 identical rows and 460 `differing_conflict` rows (99.8933% identical).
Conflicts were `age` 460, `mdrd_est` 460, and `scr_baseline` 85; there were no
missing, candidate-only, or null-only rows. Comparator attribution was not
attempted because this output has no datetime column. Slurm elapsed time was
83 seconds.

Artifacts:
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in
this attempt directory.
