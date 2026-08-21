# Mismatch-diagnostician evidence — sirs, attempt_0001

The diagnostician inspected the full comparison, SIRS SQL/ViewDefinitions,
dependency artifacts/states, canonical notes, and upstream `mimic-fhir` SQL.
It classified the `review` as upstream transformation loss, not a SIRS port
bug. Four source charttime collision groups (eight raw rows) were shifted from
the DST spring-forward 02:00 hour to occupied 03:00 keys by
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`. The resulting
`vitalsign` aggregation changed maxima in four stays, crossing the strict SIRS
heart-rate/respiratory thresholds and producing exactly the four conflicting
SIRS rows: two `heart_rate_score`, two `resp_score`, and four `sirs`, with zero
residual divergence rows.

The original wall times are absent from semantic FHIR elements; `issued` is
storetime and resource IDs are opaque, so no valid query can recover them.
`mimic-fhir/sql/fhir_encounter_icu.sql:31,98` was checked and did not affect
these rows. `first_day_bg_art` and `first_day_lab` are exact dependencies; the
divergence is inherited from the judge-accepted `first_day_vitalsign`.
No carryover stage is at fault, no invalidation/retry is required, and no
fragment was appended. Per the contract, the upstream DST exception is not
essential-loss blocking; the equivalence judge must make the terminal semantic
decision.
