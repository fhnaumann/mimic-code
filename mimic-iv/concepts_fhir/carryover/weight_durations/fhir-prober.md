# FHIR prober mapping — `weight_durations` (attempt 0003 rerun)

## Probe scope and authoritative sources

- Canonical source SQL: `mimic-iv/concepts/demographics/weight_durations.sql`.
- Reused source analysis: `mimic-iv/concepts_fhir/carryover/weight_durations/source-analyst.md`.
- Authoritative FHIR source: `/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded Pathling 9.6.0 on Spark 4.0.2. No HTTP Pathling server was used.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB 1.5.5).
- Canonical ViewDefinition shape: `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- ETL statements checked: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:8-9,20-23,34-38,58-80` and `/Users/nau025/Documents/mimic-fhir/sql/fhir_encounter_icu.sql:30-32,44-46,77-100`.
- This is a mapping artifact only. No attempt ViewDefinition or `concept.sql` was authored.

## Source table to FHIR resource mapping

| MIMIC-IV source table | FHIR resource/stream | Mapping role |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation`, ICU chartevents stream | Exact item-code filter, numeric Quantity, effective dateTime, patient reference, and ICU Encounter reference. |
| `mimiciv_icu.icustays` | `Encounter`, ICU stream selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | `stay_id` identifier, `intime`/`outtime` period endpoints, patient reference, and the encounter resource key used for equality joins. |

The Observation `encounter.getReferenceKey(Encounter)` equals the ICU
Encounter `getResourceKey()` byte-for-byte. It is an opaque equality-join key;
it is not a `stay_id` and must not be parsed or regenerated. The numeric
`stay_id` comes from the ICU Encounter's `identifier.value`.

## Confirmed coded discriminator

The source SQL names exactly `226512` and `224639`. The authoritative Delta
stores both as decimal strings in
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
No alternate system was observed for either code. The discriminator is
**system plus exact code**, never `meta.profile`; the merged-data profile is not
a stable stream discriminator. `d_items.itemid` is a global primary key with a
single `linksto` value, so these exact codes identify the chartevents stream.

Canonical constrained coding group:

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

Fresh demo counts (source oracle → constrained FHIR coding rows → distinct
FHIR resources):

| Source itemid / FHIR code | Source rows | FHIR coding rows | FHIR resources | Display |
|---:|---:|---:|---:|---|
| `226512` | 129 | 129 | 129 | `Admission Weight (Kg)` |
| `224639` | 441 | 441 | 441 | `Daily Weight` |
| **total** | **570** | **570** | **570** | |

The constrained target has 570 coding rows over 570 distinct Observation
resources, ratio **1.000**. An unfiltered `code.coding` projection over the
current Delta had 813,540 coding rows over 813,540 distinct Observation
resources, also ratio **1.000**. Keep the system/code constraint inside the
repeating group even though this warehouse currently has one coding per
resource.

## Canonical ViewDefinition projections

These are mapping projections, not attempt artifacts.

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
`string_value` were 0/570. Materialized types were:

| Alias | FHIR type | Materialized Delta/ViewDefinition type | Count |
|---|---|---|---:|
| `observation_key` | resource key | `STRING` | 570/570 |
| `patient_key` | `Reference(Patient)` key | `STRING` | 570/570 |
| `encounter_key` | `Reference(Encounter)` key | `STRING` | 570/570 |
| `effective_datetime` | `dateTime` | `STRING` with offset-bearing ISO-8601 text | 570/570 |
| `effective_period_start` | `Period.start` | `STRING` | 0/570 |
| `effective_instant` | `instant` | native Spark `TIMESTAMP` | 0/570 |
| `quantity_value` | `Quantity.value` decimal | ViewDefinition alias `STRING`; raw Delta Quantity value `decimal(32,6)` | 570/570 |
| `quantity_unit` | `Quantity.unit` string | `STRING` | 570/570 |
| `quantity_comparator` | `Quantity.comparator` code | `STRING` | 0/570 |
| `string_value` | `valueString` | `STRING` | 0/570 |

Do not coalesce the unused native `instant` alias with the string dateTime
alias before casting: the aliases have different materialized types. The
target's Quantity unit was `kg` on 570/570 rows.

