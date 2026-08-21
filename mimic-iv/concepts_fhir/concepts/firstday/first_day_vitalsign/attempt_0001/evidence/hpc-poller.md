# HPC poller evidence

`uv run mimic_utils hpc-poll first_day_vitalsign` polled the recorded Slurm
job `30308135` and completed cleanly, fetching a fresh full comparison. The
poll outcome was `complete`, while the comparator verdict was `review` with
`divergence.tier: contested`, `judge_required: true`, and
`diagnostician_required: true`.

The schema matched and both candidate and oracle had 73,181 rows (row count is
report-only). The keyed diff reproduced 72,998 rows identically (99.75%) and
had no `only_oracle`, `only_candidate`, or `differing_null_only` rows. It had
183 `differing_conflict` rows (0.250%), concentrated in aggregate columns:
`resp_rate_mean` 152, `heart_rate_mean` 141, `mbp_mean` 128,
`dbp_mean` 125, `sbp_mean` 121, with smaller conflicts in the other vital
aggregates. Conflict attribution was not attempted because the target output
has no datetime column. The full result requires diagnosis before the judge.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_vitalsign/attempt_0001/hpc_accounting.json`
