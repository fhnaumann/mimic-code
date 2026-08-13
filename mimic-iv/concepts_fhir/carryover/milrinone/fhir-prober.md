# FHIR prober mapping — `milrinone`

**Concept:** `medication/milrinone`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/milrinone/source-analyst.md`  
**Probe date:** 2026-08-13  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Resource mapping and exact discriminator

`mimiciv_icu.inputevents` maps one-for-one to the ICU
`MedicationAdministration` resource stream. The administered medication is
carried in `MedicationAdministration.medicationCodeableConcept.coding` by the
exact source itemid:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu
code   = "221986"
display = "Milrinone"
```

The source literal `itemid = 221986` was confirmed in the read-only DuckDB
dimension as `(221986, 'Milrinone', 'inputevents')` and independently in the
served Delta coding. The exact system plus exact string code is the
discriminator. Do not use `meta.profile` or `display`, and do not translate the
code.

Use this constrained coding group in the MedicationAdministration
ViewDefinition:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221986')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The target returned 15 coding rows for 15 distinct MedicationAdministration
resources. Code `221986` occurred under no other medication coding system
(0 rows). Across the complete ICU medication system, the coding projection
returned 20,404 rows for 20,404 distinct resources. Therefore the
codings-per-resource ratio is **15/15 = 1.000** for the target and
**20,404/20,404 = 1.000** for the ICU stream; the constrained `forEach` does
not multiply target rows.

The Delta warehouse has no served `CodeSystem` resource table, so the code is
validated from the MedicationAdministration coding and the DuckDB `d_items`
dimension, not from a CodeSystem resource.

## Canonical support ViewDefinitions

### MedicationAdministration

These support columns preserve opaque resource/reference keys for joins only.
They must not be parsed or used to recover a source identifier.

```json
{
  "resource": "MedicationAdministration",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "medadmin_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
        { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
        { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
        { "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" },
        { "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" },
        { "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" },
        { "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }
      ]
    },
    {
      "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221986')",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "code_system" },
        { "path": "display", "name": "code_display" }
      ]
    }
  ]
}
```

`MedicationAdministration.context` is the served R4 Encounter reference field;
the path is `context.getReferenceKey(Encounter)`, not
`encounter.getReferenceKey(Encounter)`. The target had a context reference on
15/15 rows and a Patient subject reference on 15/15 rows. No Patient join is
needed by the six-column source output.

Pathling materialized all aliases above as Spark `STRING`, including the
Quantity values and dateTime choices. The raw encoded fields are
`dosage.dose.value: decimal(32,6)` and
`dosage.rateQuantity.value: decimal(32,6)`. The implementer must cast the
numeric aliases to the manifest's `FLOAT` type and FHIR datetime aliases to
`TIMESTAMP_NTZ` in the final SQL. Do not use an offset-aware `TIMESTAMP` cast.

### ICU Encounter support

