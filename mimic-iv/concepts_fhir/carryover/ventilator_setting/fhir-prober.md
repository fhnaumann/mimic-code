# FHIR mapping: `ventilator_setting`

## Probe basis

- Source analysis: `mimic-iv/concepts_fhir/carryover/ventilator_setting/source-analyst.md`.
- Source table: `mimiciv_icu.chartevents` (the source SQL uses the
  dataset-qualified spelling `physionet-data.mimiciv_icu.chartevents`).
- FHIR resource confirmed in the authoritative embedded Spark/Delta warehouse:
  `Observation`.
- Warehouse probed: `/Users/nau025/warehouses/mimic-iv-demo/delta`, using
  Pathling 9.6.0 embedded on Spark 4.0.2. The local DuckDB oracle used for
  relational checks was `/Users/nau025/warehouses/mimic4-demo.db`.
- The source predicate is `value IS NOT NULL AND stay_id IS NOT NULL` plus the
  15 literal itemids listed below. The DuckDB target had 14,831 rows after this
  predicate. The projected FHIR target had 14,831 coding rows and 14,831
  distinct Observation resources.

## Canonical ViewDefinition extraction groups

The code group must constrain the coding inside `forEach`; do not filter on
`meta.profile`.

```json
{
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_key"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "issued", "name": "issued"},
        {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
        {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
        {"path": "(value).ofType(Quantity).code", "name": "quantity_code"},
        {"path": "(value).ofType(Quantity).system", "name": "quantity_system"},
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
    }
  ]
}
```

All FHIRPath aliases above are FHIR-typed extraction columns. In particular,
`getResourceKey()` and both `getReferenceKey(...)` results are opaque string
identity keys for equality joins only; they are not `subject_id` or `stay_id`.
The materialized Pathling types observed were: identity/reference aliases
`string`; `effective_datetime` `string`; `issued` native Spark `timestamp`;
Quantity value/unit/code/system and `value_string` `string` aliases. The raw
FHIR `Observation.valueQuantity.value` is `decimal(32,6)`, but the
ViewDefinition Quantity value alias is string-like and must be cast before
numeric cleaning or aggregation.

## Source-column to FHIR-path mapping

| Source column | FHIR resource/path (`{path, name}`) | FHIR type / target typing requirement | Probe result and use |
|---|---|---|---|
| `chartevents.itemid` | `Observation.code.coding` filtered by the exact chartevents system; `{path: "code", name: "item_code"}` | `Coding.code` is `string`; cast to integer only after system filtering | The 15 source itemids were present under the exact system. 14,831/14,831 target rows had a non-null code. |
| Binding for `itemid` | Inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"`; `{path: "system", name: "item_system"}` | `string` | This is the discriminator: exact system plus exact string code. `meta.profile` is not used. |
| `d_items.label`/served item display (not selected by source SQL) | `{path: "display", name: "item_display"}` in the same coding `forEach` | `string` | Display was non-null and constant per target code: all 15 code/display pairs were populated. It is descriptive only; never filter on it. |
| `chartevents.subject_id` | Observation `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}`; join to Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | Reference/key and identifier value are `string`; final SQL must `CAST(subject_id_str AS INTEGER)` | `patient_key` and the Patient identifier were populated and joined for 14,831/14,831 target rows. Source/FHIR distinct `(subject_id, stay_id)` sets both had 76 pairs. Do not parse either UUID key. |
| `chartevents.stay_id` | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}`; join to ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | Reference/key and identifier value are `string`; final SQL must `CAST(stay_id_str AS INTEGER)` | The ICU Encounter view had 140/140 resources with the ICU identifier. The target Observation-to-Encounter join and `stay_id_str` were populated for 14,831/14,831 rows. `Encounter.class` is not a stream discriminator. |
| `chartevents.charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | FHIR dateTime; materialized alias `string`; outer SQL should use `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` | 14,831/14,831 target rows populated; `effective.ofType(Period).start/end` and `effective.ofType(instant)` were 0/14,831. Source/FHIR `(subject_id, stay_id, charttime, itemid)` multisets agreed exactly on the demo target. |
| `chartevents.storetime` | `{path: "issued", name: "issued"}` | FHIR `instant`; materialized as native Spark `timestamp` | Ancillary only: source SQL selects it but never filters, groups, or emits it. It was non-null in the source and FHIR target on 14,831/14,831 rows. Across all chartevents Observations, issued was populated on 667,703/668,862, so do not assume this field is globally total. |
| `chartevents.valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | FHIR `Quantity.value` decimal; ViewDefinition alias is string-like; cast to numeric before use | 14,408/14,831 target rows had Quantity values, exactly matching source `valuenum IS NOT NULL` (14,408); all numeric source/FHIR groups agreed within `rtol=atol=1e-6` after the source cleaning rules below. |
| `chartevents.valueuom` | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}`; optionally `{path: "(value).ofType(Quantity).code", name: "quantity_code"}` and `{path: "(value).ofType(Quantity).system", name: "quantity_system"}` | `unit`/`code`/`system` are `string` | `quantity_unit` was non-null on 10,343/14,831 target rows, matching source `valueuom` non-null 10,343/14,831. Unit-bearing target counts were exact by item. The ETL commonly sets Quantity code equal to unit and uses the proprietary `mimic-units` system when present. |
| `chartevents.value` when `valuenum IS NULL` | `{path: "(value).ofType(string)", name: "value_string"}` | FHIR `string` | 423/14,831 target rows had `value_string`, exactly matching source `valuenum IS NULL`; source text multiset agreement was exact for every item. This is the reliable categorical/text path. |
| `chartevents.value` when `valuenum IS NOT NULL` | No source-text path; the FHIR value is Quantity | Source `VARCHAR(200)` is not preserved as a string on these rows | The ETL writes Quantity and drops source `value` whenever `valuenum` is non-null. This affects the three text-pivot itemids; see the gap section. |

