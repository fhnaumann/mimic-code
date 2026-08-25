## Chartevents Observation.issued is sourced from storetime but is not universally populated
- Affected: `Observation.issued` for resources generated from `mimiciv_icu.chartevents`
- Verified: `ventilator_setting` authoritative demo Delta probe with `forEach: code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')` found `issued` on 667,703/668,862 chartevents Observations overall and 14,831/14,831 target Observations; the DuckDB target had `chartevents.storetime` non-null on 14,831/14,831; ETL mapping is `mimic-fhir/sql/fhir_observation_chartevents.sql:10,68`.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: served `CodeSystem` resources and validation of chartevents item codes through a served CodeSystem
- Verified: `ventilator_setting` embedded Pathling 9.6.0 probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` raised `IllegalArgumentException: No data found for resource type: CodeSystem`; the exact chartevents system and all 15 target codes were instead observed on 14,831/14,831 target Observation codings.

## Rebuilt numeric chartevents carry distinct ventilator text in component.valueString
- Affected: `Observation.component.valueString` and its `component.code.coding` for chartevents itemids `223848`, `223849`, and `229314`
- Verified: `ventilator_setting` attempt_0002 authoritative embedded Pathling probe with `forEachOrNull: "component"` found component text on 906/1,292, 1,011/1,048, and 402/402 target resources respectively (2,319/2,742 total text-item resources); every component coding matched the parent item code and `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, and the source/FHIR text pivots agreed 2,742/2,742 exactly. This confirms the `e7c326b` branch in the rebuilt Delta for ventilator settings.
