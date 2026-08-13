# Equivalence judge evidence — gcs

The independent equivalence judge returned `blocked` for the `review`,
`contested` full-data result.

The cited upstream statement is
`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80`: numeric chartevents
write `Observation.valueQuantity` and discard source text, so `No Response`
and `No Response-ETT` both become Quantity 1. The direct string path is empty
for these rows, and resource IDs are opaque and cannot be used to invert the
loss.

The canonical `gcs.sql:33,45,62-95` uses the lost distinction for
`gcs_verbal`, `gcs_unable`, total GCS, and six-hour carry-forward. This is
essential clinical loss, not an ancillary column gap, so the judge ruled that
publishing the partial table would conceal semantic ambiguity.

Full-data evidence: 576,086 `differing_conflict` rows, 74 `only_candidate`,
98 `only_oracle`, 64.82% identical. Comparator key replay attributes 74
candidate/oracle pairs to chartevents datetime normalization at
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`; 24 collision residuals
remain. No divergent dependencies.
