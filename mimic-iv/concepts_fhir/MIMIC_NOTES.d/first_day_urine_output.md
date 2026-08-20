## Outputevents effective timing is dateTime-only in the authoritative Delta
- Affected: `Observation.effective[x]` for the outputevents stream
- Verified: `first_day_urine_output` attempt 0001 embedded Pathling 9.6.0/Spark 4.0.2 projection over `/Users/nau025/warehouses/mimic-iv-demo/delta` counted 24,642 `mimic-d-items` rows/resources at ratio 1.000; the exact twelve-code urine subset was 7,349/7,349 `effective.ofType(dateTime)`, 0/7,349 `effective.ofType(Period).start`, 0/7,349 `.end`, and 0/7,349 `effective.ofType(instant)`.

## Outputevents TIMESTAMPTZ normalization can affect first-day aggregation
- Affected: `Observation.effectiveDateTime` from outputevents and any dependency/window/grouping using its `charttime`, including `first_day_urine_output`
- Verified: `first_day_urine_output` attempt 0001 checked `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60`; the demo had exact source/FHIR wall-time keys for 7,349/7,349 target events and exact first-day aggregates for 140/140 ICU stays, but the ETL casts `charttime` through `TIMESTAMPTZ`, so a spring-forward 02:xx wall time can be irreversibly written as 03:xx. The demo probe found 334 target source rows in the 02:xx hour; no changed demo key was observed. The original wall time must not be recovered from an opaque resource id.
