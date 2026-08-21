# FHIR probe and mapping: `first_day_gcs`, attempt_0001

**Concept:** `firstday/first_day_gcs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/first_day_gcs/source-analyst.md`  
**Canonical source SQL:** `mimic-iv/concepts/firstday/first_day_gcs.sql`  
**Authoritative FHIR warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2  
**Read-only source oracle:** `/Users/nau025/warehouses/mimic-iv-duckdb-demo/icu/*.csv.gz` (DuckDB 1.5.5-compatible MIMIC-IV demo source)  
**Dependency:** completed `gcs` view; the target must consume it and must not rederive GCS from Observation resources.

This is a mapping artifact, not a ViewDefinition or terminal representability
decision. Resource/reference keys below are opaque equality keys. No resource
id was parsed, regenerated, hashed, hardcoded, brute-forced, or used to infer
an identifier, timestamp, or source label.

## Resource and dependency mapping

| MIMIC-IV source/interface | MIMIC-on-FHIR resource/interface | Role |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | One output row per ICU stay; supplies the stay identity and `intime` anchor |
| `mimiciv_icu.icustays.subject_id` | ICU `Encounter.subject` → `Patient.identifier` | Patient equality spine and final numeric `subject_id` |
| `mimiciv_icu.icustays.stay_id` | ICU `Encounter.identifier` with the ICU identifier system | Final numeric `stay_id` and dependency equality spine |
| `mimiciv_icu.icustays.intime` | ICU `Encounter.period.start` | Inclusive `-6 hour` / `+1 day` target window anchor |
| completed `mimiciv_derived.gcs` | Published derived dependency interface `gcs` | Supplies `charttime`, `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable`; consume `FROM gcs` |
| `mimiciv_icu.chartevents` (dependency provenance only) | ICU chartevents `Observation` | Upstream inputs owned by `gcs`; not an additional source for `first_day_gcs` |

The completed `gcs` attempt exposes `patient_key` and
`icu_encounter_key` alongside its derived fields. The published dependency
interface is keyed by those resource keys; the integer `subject_id`/`stay_id`
identifiers are not a valid replacement for the key join. The target should
therefore join `gcs.icu_encounter_key` to the ICU Encounter resource key, not
rederive or rejoin raw `chartevents` on `stay_id`.

Recommended consumer spine:

```sql
FROM icu_encounter e
LEFT JOIN gcs g
  ON e.icu_encounter_key = g.icu_encounter_key
 AND g.charttime >= e.intime_datetime - INTERVAL 6 HOURS
 AND g.charttime <= e.intime_datetime + INTERVAL 1 DAY
```

Keep this as a `LEFT JOIN` so every ICU Encounter survives. Apply the source
window and `ROW_NUMBER()` selection to the completed dependency rows, ordering
by `gcs ASC NULLS LAST, charttime DESC NULLS LAST`. Do not inline the GCS
`itemid` pivots, six-hour carry-forward, defaults, or No Response-ETT logic in
this consumer.

## Canonical FHIRPath projections

These are reusable extraction mappings. The output aliases from the
ViewDefinition are FHIR/Pathling strings unless noted below; the final SQL
must cast identifier strings to the manifest types.

### Patient

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

### ICU Encounter

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

Filter the Encounter stream with the ICU identifier system, never
`Encounter.class`. The Delta has 637 Encounter resources: 275 hospital, 140
ICU, and 222 ED. The ICU identifier selects exactly the 140 ICU stays in the
demo.

### Upstream GCS Observation provenance (owned by `gcs`, not this consumer)

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
      {"path": "(value).ofType(string)", "name": "value_string"}
    ]},
    {"forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='223900' or code='223901' or code='220739'))",
     "column": [
       {"path": "code", "name": "item_code"},
       {"path": "system", "name": "item_system"},
       {"path": "display", "name": "item_display"}
     ]}
  ]
}
```

The coding restriction belongs inside `forEach`. The discriminator is the
exact pair `item_system + item_code`, never `meta.profile`. The Delta has no
served `CodeSystem` table, so the system and code set are established from the
served Observation codings and the ETL/source dimension, not terminology
expansion.

## Source-column → FHIRPath mapping and types

### ICU identity and time spine

| Source column / role | Canonical mapping (`{path, name}`) | FHIR type / materialized type | Required final/use type |
|---|---|---|---|
| `icustays.subject_id` | Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key + `Identifier.value` string; aliases `STRING` | Equality join on `patient_key`; `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; emit `patient_key` unchanged |
| `icustays.stay_id` | Encounter `{ "path": "value", "name": "stay_id_str" }` inside `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')` | `Identifier.value` string; alias `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; emit `icu_encounter_key` alongside it |
| ICU Encounter identity | Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Opaque, type-prefixed resource key string; `STRING` | Equality join to `gcs.icu_encounter_key` and required key output; never parse or substitute for `stay_id` |
| Patient identity | Patient `{ "path": "getResourceKey()", "name": "patient_key" }` | Opaque, type-prefixed resource key string; `STRING` | Equality join/provenance and required key output; never parse or substitute for `subject_id` |
| `icustays.intime` | Encounter `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`; Pathling alias is offset-bearing `STRING` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)` → `TIMESTAMP` window anchor; do not offset-convert |

