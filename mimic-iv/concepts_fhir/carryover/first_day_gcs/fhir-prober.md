# FHIR probe and mapping: `first_day_gcs`, attempt_0003

**Concept:** `firstday/first_day_gcs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/first_day_gcs/source-analyst.md`  
**Canonical SQL:** `mimic-iv/concepts/firstday/first_day_gcs.sql`  
**Authoritative FHIR warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Probe engine:** embedded Pathling 9.6.0 / Spark 4.0.2  
**Source oracle:** `/Users/nau025/warehouses/mimic-iv-duckdb-demo/icu/*.csv.gz` and read-only `/Users/nau025/warehouses/mimic4-demo.db`

This is a mapping artifact, not a ViewDefinition or a terminal
representability decision. Resource/reference keys were used only for equality
joins and grouping. No resource id was parsed, regenerated, hashed, guessed,
hardcoded, or used to infer a source value.

## Reopened instruction applied

The implementer must receive this instruction verbatim:

```text
      REOPENED (x1) -- this is the instruction set for this attempt,
      not background. The previous run's SQL was defective:

          Dependency gcs was re-implemented against upstream e7c326b (#125): itemid
          223900   now distinguishes 'No Response' from 'No Response-ETT' via
          Observation.component[].valueString,   and gcs attempt_0008 is COMPLETED
          with no divergence. The dependency gap this port's   accepted divergence
          rests on no longer exists. Drop the ambiguity-propagation logic that
          emitted NULL for gcs_min and the components on the 28,837 affected first-day
          windows, and   remove the gcs_unable unrepresentability declaration. Do not
          reconstruct any resource id.
```

The current Delta probe confirms the premise. Item `223900` has a component
text on 3,266/3,266 verbal Observations, including distinct `No Response` and
`No Response-ETT` values despite both having Quantity 1. The completed `gcs`
attempt_0008 full comparison independently reproduced 1,637,763/1,637,763
oracle rows with zero differing, missing, or extra rows. The previous
`gcs_unable` declaration and ambiguity-propagation logic must not be carried
forward.

## Resource/interface mapping

| Source/interface | FHIR resource or interface | Role |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | One output row per ICU stay; supplies `stay_id` and `intime` |
| `icustays.subject_id` | ICU `Encounter.subject` equality join to `Patient`, then Patient identifier | Supplies final numeric `subject_id`; do not obtain it from a resource key |
| `icustays.stay_id` | ICU `Encounter.identifier` with the ICU identifier system | Supplies final numeric `stay_id` and the natural key |
| `icustays.intime` | ICU `Encounter.period.start` | Inclusive target window anchor |
| completed `mimiciv_derived.gcs` | Published dependency interface `gcs` | Supplies `charttime`, `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs_unable`; consume `FROM gcs` |
| dependency `mimiciv_icu.chartevents` | ICU chartevents `Observation` | Upstream provenance owned by `gcs`; `first_day_gcs` must not rederive it |

The consumer joins `gcs.icu_encounter_key` to the ICU Encounter's
`getResourceKey()` output. Do not join the published dependency by its integer
`stay_id` or by parsing an id. Keep both joins and the final outer join as
`LEFT JOIN`s so stays with no qualifying GCS row survive.

## ViewDefinition-ready projections

### Patient support view

```json
{
  "resource": "Patient",
  "select": [{
    "column": [
      {"path": "getResourceKey()", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
    ]
  }]
}
```

### ICU Encounter support view

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

Filter the Encounter stream by the ICU identifier system, never by
`Encounter.class`. The unfiltered Delta has 637 Encounters (hospital, ICU,
and ED); the ICU identifier group materializes exactly 140 rows in the demo.

### Upstream GCS Observation view

The item coding restriction must be inside `forEach`. The component restriction
must select only the component coded as verbal item `223900`; it is a nullable
repeat for the 9,791-row three-code projection and is populated on the 3,266
verbal rows.

