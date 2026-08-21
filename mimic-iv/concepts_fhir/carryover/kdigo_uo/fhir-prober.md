# FHIR mapping: `kdigo_uo`

## Scope and authoritative sources

- Concept: `kdigo_uo`; target attempt: `attempt_0001`.
- Source analysis read exactly from
  `mimic-iv/concepts_fhir/carryover/kdigo_uo/source-analyst.md`.
- Canonical source SQL: `mimic-iv/concepts/organfailure/kdigo_uo.sql`.
- The target has two completed dependencies and must consume their published
  output tables named `urine_output` and `weight_durations`. It must not inline
  or rederive either dependency in the target SQL.
- FHIR warehouse probed with embedded Pathling 9.6.0 / Spark 4.0.2 over
  `/Users/nau025/warehouses/mimic-iv-demo/delta`. No HTTP Pathling server or
  stale NDJSON was used.
- Read-only source oracle used for checks:
  `/Users/nau025/warehouses/mimic4-demo.db`.
- Canonical ViewDefinition shape checked at
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Full target manifest entry:
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`, concept
  `kdigo_uo`.

## Source table and dependency to FHIR resource mapping

| Source or dependency | FHIR representation | Use in `kdigo_uo` |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | Provides the ICU stay identifier and `intime` used for the rolling numeric time axis. The target must project its resource key and patient reference as required candidate key columns. |
| `mimiciv_icu.outputevents` (inside completed `urine_output`) | `Observation`, outputevents stream, with ICU `Encounter` reference | The dependency maps the exact output item codes, Quantity value, and effective dateTime into `(stay_id, charttime, urineoutput)`. `kdigo_uo` consumes the dependency output rather than this raw stream. |
| `mimiciv_icu.chartevents` (inside completed `weight_durations`) | `Observation`, ICU chartevents stream, with ICU `Encounter` reference | The dependency maps the exact weight item codes, Quantity value, effective dateTime, and ICU period endpoints into weight intervals. `kdigo_uo` consumes `weight_durations` rather than this raw stream. |
| `mimiciv_derived.urine_output` | Published dependency table `urine_output` (not a FHIR resource) | Required fields: `stay_id`, `charttime`, `urineoutput`, `icu_encounter_key`, `patient_key`. |
| `mimiciv_derived.weight_durations` | Published dependency table `weight_durations` (not a FHIR resource) | Required fields: `stay_id`, `starttime`, `endtime`, `weight`; `weight_type` is present in the dependency but is not consumed by this target. |

The target's natural row grain is one urine-output time per ICU stay,
`(stay_id, charttime)`. The full manifest confirms keyed comparison on that
pair, target row count 3,321,748, and required additive candidate keys
`icu_encounter_key` and `patient_key`.

## Canonical FHIRPath projections

These are mapping projections for the dependency inputs. They are not
ViewDefinitions for this attempt.

### ICU Encounter projection

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "icu_encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "period.start", "name": "intime_datetime" },
        { "path": "period.end", "name": "outtime_datetime" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
      "column": [
        { "path": "system", "name": "stay_system" },
        { "path": "value", "name": "stay_id_str" }
      ]
    }
  ]
}
```

`getResourceKey()` and `getReferenceKey(Patient)` are opaque, type-prefixed
FHIR strings. They are equality/provenance keys only. `stay_id` comes from the
ICU `identifier.value` string and is cast to `INTEGER` in downstream SQL; a
resource UUID must never be parsed or used as `stay_id`.

### Outputevents Observation projection used by `urine_output`

```json
{
  "resource": "Observation",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "observation_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
        { "path": "(value).ofType(Quantity).value", "name": "value_quantity" },
        { "path": "(value).ofType(Quantity).unit", "name": "value_unit" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
        { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
        { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
        { "path": "(effective).ofType(instant)", "name": "effective_instant" }
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items' and (code='226559' or code='226560' or code='226561' or code='226584' or code='226563' or code='226564' or code='226565' or code='226567' or code='226557' or code='226558' or code='227488' or code='227489'))",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "item_system" },
        { "path": "display", "name": "item_display" }
      ]
    }
  ]
}
```

