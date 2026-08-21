# FHIR probe and mapping: `first_day_vitalsign`

**Probed:** 2026-08-21  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/first_day_vitalsign/source-analyst.md`  
**Canonical source SQL:** `mimic-iv/concepts/firstday/first_day_vitalsign.sql`  
**Dependency SQL:** `mimic-iv/concepts/measurement/vitalsign.sql`  
**Authoritative FHIR warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**FHIR engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone UTC  
**Read-only source oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB 1.5.5)

This is a mapping artifact only. No ViewDefinition, concept SQL, attempt artifact,
or resource identifier was authored or regenerated. All resource/reference keys
below are opaque equality keys.

## Scope and resource mapping

| MIMIC-IV source/interface | MIMIC-on-FHIR resource/interface | Role |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter` resources, selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Driving one-row-per-ICU-stay spine; supplies `subject_id`, `stay_id`, and `intime` |
| `mimiciv_icu.icustays.subject_id` | ICU `Encounter.subject` → `Patient.identifier` | Patient equality spine and final numeric `subject_id` |
| `mimiciv_icu.icustays.stay_id` | ICU `Encounter.identifier` | ICU-stay equality spine and final numeric `stay_id` |
| `mimiciv_icu.icustays.intime` | ICU `Encounter.period.start` | Window anchor; cast the served string to `TIMESTAMP_NTZ` |
| completed `mimiciv_derived.vitalsign` | Published `vitalsign` dependency interface | Supplies `charttime` and the eight consumed vital measures; consume it as `FROM vitalsign`, never rederive it in this concept |
| `mimiciv_icu.chartevents` (dependency provenance) | ICU chartevents `Observation` resources | Exact code/value/effective-time inputs owned by the `vitalsign` dependency |

The dependency's source SQL names `ce.stay_id`, but the published resource-key
shape strips the integer identifiers it replaces. The published `vitalsign`
interface therefore supplies `icu_encounter_key` and `patient_key`, not
`stay_id` or `subject_id`. Preserve the source equality join by joining
`vitalsign.icu_encounter_key` to the ICU Encounter `getResourceKey()` value;
recover/output `stay_id` and `subject_id` from the ICU Encounter/Patient
identifier paths. Do not join a published dependency on a dropped integer.

## Canonical FHIRPath projections

These are reusable extraction projections, not implementation artifacts.

### ICU chartevents Observation (`vitalsign_observation`)

```json
{
  "resource": "Observation",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "observation_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key"},
      {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
      {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
      {"path": "(effective).ofType(Period).end", "name": "effective_period_end"},
      {"path": "(effective).ofType(instant)", "name": "effective_instant"},
      {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
      {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
      {"path": "(value).ofType(string)", "name": "string_value"}
    ]},
    {"forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='220045' or code='225309' or code='225310' or code='225312' or code='220050' or code='220051' or code='220052' or code='220179' or code='220180' or code='220181' or code='220210' or code='224690' or code='220277' or code='225664' or code='220621' or code='226537' or code='223762' or code='223761' or code='224642'))",
     "column": [
       {"path": "code", "name": "item_code"},
       {"path": "system", "name": "item_system"},
       {"path": "display", "name": "item_display"}
     ]}
  ]
}
```

`effective_period_*` and `effective_instant` are probe-only aliases retained
to document the choice field. The served chartevents stream is dateTime-only;
the implementer must use `effective_datetime` and must not coalesce a native
instant alias with the string dateTime alias before casting. The constrained
coding group is deliberate even though the measured coding/resource ratio is
currently 1.000.

### ICU Encounter (`vitalsign_icu_encounter`)

```json
{
  "resource": "Encounter",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "icu_encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "period.start", "name": "intime_datetime"}
    ]},
    {"forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
     "column": [
       {"path": "system", "name": "stay_system"},
       {"path": "value", "name": "stay_id_str"}
     ]}
  ]
}
```

`period.end` and `partOf` were also probed but are not required by this source
SQL. Filter the Encounter stream by the ICU identifier system, not by
`Encounter.class`.

### Patient (`vitalsign_patient`)

```json
{
  "resource": "Patient",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
    ]}
  ]
}
```

## Source-column to FHIRPath mapping

