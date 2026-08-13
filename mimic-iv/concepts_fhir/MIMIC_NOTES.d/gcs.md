## Chartevents FHIR ETL omits selected rows whose source `value` is NULL
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including GCS itemids `223900`, `223901`, and `220739`; the canonical GCS source query retains selected rows without a `value IS NOT NULL` predicate.
- Verified: `gcs` attempt_0001 source analysis checked `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` (`value IS NOT NULL`) against `mimic-iv/concepts/measurement/gcs.sql:50-57` (itemid-only WHERE); GCS-specific row magnitude was not probed at this stage.

## Numeric chartevents discard source text even when `value` is non-NULL
- Affected: `Observation.value[x]` for chartevents rows with non-NULL `valuenum`, including any source text sentinel carried alongside that numeric value
- Verified: `mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` writes `valueQuantity` when `valuenum IS NOT NULL` and writes `valueString` only otherwise; the authoritative GCS Delta probe found 9,791/9,791 target rows as Quantity and 0/9,791 as string, while DuckDB found the exact `No Response-ETT` text on 1,348 rows with `valuenum=1` (the 78 non-sentinel `No Response` rows also had `valuenum=1`), so the source text is not a FHIR value path.

## Chartevents Observation UUID retains the source value as an exact witness
- Affected: `Observation.getResourceKey()` for chartevents rows, including recovery of the `No Response-ETT` source sentinel when `valueQuantity` conflates it with `No Response`
- Verified: `mimic-fhir/sql/fhir_observation_chartevents.sql:20-23` and `mimic-fhir/sql/fhir_etl/uuid_namespace.sql:27` were recreated in the GCS attempt; UUIDv5 matching (including the one-hour DST-gap candidate) produced the same 3,279 demo `(stay_id, charttime)` rows and all eight output values as `mimiciv_derived.gcs`, without using Quantity 1 as a discriminator.

## Chartevents Observation UUID makes DST-gap charttime recoverable before a FHIR-side pivot
- Affected: `Observation.effectiveDateTime` and `Observation.id` for chartevents-derived Observations
- Verified: `gcs` attempt 0002 full-data comparison had 98 `only_oracle` keys at source 02:xx and 74 `only_candidate` keys at FHIR 03:xx, with no value conflicts. A read-only full-data join paired all 98 missing keys to a candidate key exactly one hour later with every non-key output equal; 24 of those shifted keys collided with a genuine source 03:xx key, explaining the 98-versus-74 counts. `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes the effective time, while lines 21, 41, and 45 write an Observation UUID generated from the original pre-normalization charttime and source value, so UUID candidate matching can restore the original time before grouping.

## Superseded: Observation.id cannot recover the discarded GCS label or time
- Affected: `Observation.id`, `Observation.effectiveDateTime`, and `Observation.value[x]` for GCS chartevents.
- Verified: policy review on 2026-08-13 preserved the earlier measurements but rejected their use as a mapping. Resource ids are opaque identity and cannot be regenerated or brute-forced. Because the ETL drops the `No Response-ETT` discriminator and that loss changes `gcs_unable`, `gcs_verbal`, total `gcs`, and six-hour carry-forward, the reopened concept must go to the equivalence judge for whole-concept `BLOCKED_REPRESENTATION`.