### Chartevents Observation projection used by `weight_durations`

```json
{
  "resource": "Observation",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "observation_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
        { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
        { "path": "(effective).ofType(instant)", "name": "effective_instant" },
        { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
        { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='226512' or code='224639'))",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "item_system" },
        { "path": "display", "name": "item_display" }
      ]
    }
  ]
}
```

## Source column → FHIRPath/dependency mapping and types

The FHIR alias type is the type seen by the ViewDefinition materialisation.
The dependency/output type is the type required after the dependency or target
SQL casts it. A `VARCHAR` FHIR alias is not finished: implementers must cast it
to the manifest type where shown.

| Source column or target input | Canonical mapping `{path, name}` | FHIR type / materialized type | Required dependency or target type/use |
|---|---|---|---|
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` on ICU `Encounter` | `Identifier.value` `string` / `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; never use a resource key. |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` on ICU `Encounter` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)`; it supplies `seconds_since_admit` for all target windows. |
| `icustays.outtime` (needed only inside the completed weight dependency) | `{ "path": "period.end", "name": "outtime_datetime" }` on ICU `Encounter` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(... AS TIMESTAMP_NTZ)` for the dependency's terminal `endtime`; not a direct `kdigo_uo` input. |
| ICU Encounter resource identity | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | resource key `string` / `STRING`, `Encounter/<id>` | Emit verbatim as required candidate key and use only for equality joins. |
| ICU Encounter patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | reference key `string` / `STRING`, `Patient/<id>` | Emit verbatim as required candidate key and use only for equality joins/provenance. |
| `outputevents.stay_id` inside `urine_output` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` joined by equality to ICU Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }`, then `stay_id_str` above | `Reference(Encounter)` key and resource key `string` / `STRING` | Published dependency `urine_output.stay_id INTEGER`; join keys are opaque and are not parsed. |
| `outputevents.charttime` inside `urine_output` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | `CAST/TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` → published `urine_output.charttime TIMESTAMP`. |
| `outputevents.itemid` inside `urine_output` | In constrained coding group: `{ "path": "code", "name": "item_code" }`; `{ "path": "system", "name": "item_system" }`; `{ "path": "display", "name": "item_display" }` | `Coding.code`, `Coding.system`, `Coding.display` strings / `STRING` | `CAST(item_code AS INTEGER)` for the dependency filter and `227488` discriminator. `display` is informational only. |
| `outputevents.value` inside `urine_output` | `{ "path": "(value).ofType(Quantity).value", "name": "value_quantity" }` | FHIR `Quantity.value` decimal / ViewDefinition alias `STRING` (raw value is `decimal(32,6)`) | `CAST(value_quantity AS DOUBLE)`; apply `227488 AND value > 0` → `-value`; group/sum into published `urine_output.urineoutput DOUBLE`. |
| `outputevents.valueuom` (not used by either target SQL) | `{ "path": "(value).ofType(Quantity).unit", "name": "value_unit" }` | FHIR `Quantity.unit` `string` / `STRING` | Not needed; target demo unit was `ml` on 7,349/7,349 output rows. |
| Published `urine_output.stay_id` | Upstream ICU Encounter identifier mapping above | dependency `INTEGER` | Partition, natural key, and equality-equivalent join input. Prefer dependency resource-key equality for dependency joins, while retaining this output identifier. |
| Published `urine_output.charttime` | Upstream output Observation effective dateTime mapping above | dependency `TIMESTAMP` | Target natural key, `LAG` ordering, numeric window ordering, and weight interval lookup. |
| Published `urine_output.urineoutput` | Upstream item coding + Quantity value mappings above | dependency `DOUBLE` | Numerator for all three rolling volume sums and rates. |
| Published `urine_output.icu_encounter_key` | ICU Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque `STRING` | Required target key; equality join to `weight_durations.icu_encounter_key`. |
| Published `urine_output.patient_key` | ICU Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque `STRING` | Required target key; emit verbatim. |
| `chartevents.stay_id` inside `weight_durations` | Observation encounter reference as above, joined to ICU Encounter identifier value | FHIR reference/resource keys `STRING`, identifier `STRING` | Published dependency `weight_durations.stay_id INTEGER`; no UUID parsing. |
| `chartevents.itemid` inside `weight_durations` | In constrained coding group: `{ "path": "code", "name": "item_code" }`; `{ "path": "system", "name": "item_system" }`; `{ "path": "display", "name": "item_display" }` | `Coding.code/system/display` strings / `STRING` | `226512 → 'admit'`, `224639 → 'daily'`; the exact discriminator is retained in dependency logic. |
| `chartevents.charttime` inside `weight_durations` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | Cast to `TIMESTAMP_NTZ` for ordinary interval starts, `ROW_NUMBER`, and `LEAD`. |
| `chartevents.valuenum` inside `weight_durations` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR `Quantity.value` decimal / ViewDefinition alias `STRING` (raw `decimal(32,6)`) | Cast numeric, require `> 0` and `< 1500`, round to 3 → published `weight DECIMAL(38,3)`. |
| `chartevents.valueuom` inside `weight_durations` | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | FHIR string / `STRING` | Not output; `kg` and source unit agreed on 570/570 selected events. |
| ICU period endpoints inside `weight_durations` | `{ "path": "period.start", "name": "intime_datetime" }`; `{ "path": "period.end", "name": "outtime_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | Cast `TIMESTAMP_NTZ`; used for synthetic first interval and terminal `endtime`. |
| Published `weight_durations.starttime` | No single FHIR element: ordinary `effective_datetime`, first-admit `period.start - 2 hours`, then dependency logic | dependency `TIMESTAMP` | Absent as a literal but derivable by the completed dependency's canonical `ROW_NUMBER` and arithmetic. Used in the target half-open interval join. |
| Published `weight_durations.endtime` | No single FHIR element: next derived `starttime`, or `period.end + 2 hours` | dependency `TIMESTAMP` | Absent as a literal but derivable by the completed dependency's `LEAD`/fallback. Used in `[starttime, endtime)`. |
| Published `weight_durations.weight` | Upstream `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | dependency `DECIMAL(38,3)` | Target `weight`; nullable under the target `LEFT JOIN`. |
| Published `weight_durations.weight_type` | Derived from constrained `{ "path": "code", "name": "item_code" }` | dependency `VARCHAR` | `226512`/`224639` makes it derivable, but `kdigo_uo` does not consume it. |
| Target `stay_id` | Published `urine_output.stay_id` (ultimately ICU Encounter `identifier.value`) | target `INTEGER` | Manifest type `INTEGER`; final output natural-key component. |
| Target `charttime` | Published `urine_output.charttime` (ultimately Observation `(effective).ofType(dateTime)`) | target `TIMESTAMP` | Manifest type `TIMESTAMP`; final output natural-key component and window axis. |
| Target `weight` | Published `weight_durations.weight` | target `DECIMAL(38,3)` | Manifest type `DECIMAL(38,3)`; NULL where the half-open weight join has no match. |
| Target `urineoutput_6hr`, `urineoutput_12hr`, `urineoutput_24hr` | No single FHIR path; window `SUM` of published `urine_output.urineoutput` | target `DOUBLE` | Inclusive numeric `RANGE` windows of 21,600/43,200/86,400 seconds. |
| Target `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr` | No single FHIR path; `LAG(charttime)` plus duration `SUM` | target `DECIMAL(38,6)` | Manifest type `DECIMAL(38,6)`; first row per stay contributes the canonical default `1` hour. |
| Target `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr` | No single FHIR path; gated division of rolling volume by `weight` and `uo_tm_*` | target `DECIMAL(38,4)`, nullable | Manifest type `DECIMAL(38,4)`; preserve the canonical duration gates (`6 ≤ tm6 < 12`, `tm12 ≥ 12`, `tm24 ≥ 24`). |
| Required `icu_encounter_key` | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` on ICU `Encounter` | opaque resource key `STRING` | Emit verbatim, including `Encounter/`; required by manifest but not compared to oracle values. |
| Required `patient_key` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` on ICU `Encounter` | opaque reference key `STRING` | Emit verbatim, including `Patient/`; required by manifest but not compared to oracle values. |

## Confirmed coding systems, exact literals, and cardinality

`kdigo_uo.sql` itself has no direct coded filter. Its target candidate must
consume the completed dependency outputs, but the dependency-owned literals
were rechecked against served FHIR and the read-only oracle.

### `urine_output` dependency

- Confirmed system:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`.
- The exact twelve literals are the source SQL literals. Source rows and
  constrained FHIR coding/resource rows were:

| Code | Source rows | FHIR coding rows | FHIR resources | Display |
|---:|---:|---:|---:|---|
| 226559 | 6,685 | 6,685 | 6,685 | Foley |
| 226560 | 496 | 496 | 496 | Void |
| 226561 | 90 | 90 | 90 | Condom Cath |
| 226584 | 0 | 0 | 0 | Ileoconduit |
| 226563 | 0 | 0 | 0 | Suprapubic |
| 226564 | 0 | 0 | 0 | R Nephrostomy |
| 226565 | 0 | 0 | 0 | L Nephrostomy |
| 226567 | 15 | 15 | 15 | Straight Cath |
| 226557 | 0 | 0 | 0 | R Ureteral Stent |
| 226558 | 0 | 0 | 0 | L Ureteral Stent |
| 227488 | 32 | 32 | 32 | GU Irrigant Volume In |
| 227489 | 31 | 31 | 31 | GU Irrigant/Urine Volume Out |
| **total** | **7,349** | **7,349** | **7,349** | |

- A system-constrained `forEach` had 7,349 coding rows over 7,349 distinct
  Observation resource keys: codings per resource **1.000**. The full
  `mimic-d-items` stream had 24,642/24,642, also **1.000**.
- The code system plus exact code is the discriminator. `outputevents` and
  `datetimeevents` share `mimic-d-items`, but `d_items.itemid` is a global
  primary key with one `linksto` per item; all twelve rows are `linksto =
  'outputevents'`, and the demo item sets are disjoint. Do not use
  `meta.profile`.
- The dependency's positive `227488` branch was observed in 32/32 rows and is
  exactly computable from the surviving code and Quantity value.

### `weight_durations` dependency

- Confirmed system:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
- Exact source literals and served counts:

| Code | Source rows (`valuenum IS NOT NULL AND 0 < valuenum < 1500`) | FHIR coding rows | FHIR resources | Display |
|---:|---:|---:|---:|---|
| 226512 | 129 | 129 | 129 | Admission Weight (Kg) |
| 224639 | 441 | 441 | 441 | Daily Weight |
| **total** | **570** | **570** | **570** | |

- The constrained coding projection had 570/570 rows over 570 distinct
  resources: codings per resource **1.000**. The full chartevents coding stream
  had 668,862/668,862, also **1.000**.
- The discriminator is system plus exact code, never `meta.profile`. The
  `d_items` rows are global item identifiers with one `linksto = 'chartevents'`;
  these exact codes therefore identify the dependency's chartevents stream.

### Non-coded direct target filters

There are no direct `kdigo_uo` code literals, no direct system filter, and no
direct source `WHERE` clause. The only target row-preserving source condition
is the inner stay join inside `uo_stg1`; the final weight association is a
left half-open interval join. No target code set should be invented beyond
the dependency literals above.

## Populated-field and key checks

Embedded Pathling/Spark counts on the authoritative demo Delta:

- ICU `Encounter` projection: 140 rows; `icu_encounter_key`, `patient_key`,
  `stay_id_str`, `intime_datetime`, and `outtime_datetime` were each 140/140
  non-null. All 140 resource/reference keys had the type-prefixed `Type/id`
  shape. ICU identifier values were distinct and matched the 140 source ICU
  stays.
- Exact outputevents projection: 7,349 rows/resources. Each of
  `observation_key`, `patient_key`, `encounter_key`, `item_code`,
  `item_system`, `value_quantity`, `value_unit`, and `effective_datetime` was
  7,349/7,349 non-null. Each effective choice alternative was empty:
  `effective_period_start` 0/7,349, `effective_period_end` 0/7,349, and
  `effective_instant` 0/7,349. All three key columns were 7,349/7,349 with
  `Type/id` shape, and the Observation-to-ICU-Encounter equality join matched
  7,349/7,349.
- Exact chartevents projection: 570 rows/resources. Each of
  `observation_key`, `patient_key`, `encounter_key`, `item_code`,
  `item_system`, `quantity_value`, `quantity_unit`, and
  `effective_datetime` was 570/570 non-null. `effective_period_start` and
  `effective_instant` were each 0/570. All three Observation key/reference
  columns were 570/570 with `Type/id` shape, and the Observation-to-ICU-
  Encounter equality join matched 570/570; the joined ICU `stay_id_str`,
  `intime_datetime`, and `outtime_datetime` were each 570/570.
- Quantity aliases are materialised as `STRING`; numeric casts are required.
  DateTime aliases are offset-bearing `STRING`; use `TIMESTAMP_NTZ`, not an
  offset-aware conversion to Spark `TIMESTAMP`.

## Oracle and dependency agreement checks

The read-only DuckDB oracle and the mapped FHIR rows were compared in pandas:

- Outputevents selected event keys `(stay_id, itemid, charttime)` matched
  7,349/7,349; raw Quantity values matched 7,349/7,349. After the dependency's
  `227488` sign rule, grouped `(stay_id, charttime)` keys matched 7,317/7,317
  and grouped urineoutput sums matched 7,317/7,317 exactly.
- Weight selected event keys matched 570/570. The raw FHIR decimal and source
  floating representation need not be bit-identical (231/570 were raw exact),
  but the canonical three-decimal value matched 570/570 after rounding, which
  is the dependency's published `DECIMAL(38,3)` weight input.
- ICU Encounter `stay_id`, `intime`, and `outtime` endpoint tuples matched the
  source ICU stay table 140/140 in the demo.
- Demo source dependency shapes were `urine_output` 7,317 rows at 7,317
  distinct `(stay_id, charttime)` pairs and `weight_durations` 578 rows over
  137 stays. The canonical demo `kdigo_uo` result was 7,317 rows at 7,317
  distinct `(stay_id, charttime)` pairs over 137 stays. The weight interval
  join matched 7,226/7,317 urine rows and left 91 rows without a weight; the
  maximum matching interval multiplicity was 1.
- The manifest target types are: `stay_id INTEGER`, `charttime TIMESTAMP`,
  `weight DECIMAL(38,3)`, three rolling urine volumes `DOUBLE`, three rates
  `DECIMAL(38,4)`, and three durations `DECIMAL(38,6)`. The target must also
  emit verbatim `icu_encounter_key` and `patient_key`.

## Gaps and bounded essentiality

1. **Dependency aggregates are absent as single FHIR elements but derivable.**
   `urineoutput` is reconstructed from exact coding plus Quantity value and
   grouped at `(stay_id, charttime)`, with 7,317/7,317 grouped sums exact in
   the demo. The target rolling volumes, durations, and rates are similarly
   SQL-derived rather than literal FHIR fields. This is not a representation
   gap when the mapped inputs and dependency boundary are preserved.

2. **Weight interval endpoints are absent as single FHIR fields but
   derivable.** `weight_durations.starttime` and `endtime` are produced from
   mapped chartevent effective time, exact item code, ICU period endpoints,
   `ROW_NUMBER`, `LEAD`, and the canonical two-hour fallbacks. The completed
   dependency's demo replay matched its full interval multiset 578/578. The
   target should use the published dependency values and preserve its
   `UNION ALL` multiplicity.

3. **Pre-ETL outputevents charttime is not representable on DST-gap rows.**
   `Observation.effectiveDateTime` contains the upstream normalized value;
   the original nonexistent New York 02:xx wall time is not carried by a FHIR
   element. The dependency's full attempt measured 393 `only_oracle`, 157
   `only_candidate`, and 232 conflicting urine-output groups attributed to
   this transform, with zero replay residuals. This input is essential for
   `kdigo_uo`: it is part of the natural key, `LAG` ordering, all rolling
   window membership, and the weight interval join. The affected count is
   bounded by those dependency comparison counts, not by the whole 3,321,748
   rows. This is the established upstream TIMESTAMPTZ/DST exception; do not
   reconstruct the missing wall time from an opaque Observation id.

4. **Pre-ETL ICU `intime` is not representable on DST-gap rows.**
   `Encounter.period.start` carries the upstream transformed endpoint. The
   completed `weight_durations` full diagnosis measured nine ICU-intime-derived
   residual interval effects. For `kdigo_uo`, `intime` is essential because it
   defines `seconds_since_admit` and therefore the 6/12/24-hour RANGE windows,
   duration gates, and rates. The nine-row dependency bound is evidence of the
   upstream loss, not a target-specific kdigo count; the target full comparison
   must measure propagation. This is also the established DST exception, not a
   reason to parse or regenerate a resource id.

5. **No source event id is needed for the target grain.** Individual output
   Observation ids are opaque and are not a recoverable source identifier, but
   the dependency's code/value/time projection preserves the required grouped
   `(stay_id, charttime)` grain. Do not deduplicate by `Observation.id`; the
   32 duplicate output-event groups in the demo are item-level contributions
   that must be summed.

6. **No direct target information is missing for `weight`.** Quantity values
   have more than the target's required source precision, and three-place
   rounding agreed on every 570 selected demo event. Missing weight rows after
   the left interval join are represented as typed NULLs and do not remove the
   urine row.

The prober does not make the terminal judge decision. The two DST findings are
upstream transform losses already covered by the loop's explicit exception;
the full target run must still report any propagation and the judge must rule.

## Curated notes and provisional fragments read

Curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md` entries that changed this
mapping decision were: Delta rather than NDJSON is authoritative; identifiers
are string `identifier.value` fields rather than resource UUIDs; resource and
reference keys are type-prefixed opaque equality keys; ICU Encounters are
selected by identifier system rather than class; item codes are verbatim and
must use system plus exact code rather than `meta.profile`; repeated coding
groups must be constrained; choice fields need separate `ofType` aliases;
Quantity value aliases materialise as strings; FHIR dateTimes require
`TIMESTAMP_NTZ`; and upstream ICU/Observation times may have irreversible DST
normalization. The essential-loss/opaque-id policy also ruled out any id-based
recovery of discarded wall times.

Provisional fragments read and checked against the authoritative demo where
relevant:

- `MIMIC_NOTES.d/urine_output.md`: outputevents dateTime-only effective choice
  and DST lead; both matched the fresh output projection and the dependency
  full comparison evidence.
- `MIMIC_NOTES.d/first_day_urine_output.md`: dateTime-only outputevents choice
  and DST aggregation lead; the choice matched 7,349/7,349.
- `MIMIC_NOTES.d/first_day_weight.md`: global chartevent omission predicates
  were unexercised for the two target items, and ICU period DST lead; target
  counts matched the fresh probe.
- `MIMIC_NOTES.d/weight_durations.md`: exact chartevent codes, one-coding
  cardinality, Quantity/dateTime materialisation, and ICU endpoint DST lead;
  all relevant claims were checked against the fresh target projection and
  dependency attempt artifacts.
- `MIMIC_NOTES.d/icustay_times.md`: chartevent aggregate DST non-commutation;
  it was treated as a relevant warning, not substituted for the direct ICU
  `period.start` mapping.
- `MIMIC_NOTES.d/README.md`: append-only provisional-fragment protocol.

The completed dependency carryovers and attempts read were:
`carryover/urine_output/fhir-prober.md`,
`concepts/measurement/urine_output/attempt_0003/` (mapping, ViewDefinitions,
SQL, and comparison/judge evidence),
`carryover/weight_durations/fhir-prober.md`, and
`concepts/demographics/weight_durations/attempt_0003/` (mapping,
ViewDefinitions, SQL, and comparison/judge evidence). Their mappings were
verified rather than adopted as unverified facts.

No new dataset-wide quirk was discovered. `MIMIC_NOTES.md` was not edited and
no section was appended to `MIMIC_NOTES.d/kdigo_uo.md`.
