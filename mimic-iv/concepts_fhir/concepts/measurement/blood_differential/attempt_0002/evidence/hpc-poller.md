## Evidence

Job `29676498` completed and fresh full artifacts were fetched. The comparator verdict is `review`, tier `contested`; this routes to the equivalence judge after the prior diagnosis supplied the required ETL citation.

Schema identity passed for all 20 columns. Row counts matched exactly at 3,171,906 on both sides, but row count was not used as a gate. The keyed diff on `specimen_id` found 3,171,706 identical rows and 200 `differing_conflict` rows, all on `charttime`, with no `only_oracle`, `only_candidate`, or `differing_null_only` rows. The residual is the known +1-hour DST normalization from upstream ETL.

Artifacts: `comparison.full.json` and `run_meta.full.json` under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0002/`; job ledger is `hpc_job.json`.