```json
{
  "resource": "Observation",
  "select": [
    {"column": [
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key"},
      {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
      {"path": "(value).ofType(Quantity).value", "name": "quantity_value"}
    ]},
    {"forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='223900' or code='223901' or code='220739'))",
     "column": [
       {"path": "code", "name": "item_code"},
       {"path": "system", "name": "item_system"},
       {"path": "display", "name": "item_display"}
     ]},
    {"forEachOrNull": "component.where(code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code.coding.code='223900')",
     "column": [
       {"path": "code.coding.code", "name": "component_code"},
       {"path": "code.coding.system", "name": "component_system"},
       {"path": "code.coding.display", "name": "component_display"},
       {"path": "value.ofType(string)", "name": "component_text"}
     ]}
  ]
}
```

The underlying served field is `Observation.component[].valueString`; the
canonical ViewDefinition choice projection is `value.ofType(string)`. Do not
use top-level `(value).ofType(string)` for this branch.

## Source-column to FHIRPath mapping and types

ViewDefinition aliases for identifiers, references, dateTimes, Quantity values,
and component text are materialized as Spark `STRING` unless stated otherwise.
The implementer must cast identifier strings to `INTEGER`, effective time to
`TIMESTAMP_NTZ`, Quantity values to the manifest's numeric type, and preserve
resource keys as opaque `STRING` values with their type prefix.

| Source column / dependency field | Canonical `{path, name}` | FHIR type / served alias | Required target/use type |
|---|---|---|---|
| `icustays.subject_id` | Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, then Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key plus `Identifier.value` string | Equality join on `patient_key`; `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; emit `patient_key` |
| `icustays.stay_id` | Encounter `{ "path": "value", "name": "stay_id_str" }` inside the ICU `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')` group | `Identifier.value` string | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; natural key; emit `icu_encounter_key` |
| ICU Encounter identity | Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Opaque type-prefixed resource key `STRING` | Equality join to `gcs.icu_encounter_key`; required key companion; never parse or substitute for `stay_id` |
| Patient identity | Patient `{ "path": "getResourceKey()", "name": "patient_key" }` | Opaque type-prefixed resource key `STRING` | Equality join/provenance and required key companion; never parse or substitute for `subject_id` |
| `icustays.intime` | Encounter `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`, offset-bearing `STRING` alias | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)`; inclusive `-6 hour` / `+1 day` window |
| `chartevents.subject_id` (dependency provenance) | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` key `STRING` | Preserve for dependency key/provenance; not consumed as an integer by this consumer |
| `chartevents.stay_id` (dependency provenance) | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` | `Reference(Encounter)` key `STRING` | Published `gcs` equality join key; recover numeric `stay_id` only from ICU Encounter identifier |
| `chartevents.charttime` / `gcs.charttime` | Observation `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`; alias `STRING` | Direct `TRY_CAST(... AS TIMESTAMP_NTZ)` → dependency `charttime TIMESTAMP`; window, ordering, and tie-break |
| `chartevents.itemid` | Coding `{ "path": "code", "name": "item_code" }` inside the exact system/code `forEach` | `Coding.code` `STRING` | Exact string filter first; code values are `223900`, `223901`, `220739` |
| chartevents coding system | Coding `{ "path": "system", "name": "item_system" }` | `Coding.system` `STRING` | Exact discriminator URI; never `meta.profile` |
| `d_items.label` | Coding `{ "path": "display", "name": "item_display" }` | `Coding.display` `STRING` | Ancillary display only; not a filter or source identity |
| `chartevents.valuenum` | Observation `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR `Quantity.value` decimal; alias `STRING` | Cast to `DOUBLE`/dependency numeric type; feeds motor, verbal, eyes, and total |
| `chartevents.valueuom` | Observation `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` `STRING` | Not consumed; absent on all 9,791 demo rows and source `valueuom` is also NULL on all 9,791 |
| `chartevents.value` for item `223900` | Component `{ "path": "value.ofType(string)", "name": "component_text" }` inside `forEachOrNull` over the exact component coding | `Observation.component[].valueString` `STRING` | Exact `No Response-ETT` discriminator; `gcs_verbal = 0`, `gcs_unable = 1`, and total `gcs = 15` in that branch |
| component coding | `{ "path": "code.coding.code", "name": "component_code" }`, `{ "path": "code.coding.system", "name": "component_system" }`, `{ "path": "code.coding.display", "name": "component_display" }` inside the component group | `Coding.code/system/display` `STRING` | Confirm component belongs to item `223900`; all three match the parent coding on the 3,266 verbal rows |
| published `gcs.stay_id` | No new FHIR path at the consumer; join `gcs.icu_encounter_key` to Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Derived dependency integer plus opaque key | Use the opaque key join, not the dependency integer, for the published interface |
| published `gcs.charttime` | Upstream Observation `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | Derived dependency `TIMESTAMP` | Window and `ORDER BY gcs.charttime DESC`; no id recovery |
| published `gcs.gcs` | No direct FHIR element; completed dependency calculation over Quantity and component text | Nullable dependency `FLOAT` | Selected by target `ROW_NUMBER()` and output as `gcs_min FLOAT` |
| published `gcs.gcs_motor` | No direct FHIR element; dependency pivot from item `223901` Quantity | Nullable dependency `FLOAT` | Selected coherent component row; output `gcs_motor FLOAT` |
| published `gcs.gcs_verbal` | No direct FHIR element; dependency pivot from item `223900` Quantity/component text | Nullable dependency `FLOAT` | Exact ETT branch now available; output `gcs_verbal FLOAT` |
| published `gcs.gcs_eyes` | No direct FHIR element; dependency pivot from item `220739` Quantity | Nullable dependency `FLOAT` | Selected coherent component row; output `gcs_eyes FLOAT` |
| published `gcs.gcs_unable` | No direct FHIR element; dependency derives exact ETT flag from component text | Nullable dependency `INTEGER` | Output `gcs_unable INTEGER`; no unrepresentability declaration |

The dependency's `subject_id` is not read by `first_day_gcs`; the outer target
gets `subject_id` from the ICU Encounter → Patient identifier spine.

## Final output mapping and target types

The manifest comparison key is `stay_id`; the output is one row per ICU stay.
The two opaque key companions are required by the FHIR port even though they
are not source-oracle columns.

| Output column | Canonical mapping/provenance | Required type |
|---|---|---|
| `subject_id` | Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` through ICU Encounter `patient_key` | `INTEGER` after cast |
| `stay_id` | ICU Encounter `{ "path": "value", "name": "stay_id_str" }` in the ICU identifier group | `INTEGER` after cast; natural key |
| `gcs_min` | `gcs.gcs`, selected by `ROW_NUMBER() OVER (PARTITION BY stay_id ORDER BY gcs ASC NULLS LAST, charttime DESC NULLS LAST)` | `FLOAT` |
| `gcs_motor` | `gcs.gcs_motor` on the selected dependency row | `FLOAT` |
| `gcs_verbal` | `gcs.gcs_verbal` on the selected dependency row | `FLOAT` |
| `gcs_eyes` | `gcs.gcs_eyes` on the selected dependency row | `FLOAT` |
| `gcs_unable` | `gcs.gcs_unable` on the selected dependency row | `INTEGER` |
| required `patient_key` | Patient `{ "path": "getResourceKey()", "name": "patient_key" }` | Opaque `STRING`, prefix intact |
| required `icu_encounter_key` | Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Opaque `STRING`, prefix intact |

