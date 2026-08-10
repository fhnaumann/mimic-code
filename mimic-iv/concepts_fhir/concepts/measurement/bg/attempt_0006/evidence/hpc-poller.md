# Evidence: hpc-poller (`bg`, attempt_0006)

Poll outcome: `complete` for Slurm job `29597031`; the comparison artifacts
were fetched from the full-data run. Execution succeeded with embedded
Pathling/Spark.

Comparison verdict: `review`, tier `contested`, classification
`unavailable_no_key`. Schema matched all 27 columns and row counts matched
(candidate 511,637; oracle 511,637; delta 0; row count not gated). The
full-tuple multiset reports 70 `only_candidate` and 70 `only_oracle` rows
(0.014%); keyed conflict/null classes are unavailable because `bg` has no
unique natural key. The result is reviewable, not a crash, timeout, or machine
`mismatch`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/run_meta.full.json`

The prior attempt-0005 diagnosis already identified and cited the relevant
upstream ETL transformation for this expected residual (DST-gap timestamps and
the comments fallback), and the current 70-row result is the predicted
post-fix residual. The equivalence judge is required; no implementation
artifacts or `MIMIC_NOTES.md` were modified.
