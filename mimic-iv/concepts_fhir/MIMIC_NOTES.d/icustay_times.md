## Chartevents MIN/MAX can expose DST normalization after aggregation
- Affected: aggregates over `Observation.effectiveDateTime` from chartevents, including per-stay `MIN`/`MAX` endpoints
- Verified: `icustay_times` attempt_0002 full-data comparison found 7 residual `intime_hr` conflicts where a source spring-forward-gap `02:mm` minimum was normalized to `03:mm` and a genuine unchanged `03:00`/`03:02` row became the candidate minimum; one additional `outtime_hr` conflict was a direct DST shift. This demonstrates that `MIN(transform(charttime))` need not equal `transform(MIN(charttime))`.

## Full-data confirmation of aggregate DST non-commutation
- Affected: per-stay `MIN`/`MAX` endpoints over `Observation.effectiveDateTime` from chartevents.
- Verified: `icustay_times` attempt_0003 full-data comparison reproduced 73,173/73,181 rows identically; the remaining 8 conflicts were 7 `intime_hr` aggregate effects plus 1 direct `outtime_hr` shift. `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes each charttime before FHIR serialization, confirming that `MIN(transform(charttime))` can differ from `transform(MIN(charttime))` when genuine 03:00/03:02 rows coexist with spring-forward-gap 02:mm rows.
