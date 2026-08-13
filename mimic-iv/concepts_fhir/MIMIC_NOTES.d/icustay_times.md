## Chartevents MIN/MAX can expose DST normalization after aggregation
- Affected: aggregates over `Observation.effectiveDateTime` from chartevents, including per-stay `MIN`/`MAX` endpoints
- Verified: `icustay_times` attempt_0002 full-data comparison found 7 residual `intime_hr` conflicts where a source spring-forward-gap `02:mm` minimum was normalized to `03:mm` and a genuine unchanged `03:00`/`03:02` row became the candidate minimum; one additional `outtime_hr` conflict was a direct DST shift. This demonstrates that `MIN(transform(charttime))` need not equal `transform(MIN(charttime))`.