### ICU Encounter (`icustays`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "intime_datetime" },
    { "path": "period.end", "name": "outtime_datetime" }
  ]
}
```

The unfiltered Encounter view has 637 resources. The ICU identifier path
selects 140/140 resources, with 140/140 non-null `icu_encounter_key`,
`patient_key`, `stay_id_str`, `intime_datetime`, and `outtime_datetime`; the
140 `stay_id_str` values are distinct. `period.start` and `period.end`
materialize as offset-bearing FHIR `dateTime` strings (`STRING`). The three
Encounter identifier systems in the probe were hospital 275, ICU 140, and ED
222; `Encounter.class` was not used.

## Source column → FHIRPath mapping and target types

| Source column / derived output | Canonical mapping `{path, name}` | FHIR type / materialized type | Target type and evidence/requirement |
|---|---|---|---|
| `chartevents.itemid` | `{ "path": "code", "name": "item_code" }` inside the constrained coding group; companion `{ "path": "system", "name": "item_system" }` and `{ "path": "display", "name": "item_display" }` | `Coding.code` / `uri` / `string`; all `STRING` | Filter exact system and string code first; `CAST(item_code AS INTEGER)` recovers 226512/224639. |
| `chartevents.stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }`; then `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | Reference/resource keys are opaque `STRING`; Identifier.value is FHIR `string`, materialized `STRING` | Equality join matched 570/570 target Observations to ICU Encounters; final `stay_id` must be `CAST(stay_id_str AS INTEGER)`. Never use a UUID as `stay_id`. |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | FHIR `Identifier.value` `string`, `STRING` | 140/140 identifier values agreed with the DuckDB source. Final target is `INTEGER`. |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`, offset-bearing `STRING` | `CAST(effective_datetime AS TIMESTAMP_NTZ)` agreed with source wall time 570/570. Final `starttime`/`endtime` target type is `TIMESTAMP`; keep the Spark expression/output wall-clock-preserving as `TIMESTAMP_NTZ`, not plain offset conversion. |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`, offset-bearing `STRING` | Direct source agreement 140/140 in the demo. Cast to `TIMESTAMP_NTZ` before subtracting two hours or comparing for `wt_fix`. |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime_datetime" }` | FHIR `dateTime`, offset-bearing `STRING` | Direct source agreement 140/140 in the demo. Cast to `TIMESTAMP_NTZ` before adding the two-hour terminal extension. |
| `chartevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR Quantity decimal; alias `STRING`; raw value `decimal(32,6)` | Cast to a numeric/decimal before `ROUND(..., 3)`. The canonical three-decimal weight matched the source for 570/570 events and the complete derived interval multiset matched 578/578 rows. |
| `chartevents.valueuom` | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | FHIR string, `STRING` | `kg` and source unit agreed 570/570; the canonical output does not retain this field. |
| `chartevents.value` (not used by source SQL) | `{ "path": "(value).ofType(string)", "name": "string_value" }` | FHIR `string`, `STRING` | 0/570 for this numeric target because the ETL selects Quantity when `valuenum` is non-null. Do not substitute it for `quantity_value`. |
| `weight_type` | Derived from `{ "path": "code", "name": "item_code" }` | SQL string | `226512 → 'admit'`, `224639 → 'daily'`; exactly derivable from the surviving discriminator. Final manifest target is `VARCHAR`; use a bounded Spark cast such as `VARCHAR(255)`. |
| `weight` | Derived from `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR input alias `STRING`; source output numeric | `ROUND(CAST(quantity_value AS DECIMAL), 3)`. Final manifest target is `DECIMAL(38,3)`. |
| `starttime` | Ordinary event: `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }`; first admission/backfill: `{ "path": "period.start", "name": "intime_datetime" }` minus two hours | Mapped inputs are `STRING` aliases cast to `TIMESTAMP_NTZ` | Absent as one literal FHIR field but derived by replaying the canonical CASE, item-derived type/rank, and ICU period start. Final manifest target is `TIMESTAMP`. |
| `endtime` | Next derived `starttime` within stay; terminal fallback from `{ "path": "period.end", "name": "outtime_datetime" }` plus two hours | Mapped input is a `STRING` alias cast to `TIMESTAMP_NTZ` | Absent as one literal FHIR field but derived by the canonical `LEAD`/fallback while preserving `UNION ALL` multiplicity. Final manifest target is `TIMESTAMP`. |
| Required `icu_encounter_key` output key | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` on the ICU Encounter | type-prefixed opaque resource key, `STRING` | Emit verbatim, including `Encounter/`; do not cast, strip, parse, regenerate, or use it to recover source times. Manifest key column. |
| Required `patient_key` output key | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` on the ICU Encounter (also available on Observation as the same path) | type-prefixed opaque reference key, `STRING` | Emit verbatim, including `Patient/`; equality joins are allowed. Manifest key column. |

The full manifest target schema is `stay_id INTEGER`, `starttime TIMESTAMP`,
`endtime TIMESTAMP`, `weight DECIMAL(38,3)`, and `weight_type VARCHAR`, with
manifest key columns `icu_encounter_key` and `patient_key`.

## Equality joins, multiplicity, and oracle checks

- The FHIR equality join `Observation.encounter.getReferenceKey(Encounter) = ICU Encounter.getResourceKey()` matched 570/570 target Observations, with zero unmatched rows and 137 distinct ICU stays. The target covered 100 distinct patients.
- The FHIR event key multiset `(stay_id, itemid, effective wall time)` matched the selected source multiset exactly: 570 FHIR rows, 570 source rows, 570 unique keys on each side, zero FHIR-only and zero source-only keys.
- On those 570 matched events, effective wall time, three-place rounded Quantity value, and unit each agreed 570/570.
- The read-only source oracle found no duplicate `(stay_id, charttime, itemid)` groups for the selected, positive, `<1500` rows; maximum multiplicity was one. This is a measured property of this target, not permission to deduplicate the FHIR resource stream generally. The canonical derived query still requires `UNION ALL` and preserves multiplicity.
- Replaying the canonical window/arithmetic logic over mapped FHIR columns and over the source oracle produced 578 rows on both sides, 578 unique full tuples, and an exact full-tuple multiset match. This includes synthetic `wt_fix` rows.

