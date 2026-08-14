# FHIR prober mapping — `weight_durations`

## Probe scope and sources

- Canonical source SQL: `mimic-iv/concepts/demographics/weight_durations.sql`.
- Source analysis: `mimic-iv/concepts_fhir/carryover/weight_durations/source-analyst.md`.
- Authoritative FHIR warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`.
- Source oracle: `/Users/nau025/warehouses/mimic4-demo.db`, opened read-only.
- Engine: embedded Pathling 9.6.0 on Spark 4.0.2, with the executor session
  timezone pinned to UTC. No HTTP Pathling server was used.
- The canonical ViewDefinition shape was checked against
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- This file is a mapping artifact only. No attempt ViewDefinition or concept
  SQL was authored.

## Source table to FHIR resource mapping

| MIMIC-IV source table | FHIR resource/stream | Selection and role |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation`, ICU chartevents stream | Select the exact chartevents coding system and codes `226512` and `224639`. The Observation carries the patient and ICU-Encounter references, effective dateTime, and numeric Quantity. |
| `mimiciv_icu.icustays` | `Encounter`, ICU stream | Select `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`. The identifier value carries `stay_id`; `period.start` and `period.end` carry `intime` and `outtime`. |

The Observation's `encounter.getReferenceKey(Encounter)` joins to the ICU
Encounter `getResourceKey()`. The numeric `stay_id` is then obtained from the
ICU Encounter's `identifier.value`, not from either resource/reference UUID.
The demo had 140 ICU Encounters and all 570 target Observations resolved to an
ICU Encounter; the target covered 137 distinct stays.

## Confirmed coded discriminator

The source SQL names exactly two itemids. The authoritative Delta carries both
as decimal strings in this coding system and no alternate system was observed
for either exact code:

`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`

| Source itemid | FHIR code | FHIR display | Source rows | FHIR coding rows | Distinct FHIR resources |
|---:|---:|---|---:|---:|---:|
| 226512 | `226512` | `Admission Weight (Kg)` | 129 | 129 | 129 |
| 224639 | `224639` | `Daily Weight` | 441 | 441 | 441 |
| **total** |  |  | **570** | **570** | **570** |

The exact discriminator is `code.coding.system` plus the exact string code.
`d_items.itemid` is a global primary key with one `linksto` value, so the exact
code separates this chartevents stream; `meta.profile` is not a discriminator.
The unfiltered chartevents coding projection was 668,862 coding rows over
668,862 distinct Observation resources, a codings-per-resource ratio of
**1.000**. The target ratio was also **570/570 = 1.000**. Keep the coding
constraint inside the repeating group nevertheless.

Canonical coding group:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='226512' or code='224639'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

## Canonical ViewDefinition projections

These are mapping projections, not implementation artifacts. FHIR identifier
values and resource/reference keys remain strings until the final SQL casts the
MIMIC identifiers to the manifest's integer type.

### Observation (`chartevents`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" },
    { "path": "(value).ofType(string)", "name": "string_value" }
  ]
}
```

The target counts were 570/570 for `observation_key`, `patient_key`,
`encounter_key`, `effective_datetime`, `quantity_value`, and `quantity_unit`.
`effective_period_start`, `effective_instant`, `quantity_comparator`, and
`string_value` were 0/570. The two unused effective variants must not be
coalesced with the dateTime string: the dateTime alias is `STRING`, while the
instant alias is native Spark `TIMESTAMP`.

### ICU Encounter (`icustays`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "intime_datetime" },
    { "path": "period.end", "name": "outtime_datetime" }
  ]
}
```

The ICU view selected 140/140 resources with non-null `encounter_key`,
`patient_key`, `parent_encounter_key`, `stay_id_str`, `intime_datetime`, and
`outtime_datetime`; all 140 `stay_id_str` values were distinct. The two period
aliases are FHIR dateTime strings (materialized `STRING`) with offset-bearing
ISO-8601 values. Direct wall-clock comparison to DuckDB `icustays.intime` and
`outtime` agreed 140/140 in the demo.

## Source column to FHIRPath mapping and types

