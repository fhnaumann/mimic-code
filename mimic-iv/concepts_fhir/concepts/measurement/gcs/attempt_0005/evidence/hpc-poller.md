# HPC poller evidence — gcs

Slurm job `29874287` completed normally and the full comparison artifacts were
fetched. The mechanical verdict is `review`, not failure, with schema match
and keyed comparison classification `contested`.

Observed full-data counts: oracle 1,637,763 rows; candidate 1,637,739;
1,061,579 identical (64.82%); 576,086 `differing_conflict`; 74
`only_candidate`; 98 `only_oracle`. Conflicts are in `gcs`, `gcs_verbal`, and
`gcs_unable`. The comparator reports `judge_required: true` and
`diagnostician_required: true`; key-level DST replay accounts for 74 of 98
unpaired rows but does not explain the residual or the value conflicts.

Artifacts fetched under
`mimic-iv/concepts_fhir/concepts/measurement/gcs/attempt_0005/`:
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
