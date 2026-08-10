# Evidence: hpc-poller (`bg`, attempt_0005)

Poll outcome: `complete` for Slurm job `29592332`; comparison artifacts were
fetched. The full run used embedded Pathling on Spark and completed execution
and comparison successfully.

Verdict: `review`, tier `contested`, classification
`unavailable_no_key`. `bg` has no empirical full-data natural key, so the
full-tuple multiset comparison cannot distinguish `only_oracle` from
`only_candidate` when rows differ. Both classes were reported at 511,637; no
keyed conflict/null classes were available. The artifact requires an
equivalence judge, but because the tier is contested it first requires a
diagnosis with an upstream ETL citation.

Hard gates passed: schema matched all 27 columns/types and row count was
511,637 on both sides (reported only, not gated). The run was not a
`mismatch`, crash, or timeout.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/run_meta.full.json`

No implementation artifacts or `MIMIC_NOTES.md` were modified.
