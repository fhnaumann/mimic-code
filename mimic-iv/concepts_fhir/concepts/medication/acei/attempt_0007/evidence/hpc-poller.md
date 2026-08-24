## Evidence — hpc-poller, acei attempt 0007

Slurm job `30483991` completed successfully (`ElapsedRaw=29` seconds), and
`comparison.full.json` was fetched. The comparator verdict is `review`, not a
mechanical mismatch: schema matched, the tier is `gap_shaped`,
`diagnostician_required=false`, and `judge_required=true`.

Oracle and candidate row counts were both 112,014 (reported, not used as a
gate). The unkeyed residual was paired on `acei`, `hadm_id`, and `subject_id`.
There were 102,955 identical rows (91.91%) and 9,059 paired
`differing_null_only` rows: candidate `starttime` was NULL for 9,058 and
candidate `stoptime` was NULL for 9,051. There were zero `only_oracle`,
`only_candidate`, or `differing_conflict` rows. The candidate's
`patient_key`/`encounter_key` provenance columns were present and accepted by
the schema gate.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt.
