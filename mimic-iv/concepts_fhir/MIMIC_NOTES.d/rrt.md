## Chartevents ETL irreversibly normalizes spring-forward-gap chart times
- Affected: `Observation.effectiveDateTime` for resources generated from `mimiciv_icu.chartevents`, especially unkeyed/multiset concepts where repeated output tuples amplify one transformed source row
- Verified: `rrt` attempt 0001 full comparison reported 821 oracle-only and 241 candidate-only tuples (580 fewer candidate rows); all sampled candidate-only times are March 03:xx and sampled corresponding oracle times include March 02:xx. Full-oracle replay found 608 selected chartevents source rows changed by `CAST(charttime AS TIMESTAMPTZ)`, while `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` writes only the normalized value. The original wall time is not present in any FHIR element; resource identity is opaque and cannot be used as a semantic side channel.

## Chartevents resources preserve repeated same-item observations at one stay/time
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, and any RRT pivot or multiset keyed by `(stay_id, charttime, itemid)`.
- Verified: `rrt` attempt 0001 authoritative Delta probe found item `224146` retained 532 source/FHIR rows; 338 `(stay_id, charttime)` groups had one row, 94 had two, and 2 had three. This confirms repeated source rows must not be pre-deduplicated.

## ICU input-event MedicationAdministration endpoints also receive DST normalization
- Affected: `MedicationAdministration.effectivePeriod.start` and `.end` from `mimiciv_icu.inputevents`, and interval overlays consuming those endpoints.
- Verified: `rrt` attempt 0002 full-oracle replay found 27 selected inputevents intervals changed by the upstream `TIMESTAMPTZ` cast at `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-67`; together with 608 shifted chartevents rows, the replay accounted for 449 `only_oracle` and all 241 `only_candidate` RRT divergence rows through `UNION DISTINCT` and the inclusive range overlay.
