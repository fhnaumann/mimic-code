## Chartevents Observation.issued is sourced from storetime but is not universally populated
- Affected: `Observation.issued` for resources generated from `mimiciv_icu.chartevents`
- Verified: `ventilator_setting` authoritative demo Delta probe with `forEach: code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')` found `issued` on 667,703/668,862 chartevents Observations overall and 14,831/14,831 target Observations; the DuckDB target had `chartevents.storetime` non-null on 14,831/14,831; ETL mapping is `mimic-fhir/sql/fhir_observation_chartevents.sql:10,68`.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: served `CodeSystem` resources and validation of chartevents item codes through a served CodeSystem
- Verified: `ventilator_setting` embedded Pathling 9.6.0 probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` raised `IllegalArgumentException: No data found for resource type: CodeSystem`; the exact chartevents system and all 15 target codes were instead observed on 14,831/14,831 target Observation codings.