## Exact item bindings and served counts

The code discriminator is `item_system` equal to
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus the
exact `item_code` string. This system is established from the served Delta, not
from the table name. The 15 code counts below are FHIR coding/resource counts;
the DuckDB source counts after `value IS NOT NULL AND stay_id IS NOT NULL`
were identical. The target coding-per-resource ratio was
`count(*) / count(distinct observation_key) = 14,831 / 14,831 = 1.000` (the
same all-chartevents ratio was 668,862/668,862 = 1.000), so the filtered
`forEach` does not fan out this target.

| Exact `item_code` | Served display | FHIR/source rows | Quantity rows | String rows | Observed unit |
|---:|---|---:|---:|---:|---|
| `224688` | Respiratory Rate (Set) | 801 | 801 | 0 | `insp/min` |
| `224689` | Respiratory Rate (spontaneous) | 1,314 | 1,314 | 0 | `insp/min` |
| `224690` | Respiratory Rate (Total) | 1,331 | 1,331 | 0 | `insp/min` |
| `224687` | Minute Volume | 1,359 | 1,359 | 0 | `L/min` |
| `224685` | Tidal Volume (observed) | 1,331 | 1,331 | 0 | `mL` |
| `224684` | Tidal Volume (set) | 769 | 769 | 0 | `mL` |
| `224686` | Tidal Volume (spontaneous) | 661 | 661 | 0 | `mL` |
| `224696` | Plateau Pressure | 510 | 510 | 0 | `cmH2O` |
| `220339` | PEEP set | 1,447 | 1,447 | 0 | `cmH2O` |
| `224700` | Total PEEP Level | 490 | 490 | 0 | `cmH2O` |
| `223835` | Inspired O2 Fraction | 1,746 | 1,746 | 0 | null |
| `223849` | Ventilator Mode | 1,048 | 1,011 | 37 | null |
| `229314` | Ventilator Mode (Hamilton) | 402 | 402 | 0 | null |
| `223848` | Ventilator Type | 1,292 | 906 | 386 | null |
| `224691` | Flow Rate (L/min) | 330 | 330 | 0 | `L/min` |

The source item-code order in the SQL is different from the sorted table above;
the set is unchanged. No served `CodeSystem` resource was available, so code
validation is by the observed Observation bindings and the DuckDB source counts.

## Numeric transformations required by the source SQL

The FHIR Quantity carries the raw source `valuenum`, not the source query's
cleaned CTE alias. Cast the materialized Quantity value before applying these
rules:

- For `223835`, if Quantity value is between `0.20` and `1` inclusive,
  multiply by 100; if it is greater than 1 and less than 20, emit typed NULL;
  if it is between 20 and 100 inclusive, retain it; otherwise emit typed NULL.
  The demo had 3 FIO2 rows cleaned to NULL and 1,743 cleaned numeric rows.
- For `220339` and `224700`, emit typed NULL when Quantity value is greater
  than 100 or less than 0; otherwise retain it. No invalid PEEP rows occurred
  in the demo target.
- All other numeric itemids pass the Quantity value through.

The source SQL's final numeric expressions are `MAX` per exact
`(subject_id, charttime)` group and item discriminator. The FHIR target has
14,831 resources but 2,064 distinct `(subject_id, charttime)` groups in the
target source population; repeated same-item observations must remain rows
until the source-equivalent aggregation. The source/FHIR effective-key
multiset check was exact on the demo. After the Patient/Encounter joins, the
implementer must group by the cast Patient identifier and `effective_datetime`
wall time, use `MAX(CAST(stay_id_str AS INTEGER))` for `stay_id`, and apply the
item-specific `MAX(CASE ...)` pivots; no resource id is a source-row key.