FHIR identifier values and ViewDefinition aliases are strings. The final
concept SQL must cast `subject_id_str` and `stay_id_str` to the manifest's
`INTEGER` columns. Resource/reference keys remain uncast, type-prefixed opaque
strings and must be emitted alongside the two numeric identifiers as the
manifest key columns `patient_key` and `icu_encounter_key`.

### ICU Encounter and Patient spine

| Source column / role | Canonical mapping (`{path, name}`) | FHIR type / materialized type | Required use/type |
|---|---|---|---|
| `icustays.subject_id` | Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` → Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `Reference(Patient)` key + `Identifier.value string`; both aliases `STRING` | Equality join on `patient_key`; `CAST(subject_id_str AS INTEGER)` as `subject_id`; emit `patient_key` verbatim |
| `icustays.stay_id` | Encounter `{path: "value", name: "stay_id_str"}` inside `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')` | `Identifier.value string`, `STRING` | `CAST(stay_id_str AS INTEGER)` as `stay_id`; emit `icu_encounter_key` from `{path: "getResourceKey()", name: "icu_encounter_key"}` |
| ICU stay equality key | Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | Opaque type-prefixed resource key, `STRING` | Join to `vitalsign.icu_encounter_key`; never parse, strip, regenerate, or use as `stay_id` |
| `icustays.intime` | Encounter `{path: "period.start", name: "intime_datetime"}` | FHIR `dateTime`, materialized offset-bearing `STRING` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)` for both closed-window bounds |
| Patient equality key | Patient `{path: "getResourceKey()", name: "patient_key"}` | Opaque type-prefixed resource key, `STRING` | Equality/provenance and required output key only |

### Dependency input provenance and published output

| Source column / dependency field | Canonical mapping (`{path, name}`) | FHIR type / served alias type | Published/use type |
|---|---|---|---|
| `chartevents.subject_id` → dependency `subject_id` (internal source shape) | Observation `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` → Patient identifier `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | Reference key + `Identifier.value string`; `STRING` aliases | Internal dependency integer can be derived by cast, but published `vitalsign` keeps `patient_key` and strips `subject_id`; this consumer does not read dependency `subject_id` |
| `chartevents.stay_id` → dependency `stay_id` (internal source shape) | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}` → ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` and identifier `{path: "value", name: "stay_id_str"}` | Reference/resource key + identifier `string`; `STRING` aliases | Join the published dependency on the opaque ICU key; published `vitalsign` strips `stay_id`; final `stay_id` comes from the Encounter identifier |
| `chartevents.charttime` → `vitalsign.charttime` | Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | FHIR `dateTime`; ViewDefinition alias `STRING` with offset | `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` before dependency grouping and target windowing; published `charttime` is `TIMESTAMP_NTZ` |
| `chartevents.itemid` | Coding group `{path: "code", name: "item_code"}` plus `{path: "system", name: "item_system"}` and `{path: "display", name: "item_display"}` | `Coding.code`, `Coding.system uri`, `Coding.display string`; all `STRING` | Filter exact system + exact code inside `forEach`; use the item code as the conditional discriminator |
| `chartevents.valuenum` → numeric dependency measures | Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | FHIR `Quantity.value decimal`; ViewDefinition alias `STRING` (raw Delta value is decimal) | Cast to `DOUBLE` before conditional `AVG`/arithmetic |
| `chartevents.valueuom` | Observation `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | FHIR `Quantity.unit string`, `STRING` | Not consumed by `first_day_vitalsign`; do not require it, since 5,461/96,145 target rows have no unit |
| `chartevents.value` → `temperature_site` only | Observation `{path: "(value).ofType(string)", name: "string_value"}` | FHIR `valueString string`, `STRING` | Use only for dependency `MAX` at item `224642`; not read by this consumer |

The published `vitalsign` fields consumed by this concept are:

| Published dependency field | FHIR provenance | FHIR/served dependency type | Consumer use |
|---|---|---|---|
| `vitalsign.icu_encounter_key` | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}` | Opaque `STRING` | Equality join to ICU Encounter; replaces source `stay_id` |
| `vitalsign.patient_key` | Observation `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | Opaque `STRING` | Required key/provenance; source target does not join on subject |
| `vitalsign.charttime` | Observation effective dateTime path above | `TIMESTAMP_NTZ` | Closed temporal join predicate |
| `vitalsign.heart_rate` | Quantity path, code `220045`, conditional `valuenum > 0 AND valuenum < 300` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.sbp` | Quantity path, codes `220179,220050,225309`, `0 < valuenum < 400` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.dbp` | Quantity path, codes `220180,220051,225310`, `0 < valuenum < 300` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.mbp` | Quantity path, codes `220052,220181,225312`, `0 < valuenum < 300` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.resp_rate` | Quantity path, codes `220210,224690`, `0 < valuenum < 70` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.temperature` | Quantity path; `223761`: `(valuenum - 32) / 1.8` for `70 < valuenum < 120`; `223762`: raw `valuenum` for `10 < valuenum < 50`; then `ROUND(CAST(AVG(...) AS NUMERIC), 2)` | `DECIMAL(38,2)`, nullable | `MIN`/`MAX`/`AVG`; preserve the dependency's rounding before target aggregates |
| `vitalsign.spo2` | Quantity path, code `220277`, `0 < valuenum <= 100` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.glucose` | Quantity path, codes `225664,220621,226537`, `valuenum > 0` | `DOUBLE`, nullable | `MIN`/`MAX`/`AVG` |
| `vitalsign.sbp_ni` | Quantity path, code `220179`, `0 < valuenum < 400` | `DOUBLE`, nullable | Dependency output, not read by this consumer |
| `vitalsign.dbp_ni` | Quantity path, code `220180`, `0 < valuenum < 300` | `DOUBLE`, nullable | Dependency output, not read by this consumer |
| `vitalsign.mbp_ni` | Quantity path, code `220181`, `0 < valuenum < 300` | `DOUBLE`, nullable | Dependency output, not read by this consumer |
| `vitalsign.temperature_site` | String path, code `224642`, `MAX(string_value)` | `VARCHAR`, nullable | Dependency output, not read by this consumer |

### Final target outputs

The source output has 26 oracle columns: two identifiers and 24 aggregates.
The port must also carry the manifest's auxiliary `patient_key` and
`icu_encounter_key` key columns.

| Output column(s) | Mapping | Required type |
|---|---|---|
| `subject_id` | Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` reached via Encounter `patient_key` | `INTEGER` after cast |
| `stay_id` | ICU Encounter `{path: "value", name: "stay_id_str"}` inside the ICU identifier group | `INTEGER` after cast; keyed output |
| `patient_key` | Patient `{path: "getResourceKey()", name: "patient_key"}` or ICU Encounter subject reference | Opaque `VARCHAR`/`STRING`, type prefix intact |
| `icu_encounter_key` | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | Opaque `VARCHAR`/`STRING`, type prefix intact |
| `heart_rate_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.heart_rate)` | `DOUBLE` |
| `sbp_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.sbp)` | `DOUBLE` |
| `dbp_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.dbp)` | `DOUBLE` |
| `mbp_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.mbp)` | `DOUBLE` |
| `resp_rate_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.resp_rate)` | `DOUBLE` |
| `temperature_{min,max}` | `MIN`/`MAX(vitalsign.temperature)` | `DECIMAL(38,2)` |
| `temperature_mean` | `AVG(vitalsign.temperature)` after the dependency's two-decimal temperature result | `DOUBLE` |
| `spo2_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.spo2)` | `DOUBLE` |
| `glucose_{min,max,mean}` | `MIN`/`MAX`/`AVG(vitalsign.glucose)` | `DOUBLE` |