### Upstream GCS dependency inputs

| Source column / dependency field | Canonical mapping (`{path, name}`) | FHIR type / served alias type | Published dependency/use type |
|---|---|---|---|
| `chartevents.subject_id` → internal `gcs.subject_id` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient identifier path above | Reference key + identifier string; aliases `STRING` | `gcs` consumer does not read this integer; preserve `patient_key` |
| `chartevents.stay_id` → internal `gcs.stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` → Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Reference/resource key string; aliases `STRING` | Published `gcs` equality join key; recover final `stay_id` only from ICU Encounter identifier |
| `chartevents.charttime` → `gcs.charttime` | Observation `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`; alias `STRING` with offset | Dependency `TIMESTAMP_NTZ`; target temporal ordering/windowing |
| `chartevents.itemid` | Coding `{ "path": "code", "name": "item_code" }` with `{ "path": "system", "name": "item_system" }` and `{ "path": "display", "name": "item_display" }` | `Coding.code`, `Coding.system`, `Coding.display`; all `STRING` | Owned by `gcs`; exact system/code conditional pivot only there |
| `chartevents.valuenum` | Observation `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR `Quantity.value` decimal; ViewDefinition alias `STRING` | `gcs` casts to numeric and emits `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs`; target consumes derived `FLOAT`s |
| `chartevents.valueuom` | Observation `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | FHIR `Quantity.unit` string; alias `STRING` | Not read by `gcs` or `first_day_gcs`; demo 0/9,791 populated for GCS |
| `chartevents.value` | Observation `{ "path": "(value).ofType(string)", "name": "value_string" }` | FHIR `value[x]` string; alias `STRING` | Required source discriminator for `No Response-ETT`, but absent on numeric served rows; not representable |

The dependency's published fields consumed by this concept are:

| Published `gcs` field | Underlying provenance | Type | Consumer role |
|---|---|---|---|
| `gcs.icu_encounter_key` | Observation encounter reference key | opaque `STRING` | Join to ICU Encounter; replaces source `stay_id` join |
| `gcs.patient_key` | Observation subject reference key | opaque `STRING` | Required key/provenance; join consistency |
| `gcs.charttime` | Observation effective dateTime | `TIMESTAMP_NTZ` | Closed window and latest tie-break |
| `gcs.gcs` | Completed dependency calculation | nullable `FLOAT` | `gcs_min` source after `gcs_seq = 1` |
| `gcs.gcs_motor` | Completed dependency component | nullable `FLOAT` | `gcs_motor` |
| `gcs.gcs_verbal` | Completed dependency component | nullable `FLOAT` | `gcs_verbal` |
| `gcs.gcs_eyes` | Completed dependency component | nullable `FLOAT` | `gcs_eyes` |
| `gcs.gcs_unable` | Completed dependency flag, typed `INTEGER` | nullable `INTEGER` | `gcs_unable`; do not reconstruct it in this consumer |

### Final `first_day_gcs` outputs

