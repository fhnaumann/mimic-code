# Evidence: hpc-poller — chemistry attempt 0004

Job `30104200` completed cleanly on Petrichor. The poll fetched
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`; the
candidate Parquet remains on scratch. Slurm accounting reports 118 seconds.

Full comparator verdict: `review`, tier `attributed`. Schema identity passed
for the 19-column candidate shape. The keyed comparison on `specimen_id`
reported 3,811,325 identical rows of 3,811,523, with 198
`differing_conflict` rows on `charttime` only. There were zero
`only_oracle`, `only_candidate`, or null-only rows, and the residual was zero.

The comparator replayed `upstream_timestamptz_dst_shift` for every one of the
198 conflicts, with `America/New_York` and no residual. It therefore set
`divergence.diagnostician_required` to false and
`divergence.judge_required` to true. The cited upstream ETL paths are recorded
in `comparison.full.json` and include
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121` and
`mimic-fhir/sql/fhir_specimen_lab.sql:18,58`.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

This is a successful full run with a review verdict, not a failed job and not
yet a terminal concept state. The diagnostician is intentionally skipped by
the machine attribution; the equivalence judge is mandatory.
