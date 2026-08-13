## Chartevents FHIR ETL applies global row omissions before Observation creation
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including the ICP item streams; source rows with NULL `value` are excluded and one hard-coded `(stay_id, charttime)` duplicate is excluded before FHIR creation.
- Verified: `icp` attempt_0001 source analysis read `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` and observed the executable `value IS NOT NULL` predicate plus the hard-coded duplicate predicate at lines 35-37; no ICP-specific row-count probe was run.

## Chartevents ETL omission predicates are active but unexercised for the ICP demo target
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including codes `220765` and `227989`.
- Verified: `icp` FHIR-prober embedded Pathling probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` found 313/313 target resources against 313 DuckDB oracle rows; source `value IS NULL` was 0/313 and the hard-coded tuple `(34934165, 2151-10-03 05:14:00)` was 0 rows. The ETL predicates remain the established coverage rule, but caused no ICP demo loss.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: served `CodeSystem` resources and any attempt to validate the ICP itemids by reading a CodeSystem.
- Verified: `icp` FHIR-prober embedded Pathling probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` ran `src.read('CodeSystem')`, which raised `IllegalArgumentException: No data found for resource type: CodeSystem`; the exact ICP system and codes were instead observed on 313/313 target Observation codings.

## Chartevents Observation.id preserves a recoverable witness for DST-normalized charttime
- Affected: `Observation.id` and `Observation.effectiveDateTime` on resources generated from `mimiciv_icu.chartevents`.
- Verified: `icp` attempt `0001` reported 38 `only_oracle`, 4 `only_candidate`, and 12 `differing_conflict` rows; all 20 sampled missing keys were source 02:xx, all 4 candidate-only keys were served 03:xx (each paired at +1 hour to a sampled missing key), and all 12 conflicts were 03:xx collision groups. `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes the source time before writing `effectiveDateTime`, but lines 21, 41, and 45 write an Observation UUIDv5 generated from the original `stay_id-charttime-itemid-value`; an ICP-specific embedded probe regenerated 313/313 served demo IDs from the projected stay identifier, item code, effective wall time, and normalized Quantity string. Test the served time and one hour earlier against the resource ID before grouping rather than blanket-shifting 03:xx rows.

## Superseded: Observation.id is opaque identity, not a charttime recovery path
- Affected: `Observation.id` / `getResourceKey()` on chartevents-derived resources.
- Verified: policy review on 2026-08-13 retained the historical measurement above but rejected its recommendation. Reconstructing UUIDv5 from candidate source values uses ETL row identity as a semantic side channel and is forbidden even when exact. Reopened ICP must use served `effectiveDateTime`; the comparator and judge handle proven New York DST normalization.
