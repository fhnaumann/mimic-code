## Chartevents FHIR ETL drops one hard-coded duplicate row
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including any item-specific chart stream
- Verified: `mimic-fhir/sql/fhir_observation_chartevents.sql:34-37` excludes `(stay_id=34934165, charttime='2151-10-03 05:14:00.000')` before writing FHIR; the exact DuckDB check `SELECT count(*), count(*) FILTER (WHERE itemid=223758) FROM mimiciv_icu.chartevents WHERE stay_id=34934165 AND charttime=TIMESTAMP '2151-10-03 05:14:00'` returned `(0, 0)` in the demo, so this omission was not exercised by `code_status`'s 147 target rows.

## Chartevents FHIR ETL omits rows whose source value is NULL
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including `Observation.value[x]` and any item stream whose source SQL retains NULL-valued rows
- Verified: `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` applies `value IS NOT NULL`; the exact DuckDB target query for `itemid=223758` returned 147 total and 0 NULL `value`, while the served target ViewDefinition returned 147/147 `value.ofType(string)`, so no code-status demo row was lost.

## Chartevents effectiveDateTime irreversibly normalizes DST-gap charttime
- Affected: `Observation.effectiveDateTime` on resources generated from `mimiciv_icu.chartevents`
- Verified: `code_status` attempt 0001 reported 197,940 `only_oracle` and 9 `only_candidate` tuples. A read-only full-data join paired all 9 candidate-only tuples one-for-one to oracle tuples with identical subject, admission, stay, and status flags but source `charttime` exactly one hour earlier (02:xx source versus 03:xx FHIR). `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` casts the naive source time through `TIMESTAMPTZ` and writes only that normalized value to `Observation.effectiveDateTime`.

## Chartevents Observation.id preserves the pre-normalization charttime input
- Affected: `Observation.id` / `getResourceKey()` and `Observation.effectiveDateTime` for chartevents-derived Observations
- Verified: equivalence-judge review of `code_status` attempt 0001 traced `mimic-fhir/sql/fhir_observation_chartevents.sql:9,21,41,45,67` and `mimic-fhir/sql/fhir_etl/uuid_namespace.sql:27`; the UUIDv5 input retains the original `stay_id-charttime-itemid-value` before TIMESTAMPTZ normalization, providing an equality witness for an exact DST-gap recovery query.

## Hospital General Care code-status POE events are absent from served FHIR
- Affected: `mimiciv_hosp.poe` / `poe_detail`, especially `poe.ordertime` and `poe_detail.field_value` for `order_type='General Care'` and `order_subtype='Code status'`
- Verified: `code_status` attempt 0002 judge review found 197,931 independently counted source POE/detail rows absent from the served FHIR representation; the nearest `MedicationRequest.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-poe')` stream had zero intersection with the selected code-status POE IDs and represents medication/IV/TPN orders instead.

## Superseded: hardcoded or reconstructed Observation ids are not recovery paths
- Affected: `Observation.id` / `getResourceKey()` and the missing `poe` / `poe_detail` branch.
- Verified: policy review on 2026-08-13 preserved the historical ETL findings but rejected id-based correction. Resource ids are opaque identity. The absent POE branch changes row inclusion, so the reopened concept must present that essential loss to the equivalence judge for `BLOCKED_REPRESENTATION` unless an exact FHIR representation is found; it is not an ancillary gap eligible for automatic re-acceptance.

## Hospital General Care code-status POE omission confirmed on the fourth full run
- Affected: hospital `poe` / `poe_detail`, including `poe.ordertime` and `poe_detail.field_value` for `order_type='General Care'` and `order_subtype='Code status'`.
- Verified: `code_status` attempt 0004 reported 197,935 `only_oracle` and 4 `only_candidate` residual tuples; the four candidate tuples are the DST-normalized charttime cases, leaving the independently counted 197,931-row POE/detail branch absent. `mimic-fhir/sql/fhir_medication_request.sql:188-205,250-252` limits POE-derived MedicationRequests to EMAR medication rows or `IV therapy`/`TPN`, and `:254-288` emits no `poe_detail.field_value`; the ETL has no General Care/Code-status resource branch.
