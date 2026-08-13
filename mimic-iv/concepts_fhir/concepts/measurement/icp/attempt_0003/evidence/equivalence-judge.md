Evidence block

The independent equivalence judge returned `accept` for the `review`,
`contested` divergence. It confirmed 173,252/173,273 identical rows (99.9879%),
with 17 `only_oracle`, 2 `only_candidate`, and 4 `differing_conflict` rows on
`icp`. All 17 shifted source rows are explained by the New York spring-forward
normalization: two re-key to 03:10/03:20 and 15 collide at 03:00, changing four
grouped maxima.

The judge cited `Observation.effectiveDateTime`, projected through
`Observation.effective.ofType(dateTime)`, and
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`:
source `charttime` is cast through `TIMESTAMPTZ` and the normalized value is
written to FHIR. The original wall time is absent from admissible FHIR fields;
`issued` uses `storetime`, and UUID inversion is forbidden. The judge found the
non-inverting attempt faithful to the served representation and accepted the
intrinsic DST transformation. No new dataset-wide quirk was identified.
