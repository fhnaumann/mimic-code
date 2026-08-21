## Served chartevents Observations use the dateTime effective variant only
- Affected: `Observation.effective[x]` for the chartevents stream
- Verified: fresh embedded Pathling 9.6.0/Spark 4.0.2 probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` projected all chartevents-system codings with `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"`: 668,862/668,862 resources had `effective.ofType(dateTime)`, while `Period.start`, `Period.end`, and `instant` were each 0/668,862; the first-day target subset was 96,145/96,145 dateTime-only.

## Chartevents ETL applies global value and hard-coded stay/time exclusions
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including downstream `vitalsign` groupings
- Verified: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:34-37` applies `value IS NOT NULL` and excludes the fixed `(stay_id=34934165, charttime='2151-10-03 05:14:00.000')` group; the read-only DuckDB probe found 96,145/96,145 first-day target source rows with non-NULL `value`, 0 rows at that tuple, and the constrained Delta projection found 96,145/96,145 FHIR resources.

## ICU Encounter intime is DST-normalized before downstream windows
- Affected: ICU `Encounter.period.start` and any downstream candidate window or aggregate anchored on `icustays.intime`
- Verified: `mimic-fhir/sql/fhir_encounter_icu.sql:31,98` casts ICU `intime` through `TIMESTAMPTZ` before writing `Encounter.period.start`; the full-data `first_day_vitalsign` attempt_0001 decomposition attributed 7 non-overlapping aggregate conflicts to this anchor shift, with the original spring-forward-gap wall time absent from FHIR.