| Source column / derived output | Canonical mapping `{path, name}` | FHIR type and materialized type | Evidence and final-SQL requirement |
|---|---|---|---|
| `chartevents.itemid` | `{ "path": "code", "name": "item_code" }` inside the constrained `code.coding` group; system is `{ "path": "system", "name": "item_system" }`; label is `{ "path": "display", "name": "item_display" }` | `Coding.code` / `uri` / `string`; all materialize as `STRING` | `CAST(item_code AS INTEGER)` recovers the itemid exactly for all 570 target rows. Filter system and exact string code before any cast. |
| `chartevents.stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`, joined by equality to ICU Encounter `{ "path": "getResourceKey()", "name": "encounter_key" }`; then `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)`/resource key is opaque `STRING`; `Identifier.value` is FHIR `string`, materialized `STRING` | All 570/570 target rows joined. Final output requires `CAST(stay_id_str AS INTEGER)`. Never use the UUID key as `stay_id`. |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | FHIR `Identifier.value` `string`, materialized `STRING` | 140/140 exact identifier values; final output cast is required. |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`, materialized offset-bearing `STRING` | `CAST(effective_datetime AS TIMESTAMP_NTZ)` preserved the source wall-clock charttime for 570/570 target event keys. Keep the outermost result `TIMESTAMP_NTZ`, not plain `TIMESTAMP`. |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`, materialized offset-bearing `STRING` | 140/140 direct wall-clock matches in the demo. Cast to `TIMESTAMP_NTZ` before subtracting two hours or comparing to a mapped start. |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime_datetime" }` | FHIR `dateTime`, materialized offset-bearing `STRING` | 140/140 direct wall-clock matches in the demo. Cast to `TIMESTAMP_NTZ` before adding the two-hour terminal extension. |
| `chartevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR `Quantity.value` decimal; raw Delta field `decimal(32,6)`, ViewDefinition alias `STRING` | 570/570 populated. Cast the alias to a numeric/decimal type before the canonical three-place `ROUND`; do not treat `VARCHAR` as a finished numeric output. |
| `chartevents.valueuom` (supporting) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | FHIR `Quantity.unit` string, materialized `STRING` | `kg` on 570/570 rows. The canonical output does not retain the unit, but this confirms the Quantity branch. |
| `chartevents.value` (unused source field) | `{ "path": "(value).ofType(string)", "name": "string_value" }` | FHIR `string`, materialized `STRING` | 0/570 for this numeric target because the ETL chooses Quantity whenever `valuenum` is non-null. The source SQL does not use `value`. |
| `weight_type` | Derived from `{ "path": "code", "name": "item_code" }` | SQL `VARCHAR` derived from exact item code | `226512 -> 'admit'`; `224639 -> 'daily'`. This is absent as a FHIR field but exactly derivable from the surviving code; it is not a representation gap. |
| `weight` | Derived from `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | Source output is numeric/decimal; FHIR input alias is `STRING` | `CAST(quantity_value AS DECIMAL)` then `ROUND(..., 3)` reproduces the source's canonical weight to 3 decimal places for 570/570 rows. |
| `starttime` | Ordinary measurement: `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }`; first admission/backfill: derived from `{ "path": "period.start", "name": "intime_datetime" }` minus two hours | Output timestamp; mapped inputs are `STRING` aliases cast to `TIMESTAMP_NTZ` | The source has no single FHIR `starttime` element. It is exactly derivable by replaying the canonical CASE over effective time, item-derived type/rank, and ICU period start. |
| `endtime` | Next mapped `starttime` within stay, otherwise `{ "path": "period.end", "name": "outtime_datetime" }` plus two hours | Output timestamp; mapped inputs cast to `TIMESTAMP_NTZ` | No single FHIR end element exists. It is derivable by replaying the canonical `LEAD`/fallback over mapped times while preserving row multiplicity. |

`getResourceKey()` and `getReferenceKey(...)` are opaque identity columns for
joins only. They are not source identifiers and must not be parsed, regenerated,
or used to infer a discarded charttime or numeric value.

## Counts, precision, multiplicity, and oracle checks

The read-only DuckDB checks on the raw item set (`itemid IN (226512, 224639)`)
returned 570 total rows, with `stay_id`, `itemid`, `charttime`, `valuenum`, and
source `value` non-null on 570/570. All 570 passed the canonical positive and
`<1500` filters; no row was removed by those filters. Units were `kg` on
441/441 daily and 129/129 admission rows.

The source had 570 distinct `(stay_id, charttime, itemid)` event keys, zero
duplicate groups, and maximum multiplicity one. The FHIR target had 570
distinct joined `(stay_id, itemid, effective wall time)` keys and zero duplicate
groups. Thus this target has no demo multiplicity loss or fan-out, although the
chartevents ETL and the canonical `UNION ALL` must not be assumed to deduplicate
other streams or future rows.

The raw source column is DuckDB `FLOAT`; the raw FHIR Quantity value is
`decimal(32,6)`, while the materialized ViewDefinition alias is `STRING`.
Target values have at most one displayed decimal place. On the 570 unique
`(stay_id, itemid, wall time)` joins, the six-place decimal values were
numerically identical for 564/570; six rows differed only by the source FLOAT
round-trip (`65.800004` vs FHIR `65.8`, or `65.699996` vs `65.7`), with maximum
absolute difference `0.000004`. The canonical three-decimal `weight` was exact
for 570/570 rows. Therefore raw `valuenum` is not bit/float-exact on six rows,
but the value used by this concept is exact after its specified three-place
rounding and the difference is not essential to this concept.

