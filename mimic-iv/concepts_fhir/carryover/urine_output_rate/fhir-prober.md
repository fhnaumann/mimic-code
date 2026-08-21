# FHIR mapping: `urine_output_rate` (attempt 0001)

## Scope and authoritative sources

- Source analysis read from `mimic-iv/concepts_fhir/carryover/urine_output_rate/source-analyst.md`.
- Canonical SQL: `mimic-iv/concepts/measurement/urine_output_rate.sql`.
- The source analysis and `LOOP_CONTRACT.md` identify completed dependencies
  `urine_output` and `weight_durations`. This mapping does not rederive either
  dependency or repeat its item filters/value transformations.
- Authoritative FHIR data: `/Users/nau025/warehouses/mimic-iv-demo/delta`,
  queried with embedded Pathling 9.6.0 / Spark 4.0.2. No HTTP Pathling server
  or stale NDJSON was used.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db`
  (DuckDB 1.5.5).
- Canonical ViewDefinition structure checked at
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- ETL checked at
  `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:8-9,20-23,34-38,58-80`
  and
  `/Users/nau025/Documents/mimic-fhir/sql/fhir_encounter_icu.sql:30-32,44-46,77-100`.

## Source table/relation to FHIR mapping

| Source relation | FHIR resource or published dependency | Role in this concept |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | Stay identifier, ICU period endpoints, patient reference, and required ICU Encounter key. |
| `mimiciv_icu.chartevents` | `Observation`, ICU chartevents stream | Exact item `220045`, effective chart time, and opaque ICU Encounter reference. No charted numeric value is read by the source SQL. |
| `mimiciv_derived.urine_output` | Published dependency view `urine_output` | Consume its already-derived `charttime`, `urineoutput`, and resource-key columns. Do not read outputevents FHIR resources here. |
| `mimiciv_derived.weight_durations` | Published dependency view `weight_durations` | Consume its already-derived `starttime`, `endtime`, `weight`, and resource-key columns. Do not rebuild weight intervals here. |

`Encounter.class` is not a stream discriminator. The ICU identifier system is
the discriminator. No Patient ViewDefinition is needed solely for this target:
the ICU Encounter already carries `subject.getReferenceKey(Patient)`, which is
the required `patient_key` output.

## Canonical ViewDefinition projections

These are reusable mapping projections, not attempt implementation artifacts.
The labels/names below are illustrative target-local labels; the
`select[].column[].{path,name}` forms are load-bearing.

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

The filtered `forEach` is preferable to `forEachOrNull` here: each ICU
Encounter has one ICU identifier and the filtered projection materialized 140
rows. A flat equivalent, also verified, is
`identifier.where(system='.../encounter-icu').value` named `stay_id_str` on an
unfiltered Encounter view, followed by `stay_id_str IS NOT NULL`.

### Chartevents Observation projection

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
        { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
        { "path": "(effective).ofType(instant)", "name": "effective_instant" }
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code='220045')",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "item_system" },
        { "path": "display", "name": "item_display" }
      ]
    }
  ]
}
```

The target stream is dateTime-only in the authoritative Delta, so
`effective_datetime` is the operative path. The Period and instant aliases
were probed to make the choice-type behavior explicit; all are empty for the
target. If the implementer omits those diagnostic aliases, it must not replace
the dateTime path with a Period or instant path.

## Source column to FHIRPath mapping and types

FHIR identifier values, coding fields, dateTime aliases, and resource/reference
keys materialize as Spark `STRING`/`VARCHAR` in these ViewDefinitions. They are
not the final oracle types until the target SQL casts them.