The source window remains inclusive from `intime - 6 hours` through `intime + 1
day`. The target retains every ICU stay and chooses the lowest total GCS,
breaking equal totals by latest `charttime`.

## Confirmed code set, systems, cardinalities, and NULL counts

The served target projection contained exactly one coding per Observation and
one system for the target stream:

| Source itemid | FHIR code/display | System | coding rows | distinct resources | ratio |
|---:|---|---|---:|---:|---:|
| 220739 | `"220739"` / `GCS - Eye Opening` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | 3,274 | 3,274 | 1.000 |
| 223900 | `"223900"` / `GCS - Verbal Response` | same | 3,266 | 3,266 | 1.000 |
| 223901 | `"223901"` / `GCS - Motor Response` | same | 3,251 | 3,251 | 1.000 |
| **target total** | — | same | **9,791** | **9,791** | **1.000** |

The complete chartevents-system probe was also 668,862 coding rows over
668,862 distinct resources (ratio 1.000). The exact pair `system + code` is
the discriminator. It is not `meta.profile`; merged warehouse preparation can
collapse subtype profiles. GCS uses the chartevents-specific system, not the
shared `mimic-d-items` system used by outputevents/datetimeevents. In the
shared-system case, exact code remains valid only because `d_items.itemid` is a
global primary key with one `linksto` value per item; that warrant is not needed
for this GCS system.