| Source/output column | Canonical mapping/provenance | Required output type |
|---|---|---|
| `subject_id` | Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` reached through ICU Encounter `patient_key` | `INTEGER` after cast |
| `stay_id` | ICU Encounter `{ "path": "value", "name": "stay_id_str" }` in the ICU identifier group | `INTEGER` after cast; natural key |
| `gcs_min` | Completed `gcs.gcs`, selected by the target's `ROW_NUMBER()` | `FLOAT` |
| `gcs_motor` | Completed `gcs.gcs_motor` on the same selected dependency row | `FLOAT` |
| `gcs_verbal` | Completed `gcs.gcs_verbal` on the same selected dependency row | `FLOAT` |
| `gcs_eyes` | Completed `gcs.gcs_eyes` on the same selected dependency row | `FLOAT` |
| `gcs_unable` | Completed `gcs.gcs_unable` on the same selected dependency row | `INTEGER` |
| required companion `patient_key` | Patient `{ "path": "getResourceKey()", "name": "patient_key" }` | opaque `STRING`, type prefix intact |
| required companion `icu_encounter_key` | Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque `STRING`, type prefix intact |

The natural comparison grain is one row per `stay_id` (140/140 in the demo;
73,181 rows in the full manifest). `gcs_seq` is an internal ordinal and is
not an output column.

## Confirmed code system and literal counts

The source dependency names exactly three itemids. Fresh Delta projection
counts were:

| Source `itemid` | FHIR `Coding.code` | FHIR `Coding.display` | system | coding rows | distinct resources |
|---:|---|---|---|---:|---:|
| 220739 | `"220739"` | `GCS - Eye Opening` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | 3,274 | 3,274 |
| 223900 | `"223900"` | `GCS - Verbal Response` | same | 3,266 | 3,266 |
| 223901 | `"223901"` | `GCS - Motor Response` | same | 3,251 | 3,251 |
| **target total** | — | — | — | **9,791** | **9,791** |

The coding-per-resource ratio is **1.000** for the entire chartevents stream
(668,862/668,862) and for this exact target projection (9,791/9,791). Each
code is also 1.000. A constrained `forEach` is still required so a future
second coding cannot fan out the dependency.

The three `d_items` rows are unique and each has `linksto='chartevents'` in
the source dimension. The system plus exact code is therefore a valid
discriminator in this warehouse; it does not rely on `meta.profile`. The
shared `mimic-d-items` system used by outputevents/datetimeevents is not the
system for these GCS codings, and the global `d_items.itemid`/`linksto` rule
would still distinguish an exact code if a shared-system stream were involved.

## Probe counts and oracle checks

For the exact three-code Observation projection, rows vs non-null were:

| Alias/path | Rows | Non-null |
|---|---:|---:|
| `observation_key` / `getResourceKey()` | 9,791 | 9,791 |
| `patient_key` / `subject.getReferenceKey(Patient)` | 9,791 | 9,791 |
| `icu_encounter_key` / `encounter.getReferenceKey(Encounter)` | 9,791 | 9,791 |
| `effective_datetime` / `(effective).ofType(dateTime)` | 9,791 | 9,791 |
| `effective_period_start` / `(effective).ofType(Period).start` | 9,791 | 0 |
| `effective_period_end` / `(effective).ofType(Period).end` | 9,791 | 0 |
| `effective_instant` / `(effective).ofType(instant)` | 9,791 | 0 |
| `quantity_value` / `(value).ofType(Quantity).value` | 9,791 | 9,791 |
| `quantity_unit` / `(value).ofType(Quantity).unit` | 9,791 | 0 |
| `value_string` / `(value).ofType(string)` | 9,791 | 0 |
| `item_code`, `item_system`, `item_display` | 9,791 each | 9,791 each |

The full chartevents-system probe independently found dateTime 668,862/668,862,
Period start/end 0/668,862, and instant 0/668,862. Quantity aliases are
materialized as `STRING`; cast `quantity_value` to `DOUBLE` inside the upstream
dependency. Datetimes are offset-bearing strings representing MIMIC wall-clock
values; use direct `TRY_CAST(... AS TIMESTAMP_NTZ)`, not offset-aware parsing.

ICU Encounter probe counts were 140 resources, 140/140 resource keys, patient
references, ICU identifiers, and `period.start` values. Patient probe counts
were 100 resources, 100/100 patient keys and patient identifier values. Joining
the Observation encounter reference to the ICU Encounter view resolved
9,791/9,791 rows, with 9,791/9,791 patient-reference consistency. The
source-to-FHIR equality checks were exact:

| Check | Result |
|---|---:|
| source `icustays` rows matched to ICU Encounter by `stay_id` identifier | 140/140 |
| `(subject_id, stay_id, intime)` source/FHIR spine agreement | 140/140 |
| source GCS rows matched by `(stay_id, charttime, itemid)` after the FHIR wall-clock cast | 9,791/9,791 |
| numeric `valuenum` vs served Quantity value | 9,791/9,791 exact |
| source subject/stay values vs Patient/Encounter identifiers | 9,791/9,791 exact |

The source demo had 3,274 / 3,266 / 3,251 rows for the three itemids,
`value IS NOT NULL` on all 9,791, and no hard-coded excluded tuple. Thus the
chartevents ETL's global omission has a 0-row bound for this demo target.

## No Response versus No Response-ETT: essential representability gap

The source `chartevents` oracle has, for item `223900`:

* `No Response-ETT`: 1,348 rows, all with `valuenum=1`;
* `No Response`: 78 rows, all with `valuenum=1`;
* served verbal Observations: 3,266 rows, of which 1,426 have Quantity value
  `1` and 0 have `valueString`.

The two source states are therefore indistinguishable in served FHIR. Both
become `Observation.value.ofType(Quantity).value = 1`; neither retains the
source label in `valueString`, `component`, or another mapped element. A
Quantity-1 heuristic has measured accuracy only 1,348/1,426 = 94.53% and a
5.47% false-positive rate (78/1,426). It is not a mapping and must not be
used. `Observation.getResourceKey()` is opaque and cannot be used to recover
the label or `charttime`.

This is an **absent and not representable** input, not an approximable input.
The missing discriminator is essential to `first_day_gcs`: it changes
`gcs_unable`, `gcs_verbal`, and total `gcs`, and can change the minimum row
selected by the target, including the selected motor/eye components.

The demo bound was measured by replaying the canonical `gcs.sql` and
`first_day_gcs.sql` over the read-only source CSVs, then replacing the lost
ETT label with the only served value (Quantity 1):

* 345 ambiguous verbal observations in the target's closed window, across 60
  stays;
* 23/140 source first-day selected rows have `gcs_unable=1`;
* the label-loss counterfactual changed first-day `gcs_min` on 43/140 rows,
  `gcs_verbal` on 41/140, `gcs_motor` on 6/140, and `gcs_eyes` on 12/140;
* `gcs_unable` is absent on 140/140 counterfactual output rows.

This reaches clinically meaningful target outputs and is not a row-local
ancillary gap. Recommend that the equivalence judge consider whole-concept
blocking unless the upstream ETL preserves the discriminator. The prober does
not make the terminal decision. The target must consume the completed `gcs`
view; it must not hide this loss by assigning verbal `1`, guessing ventilation,
or regenerating an Observation UUID.

Other coverage gaps:

1. The chartevents ETL's `value IS NOT NULL` predicate and hard-coded tuple
   omission are absent from the canonical GCS source filter. This demo has
   0/9,791 affected rows. On full data, omitted rows are absent and not
   representable; they can affect dependency grouping/carry-forward and
   first-day row selection, so the full comparator must bound them.
2. ICU `Encounter.period.start` is the served representation of `intime`, but
   the upstream ETL can normalize a spring-forward-gap wall time through
   `TIMESTAMPTZ`. The original wall time is not recoverable by FHIR semantics.
   The demo bound is 0/140 ICU starts (140/140 exact). On affected full-data
   rows the loss reaches only target observations at the closed-window
   boundaries; count those rows before treating it as whole-concept
   essential. Do not use an id side channel to undo it.
3. `Quantity.unit` is absent on 9,791/9,791 GCS rows, but neither the source
   SQL nor the completed `gcs` dependency consumes it. It is an ancillary
   absent field, not a blocker for this target.

## Notes and provisional leads consulted

Read before probing:

* `AGENTS.md`;
* `mimic-iv/concepts_fhir/MIMIC_NOTES.md`;
* `mimic-iv/concepts_fhir/carryover/first_day_gcs/source-analyst.md`;
* `MIMIC_NOTES.d/gcs.md`;
* `MIMIC_NOTES.d/first_day_vitalsign.md`;
* directly relevant `MIMIC_NOTES.d/icustay_detail.md` and
  `MIMIC_NOTES.d/vitalsign.md`;
* canonical `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`;
* `mimic-fhir/sql/fhir_observation_chartevents.sql` and
  `mimic-fhir/sql/fhir_encounter_icu.sql`;
* completed `gcs` attempt_0006 ViewDefinitions, SQL, state, comparison, and
  unrepresentable declaration.

Established `MIMIC_NOTES.md` entries that changed this mapping decision:

* Delta tables, not stale NDJSON or the unauthorized live server, are the
  source of truth.
* ICU Encounters are selected by `identifier.system`; `Encounter.class` does
  not discriminate streams.
* MIMIC identifiers are strings in `identifier.value`; resource/reference keys
  are separate type-prefixed opaque equality keys and must be emitted as
  required companions.
* Observation item codes are verbatim source itemids and discrimination is
  exact `system + code`, never `meta.profile`.
* Choice fields require `ofType()` projections, Quantity aliases need numeric
  casts, and dateTimes must be parsed as `TIMESTAMP_NTZ` wall clocks.
* Resource ids cannot recover omitted values; essential source loss must not
  be concealed with a heuristic or typed ordinary value.

`MIMIC_NOTES.d/gcs.md` was treated as provisional. Its numeric-text-loss and
superseded UUID-recovery leads were independently verified in the fresh Delta
probe: Quantity 1 conflates the two labels, and UUID recovery is forbidden and
not used. `MIMIC_NOTES.d/first_day_vitalsign.md` was also treated as a lead;
its dateTime-only and ETL-omission claims were independently verified here.
The sibling `icustay_detail.md`/`vitalsign.md` leads were checked only for the
ICU identity/time and chartevents-ETL facts relevant here. No other fragment
was used as evidence.

The fresh probe established two dataset-wide facts not yet in curated
`MIMIC_NOTES.md`, so they were appended to the owned provisional fragment
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_gcs.md`: all served chartevents
Observations use dateTime effective, and the chartevents ETL applies its global
NULL-value and hard-coded tuple exclusions. No separate GCS label-loss section
was appended because that is the concept-specific fact already recorded in
the provisional `gcs.md` fragment and covered here as evidence.

No immutable attempt artifact was edited or created.