## ETL omission predicates

The chartevents ETL applies global predicates before creating an Observation:
`value IS NOT NULL` and exclusion of
`(stay_id=34934165, charttime='2151-10-03 05:14:00')`. For this exact target,
the source oracle had `value` non-null on 570/570 rows and zero rows at the
hard-coded tuple; all 570 selected source rows survived the numeric range
filter and all 570 target Observations were present. The predicates are still
part of the mapping's coverage boundary: if a full-data selected row is
omitted, the missing row is not reconstructable from a FHIR resource and can
affect ranking, `LEAD`, and interval inclusion.

## Gaps and bounded essentiality

1. **Synthetic `starttime`/`endtime`: absent but derivable.** The FHIR model
   has no single interval for this output. They are exactly derivable from the
   mapped item code, Quantity, effective dateTime, ICU period endpoints, and
   the canonical windows on the demo: 578/578 full derived tuples matched.
   Preserve duplicate rows and do not deduplicate on `(stay_id, starttime)`.

2. **`weight_type`: absent but derivable.** The surviving exact coding
   discriminator identifies the two branches, so this is not a representation
   gap: `226512` is `admit` and `224639` is `daily`.

3. **Pre-ETL chartevents wall `charttime`: not representable on DST-gap
   rows.** The ETL casts through `TIMESTAMPTZ` before writing
   `Observation.effectiveDateTime` (`fhir_observation_chartevents.sql:9,67`).
   The original nonexistent New York spring-forward 02:xx wall time is not in
   a FHIR element. Resource/reference ids are opaque identity and are not a
   permitted recovery channel. The fresh demo bound was 0/570 target chart
   rows in the gap, with 570/570 wall-time agreement. On affected full-data
   rows this can be essential because charttime controls per-stay/type
   `ROW_NUMBER`, stay-wide `LEAD`, strict backfill inclusion, and interval
   boundaries. Attempt 0002's full diagnosis measured eight downstream
   chartevents/`LEAD` residual conflicts; the known upstream-DST exception is
   for the comparator/equivalence judge, not an early prober-stage block.

4. **Pre-ETL ICU `intime`/`outtime`: not representable on DST-gap rows.** The
   ICU ETL casts both endpoints through `TIMESTAMPTZ` and writes only the
   transformed values to `Encounter.period.start/end`
   (`fhir_encounter_icu.sql:31-32,97-100`). The fresh demo bound was 0/140
   ICU `intime` gaps and 0/140 `outtime` gaps; direct endpoint agreement was
   140/140, and `intime - 2 hours`/`outtime + 2 hours` arithmetic agreement was
   140/140. The invalidation diagnosis is nevertheless real: when a source
   ICU `intime` is shifted from 02:xx to 03:xx, subtracting two hours can move
   the resulting `weight_durations` `starttime` outside the DST gap, so a
   final-value replay looking only for a 02:xx→03:xx endpoint conflict can
   miss it. Attempt 0002's full diagnosis measured nine such ICU-intime-derived
   residual conflicts. The original endpoint is not recoverable from served
   FHIR or opaque identity; this is the same known upstream-DST exception,
   despite its possible effects on a key and on interval timing.

5. **Global ETL row omissions: not representable on omitted rows.** The exact
   target bound is 0/570 omitted rows (`value IS NULL` 0/570; hard-coded tuple
   0). If present in the full target, the loss can change row inclusion and
   temporal windows, so it must be reported by the full comparator rather than
   replaced by an invented row or a value NULL.

## Curated notes and provisional fragments read

Curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md` entries that changed this
mapping decision were: Delta rather than stale NDJSON is authoritative; MIMIC
identifiers are string `identifier.value` fields rather than resource UUIDs;
resource/reference keys are type-prefixed opaque equality keys; Encounter
streams are selected by identifier system rather than class; itemid codes are
verbatim and discriminated by system plus exact code rather than profile;
choice fields need one alias per variant; Quantity value aliases materialize
as `STRING`; FHIR datetimes must be cast to `TIMESTAMP_NTZ`; and chartevents
and ICU Encounter endpoints can receive irreversible DST normalization.

Read as provisional leads and checked where relevant against this target:
`MIMIC_NOTES.d/weight_durations.md`, `icustay_times.md`, `icustay_detail.md`,
`rrt.md`, `oxygen_delivery.md`, `crrt.md`, `coagulation.md`, `gcs.md`,
`height.md`, `icp.md`, `ventilator_setting.md`, and `vitalsign.md`.
The relevant leads on chartevents coding, one-coding cardinality, ETL
omissions, mixed effective-choice materialization, DST normalization, ICU
Encounter period transformation, and opaque-id policy were checked against
the fresh Delta/oracle probe above. Unrelated medication, laboratory, and
other resource claims were not substituted into this mapping.

No new dataset-wide quirk was discovered in this rerun, so
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/weight_durations.md` was not appended.