For the 9,791-row Observation projection, rows/non-null were:

| Alias / path | Rows | Non-null |
|---|---:|---:|
| `patient_key` / `subject.getReferenceKey(Patient)` | 9,791 | 9,791 |
| `icu_encounter_key` / `encounter.getReferenceKey(Encounter)` | 9,791 | 9,791 |
| `effective_datetime` / `(effective).ofType(dateTime)` | 9,791 | 9,791 |
| `effective_period_start` / `(effective).ofType(Period).start` | 9,791 | 0 |
| `effective_period_end` / `(effective).ofType(Period).end` | 9,791 | 0 |
| `effective_instant` / `(effective).ofType(instant)` | 9,791 | 0 |
| `quantity_value` / `(value).ofType(Quantity).value` | 9,791 | 9,791 |
| `quantity_unit` / `(value).ofType(Quantity).unit` | 9,791 | 0 |
| top-level `value_string` / `(value).ofType(string)` | 9,791 | 0 |
| `item_code`, `item_system`, `item_display` | 9,791 each | 9,791 each |
| verbal component code/system/display/text | 9,791-row view; component-bearing rows only | 3,266 each |

Support-view counts were ICU Encounter 140 rows with all five projected fields
non-null, and Patient 100 rows with both `patient_key` and `subject_id_str`
non-null. The read-only DuckDB source had 140/140 non-null
`icustays.subject_id`, `stay_id`, and `intime`.

The demo source dependency counts were 3,279 rows total, with
`charttime=3,279`, `gcs=3,279`, `gcs_motor=3,275`, `gcs_verbal=3,278`,
`gcs_eyes=3,278`, `gcs_unable=3,279`, and `stay_id=3,279` non-null. The demo
`first_day_gcs` oracle had 140 rows and all seven source output columns were
140/140 non-null. Full dependency attempt_0008 is the stronger confirmation:
all 1,637,763 source `gcs` rows reproduced exactly.

## Source-oracle agreement

The fresh Delta/FHIR and DuckDB source join used only the opaque Patient and
Encounter keys for equality, then compared source identifiers and values:

| Check | Exact agreement |
|---|---:|
| Source/FHIR GCS rows | 9,791/9,791; source-only 0; FHIR-only 0 |
| Key `(subject_id, stay_id, charttime, itemid)` multiplicity | 9,791/9,791; duplicate count 0 on both sides |
| `subject_id` | 9,791/9,791 |
| `stay_id` | 9,791/9,791 |
| `charttime` after direct `TIMESTAMP_NTZ` wall-clock cast | 9,791/9,791 |
| Quantity numeric value vs source `valuenum` | 9,791/9,791 |
| component text vs source `value` (223900 rows) | 3,266/3,266 |
| item display vs `d_items.label` | 9,791/9,791 |
| ICU Encounter `(subject_id, stay_id, intime)` spine | 140/140 |

The component text distribution for `223900` was `No Response-ETT` 1,348,
`No Response` 78, `Oriented` 1,319, `Confused` 403, `Inappropriate Words`
39, and `Incomprehensible sounds` 79. The Quantity-1 heuristic is obsolete;
the component discriminator is exact.

## Gaps and representability status

1. **Former essential GCS label loss: resolved.** The exact source
   `No Response-ETT` discriminator is now present at
   `Observation.component[].valueString` for item `223900`. `gcs`,
   `gcs_verbal`, `gcs_unable`, total GCS, and six-hour carry-forward are
   therefore fully representable by the completed dependency. Do not emit
   ambiguity NULLs and do not declare `gcs_unable` unrepresentable.
2. **Dependency full result: fully representable.** `gcs` attempt_0008 has
   `match`, 1,637,763/1,637,763 identical rows, zero conflicts, zero
   `only_oracle`, zero `only_candidate`, and no declared unrepresentable
   columns. This removes the prior whole-concept gap on which the earlier
   `first_day_gcs` accepted divergence rested.