## Confirmed code system, literals, and coding cardinality

An unfiltered `forEach: "code.coding"` probe over all Observation resources
established the served systems before the target filter. The authoritative
Delta contained 668,862 chartevents-system coding rows over 668,862 distinct
Observation resources (ratio **1.000**). The exact target projection contained
96,145 coding rows over 96,145 distinct resources (ratio **1.000**).

The discriminator is the exact pair
`system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`
and `code`. The item code is the source `d_items.itemid` serialized verbatim as
a string. `d_items.itemid` is a global primary key with one `linksto` stream,
so the exact code separates this chartevents stream; do not use `meta.profile`.
The active source set has 19 codes. The commented `226329` line in
`vitalsign.sql` is not an active literal and is not part of the filter.
Every active literal had a non-zero source and served count in this demo; no
listed active code was absent from the served Delta, and no terminology
translation or CodeSystem expansion was used.

| Source itemid / served code | Served display | Source rows | FHIR coding rows/resources | Quantity / string | Conditional accepted events / charttime groups |
|---:|---|---:|---:|---:|---:|
| 220045 | Heart Rate | 13,913 | 13,913 / 13,913 | 13,913 / 0 | 13,910 / 13,910 |
| 225309 | ART BP Systolic | 486 | 486 / 486 | 486 / 0 | 486 / 486 (SBP) |
| 225310 | ART BP Diastolic | 486 | 486 / 486 | 486 / 0 | 486 / 486 (DBP) |
| 225312 | ART BP Mean | 488 | 488 / 488 | 488 / 0 | 486 / 486 (MBP) |
| 220050 | Arterial Blood Pressure systolic | 5,525 | 5,525 / 5,525 | 5,525 / 0 | 5,525 / 5,525 (SBP) |
| 220051 | Arterial Blood Pressure diastolic | 5,524 | 5,524 / 5,524 | 5,524 / 0 | 5,524 / 5,524 (DBP) |
| 220052 | Arterial Blood Pressure mean | 5,560 | 5,560 / 5,560 | 5,560 / 0 | 5,543 / 5,543 (MBP) |
| 220179 | Non Invasive Blood Pressure systolic | 8,347 | 8,347 / 8,347 | 8,347 / 0 | 8,347 / 8,347 (SBP/SBP_NI) |
| 220180 | Non Invasive Blood Pressure diastolic | 8,349 | 8,349 / 8,349 | 8,349 / 0 | 8,349 / 8,349 (DBP/DBP_NI) |
| 220181 | Non Invasive Blood Pressure mean | 8,342 | 8,342 / 8,342 | 8,342 / 0 | 8,342 / 8,342 (MBP/MBP_NI) |
| 220210 | Respiratory Rate | 13,913 | 13,913 / 13,913 | 13,913 / 0 | 13,866 / 13,866 (respiratory branch) |
| 224690 | Respiratory Rate (Total) | 1,331 | 1,331 / 1,331 | 1,331 / 0 | 1,330 / 1,330 (respiratory branch) |
| 220277 | O2 saturation pulseoxymetry | 13,540 | 13,540 / 13,540 | 13,540 / 0 | 13,540 / 13,540 |
| 225664 | Glucose finger stick (range 70-100) | 1,637 | 1,637 / 1,637 | 1,637 / 0 | 1,637 / 1,637 |
| 220621 | Glucose (serum) | 931 | 931 / 931 | 931 / 0 | 931 / 931 |
| 226537 | Glucose (whole blood) | 209 | 209 / 209 | 209 / 0 | 209 / 209 |
| 223762 | Temperature Celsius | 391 | 391 / 391 | 391 / 0 | 388 / 388 |
| 223761 | Temperature Fahrenheit | 3,379 | 3,379 / 3,379 | 3,379 / 0 | 3,379 / 3,379 |
| 224642 | Temperature Site | 3,794 | 3,794 / 3,794 | 0 / 3,794 | 3,794 / 3,794 (string MAX) |