The source `stay_id` is carried by the ICU Encounter identifier, not by the
opaque Encounter resource key:

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "encounter_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
      ]
    }
  ]
}
```

The ICU Encounter identifier system is the stream discriminator. The served
warehouse has 140 ICU Encounter resources, all with a non-null
`encounter-icu` identifier value; the identifier value type is `string`. A
flat support view over all Encounter resources has 637 rows and 140 populated
`stay_id_str` values, so the system restriction must be retained. Join
`encounter_key` to the MedicationAdministration context reference key and
emit `CAST(stay_id_str AS INTEGER) AS stay_id`. Never emit either UUID key as
`stay_id`.

## Source column → FHIRPath mapping

The final types are the immutable full-oracle manifest types. FHIR element
types and materialized ViewDefinition types are shown separately because
Pathling aliases are string-like for Quantity and dateTime values.

| Source column / output | Canonical FHIR extraction (`{path, name}`) | FHIR type | Probe result / final type |
|---|---|---|---|
| `itemid` (filter only) | `{ "path": "code", "name": "item_code" }` inside the constrained medication coding `forEach`; paired with `{ "path": "system", "name": "code_system" }` | `Coding.code` / `Coding.system`, strings | Exact system + code `221986`: 15/15 rows and resources; display `Milrinone` 15/15; not emitted |
| `stay_id` | MA `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key string, then `Identifier.value` string | 15/15 resolved; final `CAST(stay_id_str AS INTEGER)` → `INTEGER` |
| `linkorderid` | **No FHIRPath; no `select.column` is emitted** | Not represented | DuckDB source 15/15 non-null; preserve manifest shape with typed `CAST(NULL AS INTEGER)` |
| `rate` → `vaso_rate` | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value`, decimal | 15/15 non-null; materialized `STRING`; final `CAST(rate_value AS FLOAT)` → `FLOAT` |
| `amount` → `vaso_amount` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value`, decimal | 15/15 non-null; materialized `STRING`; final `CAST(amount_value AS FLOAT)` → `FLOAT` |
| `starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `effective[x] = Period.start`, `dateTime` | 15/15 non-null for this target; materialized `STRING`; final `CAST(... AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `endtime` when rate is non-null | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `effective[x] = Period.end`, `dateTime` | 15/15 non-null for this target; materialized `STRING`; final `CAST(... AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `endtime` when rate is null | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effective[x] = dateTime`, `dateTime` | 0/15 in this target; required for the general ICU stream and contains source `endtime` only |

The unit support paths are `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }` and `{ "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }`, both FHIR `string`. They were populated 15/15 as `mcg/kg/min` and `mg`, respectively. The source SQL does not select or filter `rateuom` or `amountuom`; no unit predicate or conversion belongs in the port.

## Effective choice, dosage, null, and cardinality probes

For the exact system/code target, the materialized ViewDefinition counts were:

| Alias | Total | Non-null |
|---|---:|---:|
| `medadmin_key` | 15 | 15 |
| `patient_key` | 15 | 15 |
| `encounter_key` | 15 | 15 |
| `item_code` | 15 | 15 |
| `code_system` | 15 | 15 |
| `code_display` | 15 | 15 |
| `effective_datetime` | 15 | 0 |
| `effective_period_start` | 15 | 15 |
| `effective_period_end` | 15 | 15 |
| `rate_value` | 15 | 15 |
| `rate_unit` | 15 | 15 |
| `amount_value` | 15 | 15 |
| `amount_unit` | 15 | 15 |

The broader ICU MedicationAdministration stream had 20,404 resources:

```text
effectiveDateTime       9,366 / 20,404
effectivePeriod.start  11,038 / 20,404
effectivePeriod.end    11,038 / 20,404
dosage.dose.value      20,404 / 20,404
dosage.rateQuantity.value 11,038 / 20,404
context.reference      20,404 / 20,404
identifier non-empty        0 / 20,404
```

The ETL branch is therefore confirmed: non-null rate writes
`effectivePeriod` containing source `starttime` and `endtime`; null rate
writes only source `endtime` as `effectiveDateTime`. Both effective variants
must be projected in a reusable view. For this milrinone demo target, all
15 rows are rate-bearing and Period-valued.

The ICU medication coding is one coding per resource: 20,404/20,404 for the
complete ICU system and 15/15 for milrinone. The source target has one output
row per matching inputevent; the demo DuckDB query returned 15 rows, with no
NULL selected source values and 15 distinct `(stay_id,starttime)` keys.

## Natural key and DuckDB oracle checks

The immutable full manifest declares six output columns with types
`INTEGER, INTEGER, FLOAT, FLOAT, TIMESTAMP, TIMESTAMP`, comparison key
`(stay_id,starttime)`, `key_probes: 4`, and 9,573 full-oracle rows. This is
comparison metadata, not a FHIR resource key and not a claim that
`linkorderid` is unique.

The demo DuckDB source query `inputevents WHERE itemid=221986` returned 15
rows: `stay_id`, `linkorderid`, `rate`, `amount`, `starttime`, and `endtime`
were each non-null 15/15; `(stay_id,starttime)` had 15 distinct keys and
`linkorderid` had 6 distinct values.

The Delta target joined to the source on `(stay_id,starttime)` with 15/15
paired rows, zero source-only rows, and zero FHIR-only rows. Agreement was:

| Output | Oracle/FHIR agreement |
|---|---:|
| `stay_id` via ICU Encounter identifier | 15/15 exact |
| `starttime` via Period.start | 15/15 exact |
| `endtime` via Period.end | 15/15 exact |
| `vaso_rate` after `FLOAT` cast | 0/15 bitwise exact; 15/15 within `1e-6`; max absolute difference `4.825935363828027e-7` |
| `vaso_amount` after `FLOAT` cast | 0/15 bitwise exact; 15/15 within `1e-6`; max absolute difference `9.240722658176992e-7` |
| `linkorderid` | source 15/15 non-null; no FHIR value/path |

The numeric differences are the upstream served Quantity precision loss:
FHIR stores six-decimal `decimal(32,6)` values while the source columns are
FLOAT. The direct Quantity paths are the faithful mapping; do not invent a
conversion or use a resource id to recover source precision.

## Gaps and representability

### `linkorderid` — not representable, ancillary for this concept

The served ICU MedicationAdministration stream has no non-empty
`MedicationAdministration.identifier` on 0/20,404 resources (and 0/15
milrinone resources). The ICU ETL writes no inputevent identifier or
`linkorderid`; its opaque resource key is not a mapping for that source value.
The value is not absent-but-derivable and no measured approximation is
available. Do not parse, regenerate, brute-force, hardcode, or otherwise use
the resource id as a side channel. Emit a typed NULL `INTEGER` if preserving
the six-column manifest shape.

For this concept, `linkorderid` is an output payload/linkage field. It does not
control source row inclusion, the manifest natural key `(stay_id,starttime)`,
or any source-side branch/window/grouping. It can matter to a downstream
consumer that needs inputevent linkage, but the observed loss is ancillary to
the milrinone extraction rather than an essential missing discriminator for
this concept.

### `starttime` on rate-null rows — absent and not representable in the general stream

The rate-null `effectiveDateTime` branch stores only source `endtime`; it has
no FHIR element carrying source `starttime`, and no exact derivation exists.
This gap is not exercised by the 15-row milrinone demo target because all
15 rates are non-null. It must nevertheless remain in the reusable mapping:
project both effective variants and use Period.start where present rather
than assuming the dateTime branch can supply starttime.

### Quantity precision — not representable, deterministically approximable

The full source FLOAT precision is not retained in the served six-decimal
Quantity values. On the measured target, direct FHIR values were within
`1e-6` on 15/15 rates and 15/15 amounts, but no row was bitwise exact after
the final FLOAT casts. This is an upstream representation loss, not a path
choice. Preserve direct FHIR values; do not replace them with a heuristic.

### Datetime normalization

FHIR datetime aliases are offset-bearing strings. Cast them directly to
`TIMESTAMP_NTZ` to preserve the serialized MIMIC wall-clock value and avoid
machine-timezone conversion. The existing dataset-wide ETL can irreversibly
normalize a DST-gap wall time by one hour; no milrinone demo row exhibited
such a mismatch. The opaque MedicationAdministration key must not be used to
undo that transformation.

## Notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

* **MIMIC ids live in `identifier.value` as strings**: forced
  `stay_id` through the ICU Encounter identifier and kept
  `getResourceKey()`/`context.getReferenceKey(Encounter)` join-only, with a
  final integer cast.
* **Encounter has three identifier systems; class discriminates none**:
  forced the exact `encounter-icu` system for the stay join.
* **Polymorphic fields mix datatypes across rows**: required both effective
  variants and the Period.end/dateTime coalesce for endtime.
* **FHIR datetimes carry an offset; cast to `TIMESTAMP_NTZ`**: determines the
  datetime conversion.
* **Quantity.value ViewDefinition aliases materialize as VARCHAR**: requires
  final numeric casts; the fresh raw schema probe measured `decimal(32,6)`.
* **Raw `Mimic*.ndjson.gz` is stale**: all resource/code/cardinality claims
  above came from Delta, not ndjson.

The provisional fragments read were `MIMIC_NOTES.d/README.md`,
`MIMIC_NOTES.d/dopamine.md`, `MIMIC_NOTES.d/dobutamine.md`, and
`MIMIC_NOTES.d/epinephrine.md`. Their ICU medication hypotheses were treated
as leads and independently verified against the authoritative Delta target
and complete ICU stream. No sibling fragment was edited.

No implementation artifact or immutable attempt artifact was created.