3. **Global chartevents ETL omissions:** the ETL's global `value IS NOT NULL`
   and hard-coded tuple exclusion are absent from canonical `gcs.sql`. In this
   demo, source GCS rows had `value` non-null on 9,791/9,791 and the excluded
   tuple had zero rows. The completed full `gcs` match bounds this omission at
   zero rows for the dependency's full comparison; no current GCS gap remains.
4. **Quantity unit:** absent on 9,791/9,791, but source `valueuom` is also
   NULL on 9,791/9,791 and neither `gcs` nor `first_day_gcs` consumes it. This
   is absent-but-irrelevant, not essential and not a reason to block.
5. **Resource identity:** `Observation.getResourceKey()` is opaque identity
   only. It cannot recover any source text, timestamp, or identifier and must
   not be used as an inversion or side channel.

No present gap changes row inclusion, natural key, grouping, temporal
carry-forward, or a clinically meaningful output for this reopened mapping.
The implementer still needs to run the target concept's normal demo/full gates;
this prober does not make a terminal equivalence decision.

## Notes read and fragment handling

`MIMIC_NOTES.md` was read in full before probing. Its mapping decisions that
changed this mapping were: the 2026-08-21 `e7c326b` component repair; exact
itemid/system discrimination rather than `meta.profile`; identifier values as
strings separate from required opaque resource/reference keys; ICU Encounter
stream selection by identifier system rather than class; `ofType()` choice
projection; direct `TIMESTAMP_NTZ` parsing of FHIR wall-clock strings; and the
opaque-id/essential-loss policy. The historical GCS label-loss entry is not
applicable to this rebuilt warehouse.

All files returned by the `MIMIC_NOTES.d/*.md` glob were read, including the
README: `first_day_weight.md`, `dobutamine.md`, `crrt.md`, `charlson.md`,
`oxygen_delivery.md`, `apsiii.md`, `kdigo_stages.md`, `icp.md`,
`norepinephrine_equivalent_dose.md`, `complete_blood_count.md`, `age.md`,
`vasoactive_agent.md`, `coagulation.md`, `norepinephrine.md`, `kdigo_uo.md`,
`neuroblock.md`, `height.md`, `vitalsign.md`, `first_day_vitalsign.md`, `README.md`, `gcs.md`,
`first_day_gcs.md`, `ventilator_setting.md`, `ventilation.md`,
`icustay_hourly.md`, `vasopressin.md`,
`first_day_urine_output.md`, `cardiac_marker.md`, `kdigo_creatinine.md`,
`creatinine_baseline.md`, `blood_differential.md`, `lods.md`,
`weight_durations.md`, `dopamine.md`, `code_status.md`,
`suspicion_of_infection.md`, `chemistry.md`, `urine_output.md`,
`invasive_line.md`, `phenylephrine.md`, `milrinone.md`, `epinephrine.md`,
`rhythm.md`, `icustay_detail.md`, `icustay_times.md`, `first_day_bg.md`,
`arb.md`, and `rrt.md`. Every fragment was treated as provisional. The
directly relevant leads in `gcs.md`, `first_day_gcs.md`,
`first_day_vitalsign.md`, `icustay_detail.md`, `vitalsign.md`, `lods.md`,
`ventilation.md`, `ventilator_setting.md`, `height.md`, `coagulation.md`,
`chemistry.md`, `crrt.md`, `code_status.md`, `cardiac_marker.md`, `icp.md`,
`oxygen_delivery.md`, `first_day_weight.md`, `first_day_urine_output.md`,
`urine_output.md`, `icustay_times.md`, and `weight_durations.md` were checked
against the current served data or the authoritative ETL where relevant.
Historical UUID-recovery claims were explicitly rejected. Unrelated fragments
were read but did not alter this mapping and were not cited as evidence.

One new dataset/IG-wide finding was appended, and only to this goal's fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_gcs.md` now records the
verified component text behavior for numeric chartevents item `223900`.

## Carryover artifact

This file is the mutable reusable mapping for retries:

`mimic-iv/concepts_fhir/carryover/first_day_gcs/fhir-prober.md`

No ViewDefinition, `concept.sql`, immutable attempt artifact, or prior evidence
file was written or edited by this stage.
