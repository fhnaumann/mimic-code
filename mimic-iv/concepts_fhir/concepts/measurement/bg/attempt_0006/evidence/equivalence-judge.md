# Evidence: equivalence-judge (`bg`, attempt_0006)

Judge verdict: `accept` for the `review`, tier `contested`, classification
`unavailable_no_key` result.

The current full result has exact schema and equal row counts of 511,637, with
70 `only_candidate` and 70 `only_oracle` full-tuple substitutions. Because bg
has no natural key, these are not 140 independent rows and the judge reasoned
with less evidence; the exact multiset overlap is 511,567/511,637 (99.9863%),
reported descriptively rather than as a keyed fidelity figure.

The acceptance cites the upstream rewrite: `mimic-fhir/sql/fhir_observation_labevents.sql:15`
and `:121`, `fhir_observation_chartevents.sql:9` and `:67`, and
`mimic-fhir/sql/fhir_specimen_lab.sql:18` and `:58` cast source chart times
through `TIMESTAMPTZ` before writing FHIR effective/collection times. DST-gap
wall times are normalized irreversibly; FHIR retains only the normalized value,
and the specimen time repeats the same transform. `Observation.issued` is
storetime, not charttime, so no FHIR query can recover the original wall time
or exact chart-window ordering. The comments fallback at
`fhir_observation_labevents.sql:133-136` is handled by `NULLIF(value_string, '___')`.

Attempt 0003's 71 residual substitutions (70 DST-related, one comments
fallback), attempt 0005's table-wide timestamp regression diagnosis, and the
current attempt 0006 result (exactly 70 residuals after the fixes) support this
intrinsic-loss explanation. Direct NTZ handling, exact itemids, specimen spine,
polymorphic projections, and all recorded workarounds were applied. Divergent
dependencies: none (`[]`).

The residual affects 70/511,637 substitutions, approximately 0.01368% (0.014%).
The judge accepts the divergence as intrinsic upstream ETL transformation loss;
the port is faithful as the transformed data allows. No `MIMIC_NOTES.md` entry
was added or updated.
