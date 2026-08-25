# FHIR mapping: `ventilator_setting` (reopened attempt_0002)

## Probe basis

- Source analysis: `mimic-iv/concepts_fhir/carryover/ventilator_setting/source-analyst.md`.
- Canonical source: `mimic-iv/concepts/measurement/ventilator_setting.sql`.
- Source table: `mimiciv_icu.chartevents` (the SQL uses the
  dataset-qualified spelling `physionet-data.mimiciv_icu.chartevents`).
- FHIR resource confirmed in the authoritative warehouse: `Observation`.
- Warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`, probed with
  embedded Pathling 9.6.0 on Spark 4.0.2, with Spark session timezone UTC.
- Read-only DuckDB oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- Relevant upstream ETL: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql`.
  Commit `e7c326b` (#125) is the component-text rebuild; `ade10fb` (#124)
  generated the FHIR tables under UTC. The ETL still contains the
  `TIMESTAMPTZ` expressions at lines 9 and 67, but the rebuilt warehouse's
  target effective wall times were exact in this probe. Resource IDs were not
  read as source data, regenerated, parsed, or used for any recovery.

The DuckDB source predicate `value IS NOT NULL AND stay_id IS NOT NULL` left
14,831 target rows. The same 15 item codes produced 14,831 FHIR coding rows,
14,831 distinct Observation resources, and 2,064 distinct `(subject_id,
charttime)` groups. The upstream global `value IS NOT NULL` and hard-coded
duplicate exclusions are at ETL lines 34-37; neither changed this target.

## Canonical ViewDefinition extraction groups

The code discriminator is constrained inside `forEach`; do not use
`meta.profile`. The component group is deliberately `forEachOrNull`: it is
absent when the source text is just the number restated.

```json
{
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_key"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "issued", "name": "issued"},
        {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
        {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
        {"path": "(value).ofType(string)", "name": "value_string"}
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')",
      "column": [
        {"path": "code", "name": "item_code"},
        {"path": "system", "name": "item_system"},
        {"path": "display", "name": "item_display"}
      ]
    },
    {
      "forEachOrNull": "component",
      "column": [
        {"path": "code.coding.code", "name": "component_item_code"},
        {"path": "code.coding.system", "name": "component_system"},
        {"path": "value.ofType(string)", "name": "component_text"}
      ]
    }
  ]
}
```

Observed materialized Pathling types: resource/reference keys, coding fields,
Quantity aliases, and string aliases were `string`; `effective_datetime` was
`string`; `issued` was native Spark `timestamp`. Raw
`Observation.valueQuantity.value` was `decimal(32,6)`. Therefore the
implementer must cast `quantity_value` to the manifest's numeric type before
the source FIO2/PEEP cleaning and numeric `MAX`; it must cast identifier
strings to `INTEGER`, and use `TIMESTAMP_NTZ` for the final `charttime`.

## Identifier spine

`subject_id` and `stay_id` are not resource keys. Materialize these supporting
views and join by opaque key equality:

```json
{"path": "getResourceKey()", "name": "patient_key"}
{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}

{"path": "getResourceKey()", "name": "encounter_key"}
{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}
```

The target Observation-to-Patient and Observation-to-ICU-Encounter joins were
14,831/14,831. All 100 demo Patients had the patient identifier and all 140
ICU Encounters had the ICU identifier. The final SQL types must be
`CAST(subject_id_str AS INTEGER)` and `CAST(stay_id_str AS INTEGER)`; keep the
`patient_key` and `encounter_key` only as prefixed opaque equality keys.

## Source-column to FHIRPath mapping

| Source column | Canonical `{path, name}` mapping | FHIR type / materialized type / final target | Probe result and use |
|---|---|---|---|
| `chartevents.subject_id` | Observation `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}`; Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | Reference key `string`; identifier `string`; final `INTEGER` | Patient-key join and identifier were non-null on 14,831/14,831. |
| `chartevents.stay_id` | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}`; ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | Reference key and identifier `string`; final `INTEGER` | ICU Encounter-key join and identifier were non-null on 14,831/14,831. Filter the ICU Encounter identifier system, not `Encounter.class`. |
| source row identity | Observation `{path: "getResourceKey()", name: "observation_key"}` | Opaque FHIR `string` | Non-null 14,831/14,831. Use only for resource identity/provenance or equality; it is not a source row key and must not be parsed. |
| `chartevents.itemid` | Code group `{path: "code", name: "item_code"}` | `Coding.code` `string`; final cast to `INTEGER` only after system + exact-code filtering | Non-null 14,831/14,831; all 15 source codes were present. |
| item binding | Code group `{path: "system", name: "item_system"}` | `Coding.system` `URI`/`string` | The served system was exactly `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` for 14,831/14,831 target codings. |
| served item label | Code group `{path: "display", name: "item_display"}` | `Coding.display` `string` | Non-null 14,831/14,831. Descriptive only; do not filter on display. |
| `chartevents.charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | FHIR `dateTime`; materialized `string`; final `TIMESTAMP_NTZ` | Non-null 14,831/14,831. `Period.start/end` and `instant` were 0/14,831. Source/FHIR `(subject_id, stay_id, charttime, itemid)` multiplicities agreed 14,831/14,831; distinct source and candidate groups were both 2,064. |
| `chartevents.storetime` | `{path: "issued", name: "issued"}` | FHIR `instant`; materialized native Spark `timestamp` | Non-null FHIR 14,831/14,831 and source 14,831/14,831. It is selected by the CTE but is not part of the canonical output or a tie-breaker. |
| `chartevents.valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | FHIR `Quantity.value` `decimal`; materialized alias `string`; final numeric type must match the manifest (`FLOAT`) | Quantity non-null 14,408/14,831, exactly source `valuenum IS NOT NULL` 14,408/14,831. After applying the canonical cleaning to both sides, numeric group values agreed within `rtol=atol=1e-6` on 14,831/14,831 groups. |
| `chartevents.valueuom` | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | FHIR `Quantity.unit` `string` (the ETL also writes `Quantity.code` as the same unit and `Quantity.system` as the MIMIC units URI when non-null) | Non-null FHIR 10,343/14,831 and source 10,343/14,831. This field is not selected by the final concept output. |
| `chartevents.value` where `valuenum IS NULL` | `{path: "(value).ofType(string)", name: "value_string"}` | FHIR `string`; materialized `string` | Non-null 423/14,831, exactly source `valuenum IS NULL` 423/14,831. The text aggregate for all three text-pivot itemids agreed exactly on 2,742/2,742 groups when this branch was combined with the component branch. |
| `chartevents.value` where numeric text is meaningful | Component `{path: "value.ofType(string)", name: "component_text"}` inside `forEachOrNull: "component"`; component code/system are `{path: "code.coding.code", name: "component_item_code"}` and `{path: "code.coding.system", name: "component_system"}` | FHIR `Observation.component.valueString` `string`; nested component `Coding.code` `string`, `Coding.system` `URI`/`string`; materialized aliases `string` | Component text non-null 2,319/14,831 overall. Every component coding matched the parent item code and the exact chartevents system (2,319/2,319). It is the rebuilt representation of the source mode/type text when `valuenum` is non-null. |
| derived cleaned `valuenum` | No separate source FHIR element; derive in SQL from `quantity_value` | Numeric output `FLOAT`, nullable | Apply the canonical FIO2 and PEEP rules after casting Quantity value; do not use the component text for numeric pivots. |

The source SQL uses `value` only as a row-inclusion predicate for the numeric
items and as the three textual pivots for itemids 223848, 223849, and 229314.
The component branch removes the prior mapping gap for those pivots: it
preserves the source text on all numeric-text rows, while direct `valueString`
preserves the null-`valuenum` rows.

## Exact code set, systems, and counts

The source literals are exactly:
`224688, 224689, 224690, 224687, 224685, 224684, 224686, 224696, 220339,
224700, 223835, 223849, 229314, 223848, 224691`.

The authoritative unfiltered `code.coding` probe found only the following
system for these codes. The CodeSystem resource itself is absent from the
Delta warehouse; validation is from served codings and the read-only oracle.

| Item code | FHIR/source rows | coding rows / distinct resources | ratio | Quantity | direct `valueString` | component text |
|---:|---:|---:|---:|---:|---:|---:|
| 224688 | 801 | 801 / 801 | 1.000 | 801 | 0 | 0 |
| 224689 | 1,314 | 1,314 / 1,314 | 1.000 | 1,314 | 0 | 0 |
| 224690 | 1,331 | 1,331 / 1,331 | 1.000 | 1,331 | 0 | 0 |
| 224687 | 1,359 | 1,359 / 1,359 | 1.000 | 1,359 | 0 | 0 |
| 224685 | 1,331 | 1,331 / 1,331 | 1.000 | 1,331 | 0 | 0 |
| 224684 | 769 | 769 / 769 | 1.000 | 769 | 0 | 0 |
| 224686 | 661 | 661 / 661 | 1.000 | 661 | 0 | 0 |
| 224696 | 510 | 510 / 510 | 1.000 | 510 | 0 | 0 |
| 220339 | 1,447 | 1,447 / 1,447 | 1.000 | 1,447 | 0 | 0 |
| 224700 | 490 | 490 / 490 | 1.000 | 490 | 0 | 0 |
| 223835 | 1,746 | 1,746 / 1,746 | 1.000 | 1,746 | 0 | 0 |
| 223849 | 1,048 | 1,048 / 1,048 | 1.000 | 1,011 | 37 | 1,011 |
| 229314 | 402 | 402 / 402 | 1.000 | 402 | 0 | 402 |
| 223848 | 1,292 | 1,292 / 1,292 | 1.000 | 906 | 386 | 906 |
| 224691 | 330 | 330 / 330 | 1.000 | 330 | 0 | 0 |
| **total** | **14,831** | **14,831 / 14,831** | **1.000** | **14,408** | **423** | **2,319** |

The all-chartevents coding ratio was also 668,862/668,862 = 1.000. The
discriminator is therefore `item_system + exact item_code`; `meta.profile` is
not a discriminator. Component coverage on the three textual itemids is
223848: 906/1,292 (70.123%), 223849: 1,011/1,048 (96.469%), and 229314:
402/402 (100%). The complement is the direct `valueString` branch. The
component text values were `Drager/Avea/Other` for 223848, the ventilator-mode
labels for 223849, and Hamilton mode labels for 229314; no component was
emitted for these rows when the text merely restated the numeric value.

## Numeric cleaning and oracle checks

The raw FHIR Quantity is the source `valuenum`; the CTE cleaning must be
reapplied in the derived SQL:

- item 223835: multiply values in `[0.20, 1]` by 100; typed NULL for `(1,20)`;
  retain `[20,100]`; typed NULL otherwise. The target has 1,743 cleaned
  numeric values and 3 typed-NULL cleaned values.
- items 220339 and 224700: typed NULL for values `< 0` or `> 100`; retain the
  rest. No invalid PEEP value occurred in this target.
- all other numeric itemids pass through.

Read-only DuckDB/Pandas checks used the identifier spine and effective wall
time (never a resource ID):

- source/FHIR target row counts: 14,831/14,831;
- source/FHIR `(subject_id, stay_id, charttime, itemid)` key multiplicities:
  14,831/14,831 exact, with zero source-only or candidate-only keys;
- source/FHIR natural `(subject_id, charttime)` group counts: 2,064/2,064;
- cleaned numeric aggregate agreement: 14,831/14,831 groups within
  `rtol=atol=1e-6`;
- text aggregate agreement for 223848/223849/229314: 2,742/2,742 exact;
- source `storetime` versus FHIR `issued`: 14,831/14,831 full-tuple
  multiplicities exact.

## Gaps and representability

No output-affecting gap was identified for the current target after probing the
rebuilt component representation. The old categorical loss is no longer a
gap: direct `valueString` covers all null-`valuenum` text rows, and
`component.valueString` covers all 2,319 numeric-text rows used by the three
text pivots. The source text for numeric items that is merely the number
restated is not a separate FHIR string, but this concept never emits that
text; its numeric Quantity and row presence are sufficient.

`storetime`/`issued` is representable but ancillary and not in the canonical
result. `valueuom`/Quantity.unit is representable where non-null but also not
in the canonical result. The source row filters are fully covered on this
target: source `value` and `stay_id` were non-null on 14,831/14,831, and the
ETL omissions changed 0 target rows.

The rebuilt demo effectiveDateTime matched source charttime on all 14,831
target rows. Do not add a DST workaround or infer one from resource IDs. The
upstream ETL statements remain cited at
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, but the UTC rebuild
means no DST divergence was observed here; a full-data comparator, not this
probe, remains authoritative for the full cohort.

## Notes that changed this mapping decision

- `MIMIC_NOTES.md` identifier-spine and opaque-ID entries require Patient and
  ICU Encounter identifier values for `subject_id`/`stay_id`, with resource
  keys used only for equality joins.
- Its code-system/profile entries require the served exact proprietary system
  plus code and prohibit `meta.profile` filtering.
- Its categorical-chartevents entry, updated for upstream `e7c326b`, required
  probing `component.valueString` rather than declaring the numeric mode/type
  text absent.
- Its UTC rebuild/DST entry prevented assuming the historical timestamp
  divergence and prohibited UUID recovery.
- Provisional fragments read: every file in
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`, including the prior
  `ventilator_setting.md` fragment. Other fragments were treated as leads;
  the relevant chartevents coding, issued, repeated-row, categorical, and
  obsolete UUID/DST leads were checked against the authoritative probe. The
  prior ventilator fragment's issued and absent-CodeSystem findings were
  confirmed; its component branch was not previously recorded.