The conditional accepted-event column is grouped by the measure named in
parentheses where a code participates in more than one measure. Across all
active codes, source rows after the dependency's global ETL conditions were
96,145, exactly equal to the FHIR target rows/resources. Source `value` was
non-null on 96,145/96,145; source `valuenum` was non-null on 92,351/96,145,
and the remaining 3,794 rows were the string `224642` temperature-site rows.
`Quantity.unit` was non-null on 90,684/96,145; it is not a required input.

## Choice types, timestamps, joins, grain, and NULL behavior

### Choice types and timestamp casts

For the 96,145 exact target Observation rows:

| Projection | FHIR type | Materialized type | Rows / non-null |
|---|---|---|---:|
| `(effective).ofType(dateTime)` | `dateTime` | `STRING` | 96,145 / 96,145 |
| `(effective).ofType(Period).start` | `Period.start` | `STRING` | 96,145 / 0 |
| `(effective).ofType(Period).end` | `Period.end` | `STRING` | 96,145 / 0 |
| `(effective).ofType(instant)` | `instant` | native Spark `TIMESTAMP` | 96,145 / 0 |
| `(value).ofType(Quantity).value` | `decimal` | ViewDefinition alias `STRING` | 96,145 / 92,351 |
| `(value).ofType(string)` | `string` | `STRING` | 96,145 / 3,794 |

