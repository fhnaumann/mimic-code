## Outputevents Observations use dateTime-only effective timing
- Affected: `Observation.effective[x]` for the outputevents stream
- Verified: `urine_output` embedded Pathling/Spark projection over the authoritative demo Delta counted 24,642 `mimic-d-items` Observation rows/resources with `effective.ofType(dateTime)` populated 24,642/24,642, `effective.ofType(Period).start` and `.end` 0/24,642, and `effective.ofType(instant)` 0/24,642; the exact urine-output subset was 7,349/7,349 dateTime and 0/7,349 for every other variant. This is a provisional stream-wide finding for later outputevents concepts.

## Outputevents effectiveDateTime irreversibly normalizes DST-gap charttime
- Affected: `Observation.effectiveDateTime` and any outputevents concept grouped or keyed by charttime.
- Verified: `urine_output` attempt_0002 full-data comparison attributed 393 shifted keys and 232 aggregation conflicts with zero residual; `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65` casts outputevents charttime through `TIMESTAMPTZ` before writing effectiveDateTime, so original spring-forward-gap wall times are unrecoverable. The equivalence judge accepted the intrinsic divergence at 0.0118% of oracle rows.
