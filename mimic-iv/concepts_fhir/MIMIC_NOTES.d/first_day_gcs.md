## Served chartevents Observations use `effectiveDateTime` only
- Affected: `Observation.effective[x]` for the ICU chartevents stream
- Verified: `first_day_gcs` attempt_0001 embedded Pathling 9.6.0/Spark 4.0.2 probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` projected all `mimic-chartevents-d-items` codings: 668,862/668,862 had `effective.ofType(dateTime)`, while `Period.start`, `Period.end`, and `instant` were each 0/668,862; the GCS subset was 9,791/9,791 dateTime-only.

## Chartevents ETL globally omits NULL-value rows and one hard-coded tuple
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including the GCS itemids
- Verified: `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` applies `value IS NOT NULL` and excludes `(stay_id=34934165, charttime='2151-10-03 05:14:00.000')`; the attempt_0001 source/Delta probe found 9,791/9,791 GCS source rows with non-NULL `value` and no row at that excluded tuple, so the demo bound is 0 affected GCS rows.

## Rebuilt numeric chartevents preserve GCS verbal text in `component.valueString`
- Affected: `Observation.component[].valueString` and its `component.code.coding` for chartevents item `223900`
- Verified: `first_day_gcs` attempt_0003 embedded Pathling 9.6.0/Spark 4.0.2 probe over the authoritative demo Delta found the component on 3,266/3,266 item-223900 resources (and 0/6,525 other GCS resources); component code/system/display matched the parent coding on 3,266/3,266. DuckDB/FHIR source agreement was 9,791/9,791 for the GCS key/value rows and 3,266/3,266 for component text, including 1,348 `No Response-ETT` and 78 `No Response` values.