The FHIR effective wall time, item code, and stay identifier agreed with the
source on 570/570 target event keys. No target-specific DST shift was observed
in the demo. The output datetime must nevertheless be parsed with
`CAST(... AS TIMESTAMP_NTZ)`: FHIR lexical values carry an offset, and an
offset-aware `to_timestamp` or late plain `TIMESTAMP` cast converts the
de-identified wall time.

## Gaps and bounded essentiality

1. **Raw FLOAT representation of `valuenum`: absent but approximable, not
   essential here.** Six of 570 raw six-place comparisons differed by at most
   `4e-6`; the measured approximation is 564/570 exact at six places and
   570/570 exact after the canonical three-place round. The source output does
   not expose unrounded `valuenum`, so this does not change inclusion, ranking,
   grouping, or any final `weight` in this concept.

2. **Original source charttime at a DST spring-forward gap: not representable
   on affected rows.** The local ETL casts `chartevents.charttime` through
   `TIMESTAMPTZ` at `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` before
   writing `Observation.effectiveDateTime`. The original wall time is not in a
   FHIR element, and resource identity is opaque; UUID reconstruction is a
   forbidden side channel. The target-specific demo bound is 0/570 affected
   rows, with 570/570 wall-clock agreement. On full data, this loss can be
   essential for an affected row because `weight_durations` uses charttime for
   the per-stay/type `ROW_NUMBER`, stay-wide `LEAD`, strict backfill inclusion,
   interval starts, and interval ends. The shared dataset policy treats this
   known upstream ETL normalization as a comparator/judge issue rather than an
   automatic prober-stage block; the full run must measure its propagation.

3. **Rows rejected by the global chartevents FHIR ETL: absent and not
   representable on affected rows.** The ETL applies `value IS NOT NULL` and
   excludes one hard-coded `(stay_id, charttime)` tuple before Observation
   creation (`fhir_observation_chartevents.sql:34-38`). For these two target
   itemids, source `value IS NULL` was 0/570 and the hard-coded tuple count was
   zero, so the demo bound is 0/570 omitted and FHIR/source counts were 570/570.
   If a full-data target row were omitted, the loss could affect row inclusion,
   temporal ranking, and carry-forward intervals; that affected-row loss would
   be potentially essential and must be assessed by the full comparator/judge,
   not hidden by a typed value NULL or an invented row.

4. **Synthetic interval endpoints:** `starttime` and `endtime` are not literal
   FHIR fields, but they are absent-but-derivable from the mapped effective
   dateTime, ICU period endpoints, item-derived type, and the canonical window
   expressions. The derivation preserves multiplicity; do not deduplicate on
   `(stay_id, starttime)` unless a later manifest proves that grain unique.

## Curated notes and provisional fragments

Established `MIMIC_NOTES.md` entries that changed this mapping decision were:

- raw NDJSON is stale, so all claims use the Delta warehouse;
- MIMIC ids live in `Identifier.value` as strings, so ICU `stay_id` is a
  separate string alias and final integer cast, never a resource UUID;
- Encounter stream selection uses the ICU identifier system, not `Encounter.class`;
- itemid-derived Observation codes are verbatim and must be filtered by exact
  system plus code, never by profile;
- Observation subtype profiles are warehouse-version dependent;
- Quantity value aliases materialize as `STRING` even though the raw Quantity is
  decimal, requiring a numeric cast;
- FHIR datetimes carry offsets and must be cast to `TIMESTAMP_NTZ`;
- chartevents effective times can be DST-normalized, and resource ids are opaque
  rather than a recovery channel.

All existing `MIMIC_NOTES.d/*.md` fragments were read as provisional leads:
`README.md`, `arb.md`, `blood_differential.md`, `cardiac_marker.md`,
`chemistry.md`, `code_status.md`, `complete_blood_count.md`, `coagulation.md`,
`crrt.md`, `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`,
`height.md`, `icp.md`, `icustay_detail.md`, `invasive_line.md`,
`kdigo_creatinine.md`, `milrinone.md`, `neuroblock.md`, `norepinephrine.md`,
`oxygen_delivery.md`, `phenylephrine.md`, `rhythm.md`, `rrt.md`,
`urine_output.md`, `vasopressin.md`, and `ventilator_setting.md`.

The relevant provisional leads about chartevents code systems, coding
cardinality, null-value/hard-coded-row omissions, choice aliases, datetime
normalization, and opaque Observation ids were independently checked against
this target. Leads about unrelated resources or fields (for example
MedicationAdministration, laboratory comparator values, `issued`, and
outputevents) were read but were not substituted into this mapping. No sibling
fragment was cited as evidence.
