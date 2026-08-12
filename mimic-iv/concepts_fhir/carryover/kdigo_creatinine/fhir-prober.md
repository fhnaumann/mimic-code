# FHIR mapping: `kdigo_creatinine`

## Probe scope and authority

The source analysis in `carryover/kdigo_creatinine/source-analyst.md` was checked against the authoritative demo Delta warehouse `/Users/nau025/warehouses/mimic-iv-demo/delta` using embedded Pathling 9.6.0 on Spark 4.0.2. The local DuckDB oracle was `/Users/nau025/warehouses/mimic4-demo.db`. Raw `Mimic*.ndjson.gz` files were not used as the source of truth; the Delta resource tables are the served data.

The source tables map as follows:

| MIMIC-IV source table | FHIR resource | Role |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter` ICU stream | Driving relation; select only the Encounter with ICU identifier system |
| `mimiciv_hosp.labevents` | `Observation` labevents stream | Creatinine measurements, code `50912` |
| `mimiciv_hosp.labevents` grouped by `specimen_id` | `Specimen` lab stream | Optional provenance/grouping join; do not use it as the KDIGO measurement grain |

The canonical UUID/resource-key projections are `{path: "getResourceKey()", name: "encounter_id"}` for the ICU Encounter, `{path: "getResourceKey()", name: "observation_id"}` for the lab Observation, and `{path: "getResourceKey()", name: "specimen_id"}` for the lab Specimen. The canonical foreign-key projections are `{path: "subject.getReferenceKey(Patient)", name: "patient_id"}`, `{path: "partOf.getReferenceKey(Encounter)", name: "parent_encounter_id"}`, `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_id"}`, and `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_id"}` as applicable. These are UUID/string join columns, never numeric MIMIC identifiers; keep `_str` on identifier values until the final integer cast.

## Confirmed code discriminator

The only coded source filter is `mimiciv_hosp.labevents.itemid = 50912`. The served Delta carries it as:

- `system`: `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`
- `code`: `50912`
- `display`: `Creatinine`

The discriminator is **system plus exact code**, not `meta.profile`. The warehouse has no served `CodeSystem` resource (`src.read('CodeSystem')` raised `No data found for resource type: CodeSystem`), so the code was confirmed from the Observation coding itself. The item code is verbatim from the source ETL; there is no terminology translation.

Delta counts for the exact target:

| Probe | Count |
|---|---:|
| all labevents Observations | 107,727 |
| target `system + code` coding rows | 3,003 |
| distinct target Observation resources | 3,003 |
| target codings per resource | 1.0 (`3003 / 3003`) |
| target Quantity values | 3,003 |
| target Quantity comparators | 0 |
| target value strings | 0 |
| target effective dateTimes | 3,003 |
| target Observation specimen references | 3,003 |
| target Observation Encounter references | 2,366 (`637` absent) |

The coding `forEach` should therefore be constrained to `code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')`. Use `{path: "code", name: "code"}`, `{path: "system", name: "system"}`, and `{path: "display", name: "display"}` inside that group. A bare coding `forEach` happens to have ratio 1.0 here, but the constrained form protects against future coding fan-out.

## ICU Encounter mapping

The ICU stream is selected only by `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`. In the Delta there are 140 such Encounters, each with one ICU identifier, one patient reference, one parent Encounter reference, and populated `period.start`/`period.end`. The parent hospital Encounter is selected by `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`.

The source-to-FHIR paths are:

| Source column | Canonical FHIRPath alias | FHIR/materialized type | Population/probe |
|---|---|---|---|
| `icustays.stay_id` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | `string` / `VARCHAR`; cast to manifest `INTEGER` in final SQL | 140/140; 140/140 exact against DuckDB `stay_id` |
| `icustays.hadm_id` | ICU Encounter `{path: "partOf.getReferenceKey(Encounter)", name: "parent_encounter_key"}` joined to hospital Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | reference key `VARCHAR`; identifier value `VARCHAR`; cast `hadm_id_str` to manifest `INTEGER` | parent and hospital id present 140/140; 140/140 exact against DuckDB `hadm_id` |
| `icustays.subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | reference key `VARCHAR` UUID; join key only | populated 140/140 |
| `icustays.intime` | `{path: "period.start", name: "period_start"}` | FHIR `dateTime`, materialized `VARCHAR` with offset; cast directly to `TIMESTAMP_NTZ` | populated 140/140; 140/140 wall-clock exact against DuckDB |
| `icustays.outtime` | `{path: "period.end", name: "period_end"}` | FHIR `dateTime`, materialized `VARCHAR` with offset; cast directly to `TIMESTAMP_NTZ` | populated 140/140; 140/140 wall-clock exact against DuckDB |

`Encounter.class` must not be used to identify ICU stays. The ICU identifier system is the authoritative stream discriminator. `getResourceKey()` and `partOf.getReferenceKey(Encounter)` are UUID join keys, not output MIMIC ids.

## Labevents Observation mapping

The canonical Observation projection is a flat group plus the constrained coding group below. The paths are mapping entries, not an attempt ViewDefinition.

| Source column | Canonical FHIRPath alias | FHIR/materialized type | Population/probe |
|---|---|---|---|
| `labevents.labevent_id` (not used by source SQL, useful provenance) | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/observation-labevents').value", name: "labevent_id_str"}` | `Identifier.value` `string` / `VARCHAR`; cast only if used numerically | all 3,003 target identifiers joined to source; 3,003/3,003 exact id join |
| `labevents.subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `Reference` key `VARCHAR` UUID; join key only | populated for 3,003/3,003 target rows |
| `labevents.itemid` | coding group `{path: "code", name: "code"}` with `{path: "system", name: "system"}` and `{path: "display", name: "display"}` | all coding fields `string` / `VARCHAR` | code/system/display exact for 3,003/3,003 target rows |
| `labevents.valuenum` | `{path: "(value).ofType(Quantity).value", name: "value_qty"}` | FHIR `decimal`; materialized ViewDefinition alias is `string` / `VARCHAR`; cast to `DOUBLE` before `AVG`, `MIN`, or `<= 150` | Quantity present 3,003/3,003; numeric value exact 3,003/3,003 vs DuckDB |
| `labevents.valueuom` | `{path: "(value).ofType(Quantity).unit", name: "value_unit"}` | `string` / `VARCHAR` | `mg/dL` on 3,003/3,003; exact vs source `valueuom` |
| comparator diagnostic | `{path: "(value).ofType(Quantity).comparator", name: "value_comparator"}` | `string` / `VARCHAR` | 0/3,003; project while probing or guard against synthesized comparator Quantities |
| `labevents.charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | FHIR `dateTime`, materialized `string` / `VARCHAR` with offset; direct `TRY_CAST(... AS TIMESTAMP_NTZ)` | 3,003/3,003 populated; source wall-clock exact 3,002/3,003 |
| `labevents.specimen_id` | `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` then Specimen identifier below | Reference key `VARCHAR` UUID; join key only | 3,003/3,003 target references resolve |

Do not project only `effective.ofType(instant)` or coalesce a dateTime string with an instant alias. The target labevents stream is entirely `effectiveDateTime`: `effective.ofType(dateTime)` is populated 3,003/3,003, while `effective.ofType(Period).start` and `effective.ofType(instant)` are 0/3,003. The alias is string-like, so cast it directly to `TIMESTAMP_NTZ` before any `COALESCE`; do not first coalesce it with a native Spark timestamp and do not apply a final plain `TIMESTAMP` cast.

The one time conflict is the established upstream DST-gap transformation: source `2116-03-08 02:52:00` (labevent `418545`) is served as `2116-03-08T03:52:00-04:00`. This is not recoverable from the effective value alone; preserve the FHIR wall time with `TIMESTAMP_NTZ` and treat the one-hour source discrepancy as the existing FHIR ETL representation gap.

## Specimen mapping

The source SQL does not select `specimen_id`, and KDIGO must not group by specimen: its intended source grain is `(stay_id, charttime)` after averaging all qualifying item-50912 rows at that time. If specimen provenance is needed, use the following left-preserving join:

| Source column | Canonical FHIRPath alias | FHIR/materialized type | Population/probe |
|---|---|---|---|
| `labevents.specimen_id` | Observation `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` | Reference key `VARCHAR` UUID; join key only | target 3,003/3,003 |
| `labevents.specimen_id` | Specimen `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", name: "specimen_id_str"}` | `string` / `VARCHAR`; cast to `INTEGER` if emitted | target 3,003/3,003; exact identifier/source specimen id 3,003/3,003 |
| specimen collection time | `{path: "(collection.collected).ofType(dateTime)", name: "collected_datetime"}` | FHIR `dateTime`, materialized `VARCHAR` with offset; direct `TIMESTAMP_NTZ` | target 3,003/3,003; exact to source `MAX(charttime)` for 3,002/3,003, with the same DST-gap row |
| `d_labitems.fluid` (not referenced by KDIGO SQL) | Specimen type coding group `{path: "code", name: "type_code"}`, `{path: "system", name: "type_system"}`, `{path: "display", name: "type_display"}` under `forEach: "type.coding"` | strings / `VARCHAR` | target type system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-lab-fluid`, code `Blood`; display is null |

There are 12,458 served Specimen resources, but only the target lab specimens need to be joined. Use a left join if specimen fields are projected; never let an absent specimen turn a source measurement into a missing row.

## Joins, filters, and cardinality required for source semantics

1. Drive from the ICU `Encounter` stream filtered by the ICU identifier system, preserving the source `icustays LEFT JOIN labevents`.
2. Join Observation to ICU Encounter by the shared patient reference key and apply the source window in the join predicate: `effective_time >= period.start - 7 days` and `effective_time <= period.end`, both inclusive. Do **not** require `Observation.encounter`; only 2,366/3,003 target observations have one.
3. Filter the Observation coding by the exact labevents system and code `50912`, require the Quantity value to be non-null and `<= 150`, and do not use `valueString` as a numeric fallback. The target probe had no comparator or string-valued exceptions.
4. Preserve the source grouping grain `(ICU stay, charttime)`, not `(Observation id)` and not `(specimen id)`. The source joins by subject and can assign one lab event to multiple ICU stays when the subject/time window permits it; the demo oracle had 1,274 qualifying stay-event join rows from 1,208 distinct labevents, 1,272 distinct `(stay_id, charttime)` groups, and the FHIR patient/time join reproduced the same 1,274 rows and pairs exactly.
5. Average all qualifying numeric values at `(stay_id, charttime)`. Keep both baseline enrichment joins left-preserving: prior values are strictly before the current charttime and include the lower window endpoints (48 hours and 7 days). A null prior minimum must not remove the current row.
6. If `hadm_id` is emitted, obtain it through the ICU Encounter's `partOf.getReferenceKey(Encounter)` to the hospital Encounter's `encounter-hosp` identifier and cast the identifier string to `INTEGER`. Do not use the incomplete Observation Encounter reference for this join.

## Gaps and representability

| Source value/requirement | Classification | Consequence |
|---|---|---|
| Exact source `charttime` at the DST spring-forward gap | not representable from `Observation.effectiveDateTime` alone | One demo target row is irreversibly +1 hour in FHIR (`3002/3003` exact); direct `TIMESTAMP_NTZ` is the faithful FHIR-side mapping. |
| `Observation.encounter` as a source admission/stay join | absent but derivable only heuristically | It is populated for 2,366/3,003 target rows. Patient + effective time + ICU period reproduces the source demo join exactly, but this is a temporal association, not a required reference join. |
| `labevents.hadm_id` | not needed by the source SQL; if independently required, absent from 637/3,003 target Observation encounter references and not exactly recoverable from FHIR alone | The KDIGO source's `hadm_id` comes from `icustays`, so use the ICU parent hospital Encounter identifier. Do not manufacture `hadm_id` from an Observation encounter reference. |
| `labevents.labevent_id` | present and exactly recoverable via the Observation labevents identifier, but not an output column in the source SQL | Optional provenance path; it must not replace the `(stay_id, charttime)` aggregation grain. |

## Read/probe provenance

Read the full `MIMIC_NOTES.md`, the source analysis, the canonical observation ViewDefinition, and these provisional fragments: `chemistry.md`, `complete_blood_count.md`, `coagulation.md`, `height.md`, `icp.md`, `gcs.md`, and `crrt.md` (also the fragment README). The shared notes changed the mapping decisions as follows: Delta-over-ndjson authority selected the warehouse; identifier values versus UUID resource/reference keys determined the ICU and hospital id paths and casts; the ICU identifier system displaced Encounter class; itemid verbatim coding required the exact labevents system/code filter; incomplete lab Observation Encounter references required the patient/time left-preserving join; Quantity aliases required numeric casting; and the datetime/DST entries required direct `TIMESTAMP_NTZ` handling. The chemistry/coagulation datetime and Quantity leads were confirmed for this target. The CBC comparator lead was consistent with the target's 0/3,003 comparators. The height, ICP, GCS, and CRRT chartevents-specific leads were read but are not applicable to this labevents concept and were not used as evidence for this mapping.

No new dataset-wide mapping quirk beyond the established notes was found in the target. The verified absence of served CodeSystem resources was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/kdigo_creatinine.md`; it is a warehouse-level operational fact, not a concept-specific gap.
