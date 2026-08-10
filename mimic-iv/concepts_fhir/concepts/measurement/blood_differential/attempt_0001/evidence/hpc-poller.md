## Evidence

Job `29674397` completed after two polls and produced fresh full-data artifacts. The comparator verdict is `review`, not failure, with tier `contested`; schema identity passed for all 20 columns.

The keyed diff on natural key `specimen_id` found 3,171,706 identical rows, 200 `differing_conflict` rows all on `charttime`, and 5 `only_candidate` rows. There were no `only_oracle` or `differing_null_only` rows. Oracle row count was 3,171,906 and candidate row count 3,171,911; row count was not gated. The 200 charttime conflicts are uniformly +1 hour on the candidate side and require upstream ETL diagnosis before any judge. The five candidate-only rows remain contested and require diagnosis.

Artifacts: `comparison.full.json` and `run_meta.full.json` under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0001/`; job ledger is `hpc_job.json`.