## Gaps and transformations

### Absent but approximable: categorical value loss on numeric-coded ventilator settings

For source rows with non-null `valuenum`, the chartevents ETL writes only
`valueQuantity`; source `value` is absent from FHIR. The source SQL nevertheless
uses `MAX(value)` for `ventilator_type`, `ventilator_mode`, and
`ventilator_mode_hamilton`.

- `itemid=223848`: 906 rows have source values `Drager`, `Avea`, or `Other` but
  only Quantity values 1, 2, or 6 in FHIR; 386 `Hamilton` rows survive as
  `valueString`.
- `itemid=223849`: 1,011 source text rows are Quantity-only and 37 survive as
  `valueString`.
- `itemid=229314`: all 402 source text rows are Quantity-only.

The affected counts are 906, 1,011, and 402 rows/groups respectively (2,319
rows total; the item-specific groups are one per source row in this demo).
The missing branch discriminator itself survives: `value.ofType(Quantity)` is
non-null exactly on the numeric-source branch and `value.ofType(string)` is
non-null exactly on the null-`valuenum` branch. An empirical reverse codebook
from the served Quantity values was one-to-one and reproduced source text on
906/906, 1,011/1,011, and 402/402 demo rows, but that is an approximation based
on observed data, not a FHIR semantic guarantee that a Quantity's number means
the source label. If the implementer does not use that measured codebook, emit
typed NULL for only these identifiable Quantity-backed categorical rows rather
than dropping whole output groups. The gap changes clinically meaningful
categorical output values but does not change source row inclusion, the
`(subject_id, charttime)` grouping key, or the numeric columns; it is therefore
a bounded row-level coverage gap, not by itself a whole-concept block.

### Not representable: effective-time serialization in DST gaps

The source `charttime` maps to `effectiveDateTime`, and the authoritative demo
target had exact wall-time agreement for all 14,831 rows after
`TIMESTAMP_NTZ` casting. The upstream chartevents ETL casts the naive source
time through `TIMESTAMPTZ`; a spring-forward-gap source wall time can therefore
be served one hour later. The original wall time is not present in a FHIR
element. Resource identity is opaque and must not be regenerated or used to
recover it. This is the established dataset transformation from
`MIMIC_NOTES.md`; it may affect the source natural grouping/time on the full
cohort, but there were no affected target rows in this demo comparison.

The `issued`/`storetime` field is not part of the source output and is not a
tie-breaker. Do not substitute it for `charttime`.

### ETL row omissions

The upstream chartevents ETL excludes source rows with `value IS NULL` and one
hard-coded duplicate `(stay_id=34934165, charttime='2151-10-03 05:14:00.000')`.
The source concept already requires non-null `value` and `stay_id`, and the
DuckDB target count and per-code counts matched FHIR exactly at 14,831; neither
omission affected this target. No resource-id side channel is permitted for
finding or restoring an omitted row.

## Notes that changed this mapping decision

- The identifier-spine and ICU-Encounter entries in `MIMIC_NOTES.md` require
  Patient/Encounter identifier values for `subject_id`/`stay_id`, with UUID
  reference keys used only for equality joins. This prevented mapping either
  source ID to `getResourceKey()`.
- The code-system and profile entries in `MIMIC_NOTES.md` require exact served
  `system + code` filtering and prohibit `meta.profile` discrimination. The
  target binding is the proprietary chartevents system above.
- The categorical-chartevents and Quantity-alias entries require separate
  `valueString` and Quantity projections and a numeric cast of the Quantity
  alias.
- The datetime entry requires `TIMESTAMP_NTZ`, not an offset-aware parser, and
  the opaque-ID policy forbids the historical UUID-based DST recovery leads.

## Evidence summary

Embedded Pathling probes over the demo Delta measured: Observation target
resource/coding count 14,831/14,831; coding ratio 1.000; exact system and all
15 per-code counts as tabulated; Patient and ICU Encounter reference joins
14,831/14,831; Patient identifiers 100/100; ICU Encounter identifiers 140/140;
effective dateTime 14,831/14,831 with Period and instant variants 0; Quantity
branch 14,408 and string branch 423; source/FHIR effective-key multiset exact;
numeric values exact within `1e-6` after cleaning; and source text exact on all
423 string-branch rows. The DuckDB oracle checks used
`mimiciv_icu.chartevents` in `/Users/nau025/warehouses/mimic4-demo.db`.