| Source column/input | Canonical mapping `{path, name}` | FHIR type / materialized type | Required target type or use |
|---|---|---|---|
| `icustays.stay_id` (`INTEGER`) | `{ "path": "value", "name": "stay_id_str" }` inside the ICU-filtered `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')` group | `Identifier.value` `string` / `STRING` | `CAST(stay_id_str AS INTEGER)` gives target `stay_id`; never use an Encounter UUID. |
| `icustays.intime` (`TIMESTAMP`) | `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)` before one-month arithmetic and comparisons. |
| `icustays.outtime` (`TIMESTAMP`) | `{ "path": "period.end", "name": "outtime_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(outtime_datetime AS TIMESTAMP_NTZ)` before one-month arithmetic and comparisons. |
| ICU Encounter resource identity | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque type-prefixed resource key `string` / `STRING` | Emit verbatim as required candidate key; equality joins only. |
| ICU Encounter patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque `Reference(Patient)` key `string` / `STRING` | Emit verbatim as required candidate key; equality joins/provenance only. |
| `chartevents.stay_id` (`INTEGER`) | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` on Observation, joined to `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` on ICU Encounter | `Reference(Encounter)` key / resource key, both `STRING` | Equality join to the ICU Encounter. Recover the numeric stay only from `stay_id_str`; do not parse either key. |
| `chartevents.charttime` (`TIMESTAMP`) | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` gives the chart-time axis for `MIN`, `MAX`, window predicates, and elapsed-time calculations. |
| Empty effective Period alternative | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }`; `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | FHIR `Period.start/end` / `STRING` | 0/13,913 on the exact target; do not use as a fallback for this stream. |
| Empty effective instant alternative | `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | FHIR `instant` / native Spark `TIMESTAMP` | 0/13,913 on the exact target; no coalesce is needed. |
| `chartevents.itemid` (`INTEGER`) | Within the constrained coding group: `{ "path": "code", "name": "item_code" }`, `{ "path": "system", "name": "item_system" }`, `{ "path": "display", "name": "item_display" }` | `Coding.code` `string`, `Coding.system` `uri`, `Coding.display` `string`; all materialize as `STRING` | Keep system + exact code `220045` as the discriminator. `CAST(item_code AS INTEGER)` is optional because the target can compare the string literal. Display is informational. |
| Observation resource identity | `{ "path": "getResourceKey()", "name": "observation_key" }` | opaque type-prefixed resource key `string` / `STRING` | Provenance/deduplication of one FHIR resource only. It is not a source event id and is not used in the target output or to recover charttime. |

The direct source SQL does not read `chartevents.value`, `valuenum`,
`valueuom`, `storetime`, `subject_id`, or an Observation value. Do not add a
value mapping or use a missing value as a row filter. The global chartevents
ETL does require `value IS NOT NULL`; this exact target had 13,913/13,913
non-null source values, so that ETL omission was not exercised in the demo.

## Dependency boundary and joins

The completed dependency views are consumed under the unqualified names
`urine_output` and `weight_durations`. Their published FHIR shape includes the
paired opaque key columns and the dependency values. In particular, the
dependency export strips an identifier when its paired resource key is also
projected; therefore a dependent implementation must not assume that a
published dependency can be joined on `stay_id`.

Use these equality joins:

```text
ICU Encounter e.icu_encounter_key = Observation c.encounter_key
ICU Encounter e.icu_encounter_key = urine_output.icu_encounter_key
ICU Encounter e.icu_encounter_key = weight_durations.icu_encounter_key
```

The source-semantic joins on `stay_id` are preserved by this key equality; the
target's output `stay_id` comes from `CAST(e.stay_id_str AS INTEGER)`. Carry
`e.icu_encounter_key` and `e.patient_key` through the `tm`, `uo_tm`, and
`ur_stg` groups and emit them at the outermost select. Never regenerate or
parse a key, and do not rederive `urine_output` or `weight_durations` from
Observation resources.

Dependency input types to expect:

| Published dependency field | Type | Use |
|---|---|---|
| `urine_output.charttime` | `TIMESTAMP` | LAG ordering, 23-hour self-join, elapsed-time windows, output key. |
| `urine_output.urineoutput` | `DOUBLE` | Current and rolling volume numerators. |
| `urine_output.icu_encounter_key`, `patient_key` | opaque `STRING` | Equality join and required output keys. |
| `weight_durations.starttime`, `endtime` | `TIMESTAMP` | Strict/inclusive weight interval join. |
| `weight_durations.weight` | `DECIMAL(38,3)` | Positive-weight predicate, output weight, rate denominator. |
| `weight_durations.icu_encounter_key`, `patient_key` | opaque `STRING` | Equality join and required output keys. |

Preserve the source's strict/inclusive interval predicates (`charttime >
starttime` and `charttime <= endtime`), the left join to weight intervals, the
23-hour self-join, `SUM(DISTINCT io.urineoutput)`, and all source rounding and
NULL branches. The direct FHIR mappings only supply the heart-rate-qualified
stay gate; all urine and weight transformations remain dependency-owned.

## Confirmed coding discriminator and counts

The unfiltered `forEach: "code.coding"` probe over the authoritative Delta
showed these relevant stream counts:

- `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`:
  668,862 coding rows / 668,862 distinct Observation resources = **1.000
  codings per resource**.
- The exact constrained target `220045`: 13,913 coding rows / 13,913
  distinct Observation resources = **1.000**.
- The exact constrained projection materialized 13,913 rows; `item_display`
  was `Heart Rate` on 13,913/13,913 rows.

The source oracle had one literal code:

| Source literal | FHIR system | Source rows | FHIR coding rows/resources | Display |
|---:|---|---:|---:|---|
| `220045` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | 13,913 | 13,913 / 13,913 | Heart Rate |

The source dimension confirmed `d_items.itemid=220045` has `linksto='chartevents'`.
The discriminator is **system plus exact code**, never `meta.profile`.
`d_items.itemid` is a global primary key with one `linksto` value, so this
code identifies the chartevents stream; do not infer the stream from a
profile. The other `mimic-d-items` streams are relevant to the completed
`urine_output` dependency, not to this direct filter.

## Populated-field probe counts

The exact code-constrained Observation ViewDefinition had 13,913 total rows:

| Alias | Non-null | FHIR/materialized type |
|---|---:|---|
| `observation_key` | 13,913/13,913 | opaque resource key / `STRING` |
| `patient_key` | 13,913/13,913 | opaque Patient reference key / `STRING` |
| `encounter_key` | 13,913/13,913 | opaque Encounter reference key / `STRING` |
| `item_code` | 13,913/13,913 | `Coding.code` / `STRING` |
| `item_system` | 13,913/13,913 | `Coding.system` / `STRING` |
| `item_display` | 13,913/13,913 | `Coding.display` / `STRING` |
| `effective_datetime` | 13,913/13,913 | FHIR `dateTime` / offset-bearing `STRING` |
| `effective_period_start` | 0/13,913 | `Period.start` / `STRING` |
| `effective_period_end` | 0/13,913 | `Period.end` / `STRING` |
| `effective_instant` | 0/13,913 | FHIR `instant` / native Spark `TIMESTAMP` |

The filtered ICU Encounter ViewDefinition had 140 total rows, all non-null
for `icu_encounter_key`, `patient_key`, `stay_system`, `stay_id_str`,
`intime_datetime`, and `outtime_datetime` (140/140 each). Key-shape probes
found `Observation/...` for 13,913/13,913 Observation keys,
`Encounter/...` for 13,913/13,913 Observation encounter references and
140/140 ICU Encounter keys, and `Patient/...` for 13,913/13,913 Observation
patient references and 140/140 Encounter patient references.

The opaque equality join from the exact Observation projection to the ICU
Encounter projection resolved 13,913/13,913 rows. It is an identity join only;
no resource id was parsed or regenerated.

## Oracle agreement checks

The cheap source/FHIR comparison pulled both sides into pandas after the
wall-clock-preserving `TIMESTAMP_NTZ` cast:

- ICU Encounter source table: 140 rows. `stay_id`, `intime`, and `outtime`
  agreed **140/140** with the identifier and period projections.
- Chartevents item `220045`: source 13,913 rows and FHIR 13,913 resources.
  All 13,913 FHIR rows resolved to a source `stay_id`; code/system/display
  counts agreed 13,913/13,913.
- Effective-time tuple comparison found 13,911 exact source/FHIR multiset
  matches. There were 2 source-only wall-time rows and 2 extra candidate
  multiplicities at the shifted FHIR wall time; these are the two known
  spring-forward collisions, not a wrong code or reference join. The FHIR
  projection had 13,911 distinct `(stay_id, effective_datetime)` keys versus
  13,913 source keys.

## Gaps and representability

1. **Pre-ETL chartevents wall `charttime`: not representable on the affected
   DST-gap rows.** The ETL casts `charttime` through `TIMESTAMPTZ` before
   writing `Observation.effectiveDateTime` (`fhir_observation_chartevents.sql:9,67`).
   In the demo, 2 of 13,913 selected source rows were irreversibly normalized
   from 02:00 to 03:00; the two affected stays had 330 source
   `urine_output_rate` rows in total (145 and 185). The source timestamp is an
   output key, the `MIN`/`MAX` heart-rate anchor, and a boundary for inclusion
   and elapsed-time/rate calculations, so this can propagate to clinically
   meaningful output values. The surviving system/code and Encounter reference
   identify the affected stream/stay, but not which original wall time was
   discarded. A typed NULL is not an adequate whole-column answer, and no
   approximation or resource-id inversion is permitted. This is the known
   upstream TIMESTAMPTZ/DST transformation covered by the loop contract; the
   full target comparison/equivalence judge must bound and rule on its
   propagation. Never parse or regenerate `Observation.id` to repair it.

2. **Pre-ETL ICU `intime`/`outtime`: not representable on any future DST-gap
   endpoint rows.** The served `Encounter.period.start/end` carry the ETL's
   transformed values, not the discarded source wall value. The demo bound was
   0/140 changed ICU endpoints and direct endpoint agreement was 140/140. The
   source endpoints are still essential to the strict one-month heart-rate
   gate, so any full-data affected rows must be reported through the normal
   comparator/judge path; no id-based recovery is allowed. The provisional
   `weight_durations` fragment's 9-row full dependency finding was read as
   context, not reused as a target-specific count.

3. **No direct target gap for identifiers, code, references, or effective
   choice.** `stay_id`, ICU period endpoints on the demo, item `220045`, the
   Observation Encounter reference, and the required opaque keys all had
   direct projections. `Observation.id` is not a source column and is not
   needed at the `(stay_id, charttime)` grain. The completed dependency
   divergences remain inherited dependency behavior and must not be repaired
   by rederiving either dependency in this concept.

## Notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping were: Delta rather
than stale NDJSON is authoritative; MIMIC identifiers are string
`identifier.value` values rather than resource UUIDs; resource/reference keys
are type-prefixed opaque equality keys; ICU Encounter streams are selected by
identifier system rather than `class`; Observation item codes are verbatim and
must use system plus exact code rather than `meta.profile`; dateTime aliases
must be cast to `TIMESTAMP_NTZ`; and the chartevents/ICU Encounter ETL can
irreversibly normalize DST-gap wall times. The notes' essential-loss rule
also prohibited publishing an estimate or recovering the discarded timestamp
through an id.

Read as provisional leads:

- `MIMIC_NOTES.d/urine_output.md`: outputevents dateTime-only effective timing
  and outputevents DST normalization. These concern the completed dependency;
  they were not rederived here. The dependency boundary was preserved.
- `MIMIC_NOTES.d/first_day_urine_output.md`: the same outputevents
  dateTime/DST lead; read as context only and not independently rerun for this
  target.
- `MIMIC_NOTES.d/weight_durations.md`: global chartevents omission predicates
  and ICU Encounter endpoint DST lead. The exact target's source oracle had
  13,913/13,913 non-NULL item-220045 values and no hard-coded omitted tuple;
  the direct ICU endpoint probe was 140/140 exact in the demo. The earlier
  dependency full-run count was not substituted for a target count.

No new dataset-wide quirk was discovered: every quirk found in this probe is
already covered by `MIMIC_NOTES.md`. Consequently
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/urine_output_rate.md` was not appended.

## Target output shape reminder

The full manifest requires 13 oracle columns:

```text
stay_id INTEGER
charttime TIMESTAMP
weight DECIMAL(38,3)
uo DOUBLE
urineoutput_6hr DOUBLE
urineoutput_12hr DOUBLE
urineoutput_24hr DOUBLE
uo_mlkghr_6hr DECIMAL(38,4)
uo_mlkghr_12hr DECIMAL(38,4)
uo_mlkghr_24hr DECIMAL(38,4)
uo_tm_6hr DECIMAL(38,2)
uo_tm_12hr DECIMAL(38,2)
uo_tm_24hr DECIMAL(38,2)
```

The candidate must additionally emit the required uncast opaque key columns
`icu_encounter_key` and `patient_key` (both `STRING`, type-prefixed and
verbatim). The manifest comparison key is `(stay_id, charttime)`; the two
resource keys are required candidate metadata, not source oracle columns.