An unfiltered chartevents-system choice probe independently found dateTime
668,862/668,862, Period.start/end 0/668,862, and instant 0/668,862. Thus the
dateTime-only result is not specific to one item among this Delta's
chartevents stream. FHIR dateTime strings carry offsets, but they are
de-identified MIMIC wall-clock values. Use direct
`TRY_CAST(alias AS TIMESTAMP_NTZ)` for both `effective_datetime` and
`intime_datetime`; never use an offset-aware `to_timestamp`/`TIMESTAMP` cast.

### Resource/reference-key joins

The Observation reference join resolved all 96,145/96,145 target rows to an
ICU Encounter and Patient. The ICU view had 140/140 `icu_encounter_key`,
`patient_key`, `stay_id_str`, and `intime_datetime` values; the Patient view
had 100/100 `patient_key` and `subject_id_str` values. The FHIR ICU spine
joined to DuckDB `mimiciv_icu.icustays` on the cast identifiers with exact
agreement for 140/140 `(subject_id, stay_id, intime)` rows. There were 140
distinct ICU stay identifiers, 140 distinct ICU Encounter keys, and 100
distinct Patient keys.

Join only by equality of the opaque keys. The source SQL has no separate
subject predicate in the `vitalsign` join; the ICU Encounter key is the exact
FHIR replacement for the source `stay_id` equality. Never parse an Encounter
or Patient key to recover an integer or time.

### Dependency and target grain

The source dependency groups raw chartevents by
`(subject_id, stay_id, charttime)`. DuckDB `mimiciv_derived.vitalsign` has
21,086 rows/groups over 140 stays. The served replay has 21,084
`(stay_id, charttime)` groups. The source/FHIR represented payload multiset
matched 96,145/96,145 rows after normalizing source float display precision;
the time-plus-payload multiset matched 96,131 rows, with 14 source-only and
14 candidate-only event keys from the documented upstream DST normalization.
The dependency output population in DuckDB was:

```text
rows/groups=21086, stays=140
heart_rate=13910, sbp=14002, dbp=14002, mbp=13994
sbp_ni=8347, dbp_ni=8349, mbp_ni=8342
resp_rate=14009, temperature=3764, temperature_site=3794
spo2=13540, glucose=2754
```

The target keeps the ICU Encounter spine on the left and uses a `LEFT JOIN`
to `vitalsign` with both inclusive time predicates:

```sql
ON e.icu_encounter_key = v.icu_encounter_key
AND v.charttime >= e.intime_datetime - INTERVAL 6 HOURS
AND v.charttime <= e.intime_datetime + INTERVAL 1 DAY
```

The final grain is one row per `icustays`/ICU Encounter, grouped by the stay
identifier (and carrying the patient/stay resource keys). On the demo, both
source and FHIR window probes had 6,067 dependency groups across all 140
stays, with 0 lower-boundary rows and 1 upper-boundary row; the strict
interior count was 6,066 in both. The window is a closed 30-hour interval
`[intime - 6 hours, intime + 24 hours]`, despite the source comment saying
“first 24 hours”.

### NULL behavior

The `LEFT JOIN` must remain in the join condition so every ICU stay survives.
`MIN`, `MAX`, and `AVG` ignore NULL dependency measures; do not coalesce a
missing aggregate to zero. On the 140 demo output rows, each of the three
aggregates for a measure has the same NULL pattern on source and FHIR:

| Measure | Rows with non-NULL min/max/mean | Rows with all three aggregate values NULL |
|---|---:|---:|
| heart rate | 140 | 0 |
| SBP | 139 | 1 |
| DBP | 139 | 1 |
| MBP | 139 | 1 |
| respiratory rate | 140 | 0 |
| temperature | 135 | 5 |
| SpO2 | 140 | 0 |
| glucose | 139 | 1 |

## Oracle checks and served-data quirks

The source/FHIR replay of the first-day query produced 140/140 rows and
140/140 distinct stay keys. `subject_id`, `stay_id`, all non-temperature
aggregates, temperature min/max, and all aggregate NULL patterns agreed with
the DuckDB `mimiciv_derived.first_day_vitalsign` result. `temperature_mean`
was within `1e-6` on 135/135 non-NULL rows (maximum absolute difference
`4.62e-7`; 72 rows differed only at a stricter `1e-9` float comparison), due
to decimal-to-floating aggregate representation, not a missing FHIR element.

