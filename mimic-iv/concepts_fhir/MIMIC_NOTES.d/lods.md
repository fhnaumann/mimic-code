## Rebuilt numeric chartevents preserve meaningful source text in `component.valueString`
- Affected: `Observation.component` for numeric ICU chartevents, including itemids `223900`, `223901`, and `220739`; the component uses the same `mimic-chartevents-d-items` coding as `Observation.code`.
- Verified: `lods` fhir-prober UTC probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` found 9,791/9,791 selected GCS resources with matching component code/text; item `223900` had 1,348 `No Response-ETT` and 78 `No Response` component values, distinguishing labels that both have Quantity 1. This confirms the rebuilt `e7c326b` ETL branch.

## Served ICU chartevents effective timing is dateTime-only in the rebuilt Delta
- Affected: `Observation.effective[x]` for ICU chartevents used by temporal concepts.
- Verified: `lods` fhir-prober projections found `effective.ofType(dateTime)` populated 3,145/3,145 for item `226732` and 9,791/9,791 for the GCS probe, while Period and instant variants were 0/3,145 and 0/9,791 respectively; parse the served string as `TIMESTAMP_NTZ`.
