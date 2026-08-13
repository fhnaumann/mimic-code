## Chartevents Observation ETL preserves repeated same-item observations at one stay/time
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, especially `code=224146` and any pivot keyed by `(stay_id, charttime, itemid)`
- Verified: crrt authoritative demo Delta/DuckDB probe found 532 source/FHIR rows for item `224146`; 338 `(stay_id,charttime)` groups had one row, 94 had two, and 2 had three, with all 532 FHIR resources retained. This is a dataset-wide chartevents cardinality finding; it supersedes any one-row-per-stay/time/item assumption.

## Chartevents DST normalization can collapse distinct source times before a FHIR-side pivot
- Affected: `Observation.effectiveDateTime` and `Observation.id` on resources generated from `mimiciv_icu.chartevents`
- Verified: `crrt` attempt 0001 reported 85 `only_oracle`, 22 `only_candidate`, and 53 `differing_conflict` keys; the sampled missing keys are source 02:xx times, while candidate-only and conflicting keys are normalized 03:xx times. `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` rewrites those times, causing shifted 02:xx observations to merge with genuine 03:xx observations before the CRRT `MAX` pivot. Lines 21, 41, and 45 retain the pre-normalization charttime in the UUIDv5 resource id, so correction must distinguish observations by `Observation.id`, not blanket-shift all 03:xx rows.

## Spark `DATE_FORMAT` can re-normalize a `TIMESTAMP_NTZ` wall time inside the session-zone DST gap
- Affected: `Observation.id` / `Observation.effectiveDateTime` recovery and any Spark SQL formatting of corrected FHIR wall times
- Verified: `crrt` attempt 0002 retained 37 `only_oracle`, 6 `only_candidate`, and 27 `differing_conflict` rows after its UUID recovery used `DATE_FORMAT` on a one-hour-subtracted `TIMESTAMP_NTZ`. All 37 missing keys were October 02:xx and paired to candidate rows at +1 hour; all 27 conflicts were October 03:xx collision pivots. In Spark 4.0.2 with session zone `Australia/Sydney`, subtracting one hour from `2140-10-02 03:00:00` produced NTZ `02:00:00`, but `DATE_FORMAT(..., 'yyyy-MM-dd HH:mm:ss')` emitted `03:00:00`; `CAST(... AS STRING)` preserved `02:00:00`. UUID names must use the string cast, not `DATE_FORMAT`, to avoid reapplying DST normalization.

## Superseded: remove UUID recovery rather than changing its formatting
- Affected: `Observation.id` / `getResourceKey()` and `Observation.effectiveDateTime`.
- Verified: policy review on 2026-08-13 preserved the Spark session-zone finding but rejected UUID recovery itself. UTC-pinned reads prevent the false Sydney/October effect; resource ids remain opaque and cannot recover New York-normalized source times. Reopened CRRT must use served FHIR values and let the comparator/judge classify the residual.
