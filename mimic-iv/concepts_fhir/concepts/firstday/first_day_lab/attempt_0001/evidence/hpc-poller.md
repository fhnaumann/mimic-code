## Evidence

Poll of job `30307179` completed after four poll cycles with no fatal marker.
The comparator verdict is `match` for `first_day_lab` attempt `0001`.

`comparison.full.json` reports schema match, keyed join on `stay_id`, and
73,181 candidate rows versus 73,181 oracle rows (row count reported but not
gated). All 73,181 rows reproduced identically; there are zero
`only_oracle`, `only_candidate`, `differing_null_only`, or
`differing_conflict` rows. There is no divergence tier, declaration, judge,
or diagnostician requirement. No retry is needed.

Slurm accounting reports `COMPLETED`, `ElapsedRaw=690` seconds. Full-run
artifacts are:

- `mimic-iv/concepts_fhir/concepts/firstday/first_day_lab/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_lab/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_lab/attempt_0001/hpc_accounting.json`

The candidate Parquet remains on scratch by design.