The chartevents effective-time transformation is the important semantic
coverage boundary. The upstream ETL writes `charttime` through a
`TIMESTAMPTZ` cast before `Observation.effectiveDateTime`; source spring-
forward-gap 02:xx wall times can therefore be served as 03:xx. In this probe,
the source/FHIR time-plus-payload comparison had 14 mismatched event keys and
the dependency group comparison had three source-only groups and one
candidate-only group. The original source wall time is not in another FHIR
element and cannot be recovered from an opaque resource ID. It can change
dependency grouping or a window boundary, so it is potentially essential on
the affected rows. The measured demo window membership was nevertheless
identical (6,067 matched groups, including the same one upper-boundary row),
and the first-day aggregate replay had no demonstrated row-inclusion or
clinically meaningful value change beyond the tiny temperature-mean numeric
representation difference. This is a later comparator/equivalence-judge
issue, not permission to shift timestamps or reconstruct IDs.

The chartevents ETL also has global `value IS NOT NULL` and one hard-coded
stay/time-group exclusion. In this target's demo source there were zero
NULL-value rows and zero rows at the hard-coded tuple; all 96,145 target
source rows survived and all 96,145 FHIR resources were present. If a full
target row is omitted by either predicate, the missing row is not representable
and could affect charttime grouping and all downstream aggregates. The demo
bound is zero; no whole-concept decision is made at the prober stage.

Missing `Quantity.unit` is ancillary: it is absent on 5,461 target rows and
the source SQL never reads it. `temperature_site` is also not consumed by this
target. Neither should be used as a filter or a join key.

## Notes and provisional fragments consulted

The established entries in `MIMIC_NOTES.md` that changed this mapping were:

* Delta tables, not stale NDJSON or the unauthorized live server, are the
  source of truth.
* MIMIC numeric identifiers are `identifier.value` strings; resource/reference
  keys are separate required opaque key columns and must not become numeric
  IDs.
* `getResourceKey()`/`getReferenceKey()` are type-prefixed opaque equality
  keys; no parsing, UUID regeneration, or timestamp/value inference is valid.
* Encounter streams require the exact ICU identifier system; `Encounter.class`
  does not discriminate them.
* Itemid-derived Observation codes are verbatim and must be discriminated by
  exact `system + code`, never `meta.profile`; the `d_items` global-key warning
  supports the chartevents rule.
* Choice fields require separate `ofType()` aliases, Quantity aliases are
  string-like and need numeric casts, and served datetimes must use
  `TIMESTAMP_NTZ`.
* The established chartevents temperature Fahrenheit/Celsius split and
  glucose code set match the dependency's literal SQL.
* The established DST and essential-loss rules prohibit hiding the lost
  source wall time with a typed NULL or an ID side channel.

The following provisional sibling fragments were read as leads and checked
only where relevant against this fresh Delta/oracle probe:

* `MIMIC_NOTES.d/vitalsign.md`: the `issued`/storetime lead is irrelevant
  because this concept does not use `storetime`; the hard-coded chartevents
  omission lead was checked against the ETL and the target-specific zero-row
  bound.
* `MIMIC_NOTES.d/first_day_bg.md`: its labevents DST lead does not apply to
  this ICU chartevents dependency.
* `MIMIC_NOTES.d/first_day_urine_output.md`: outputevents system/effective
  findings do not apply; the ICU Encounter identifier/window spine was
  independently checked here.
* `MIMIC_NOTES.d/height.md`: the mixed-alias effective-type lead was verified
  for the relevant chartevents stream; the historical UUID recovery lead was
  rejected and not used.
* `MIMIC_NOTES.d/weight_durations.md`: the chartevents omission and ICU
  period-DST leads were checked; all 140 ICU `intime` values agreed in this
  demo and no selected target omission was present.
* `MIMIC_NOTES.d/icustay_times.md`: its aggregate DST non-commutation lead is
  consistent with the 3 source-only/1 candidate-only dependency groups; no
  ID-based correction was adopted.

No sibling claim was treated as evidence without the fresh probe. The new
dataset/IG-wide findings confirmed during this probe were appended only to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_vitalsign.md`:

1. All 668,862 served chartevents Observations use `effective.ofType(dateTime)`
   (Period and instant variants are empty).
2. The chartevents ETL's global null-value and hard-coded stay/time exclusion
   is a coverage boundary; this target had zero affected demo rows.
