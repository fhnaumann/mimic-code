## Chartevents Observation.issued preserves source storetime
- Affected: `Observation.issued` for resources generated from `mimiciv_icu.chartevents`
- Verified: `oxygen_delivery` fhir-prober attempt 0001 embedded Delta probe over all four target itemids found `issued` populated on 4,393/4,393 rows; read-only DuckDB comparison of `(subject_id, stay_id, charttime, itemid, storetime)` agreed exactly 4,393/4,393. The upstream mapping is `mimic-fhir/sql/fhir_observation_chartevents.sql:10,68`.

## Chartevents Observation resources retain repeated same-item rows at one patient/time
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, and any pivot keyed by patient plus effective time
- Verified: `oxygen_delivery` fhir-prober attempt 0001 authoritative demo probe found item `226732` had 3,145 source/FHIR rows in 3,014 `(subject_id, charttime)` groups; 106 groups had multiple rows and the maximum group size was 3. All 3,145 source/FHIR tuples agreed exactly. Do not pre-deduplicate resources before applying source ranking.
