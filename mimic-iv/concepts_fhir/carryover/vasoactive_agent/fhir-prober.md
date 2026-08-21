# FHIR prober mapping — `vasoactive_agent`

**Concept:** `medication/vasoactive_agent`  
**Attempt:** `attempt_0001`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/vasoactive_agent/source-analyst.md`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Scope and source-table to FHIR-resource mapping

The target SQL is an interval overlay over the seven derived medication
dependencies. It does not read raw `inputevents` directly. Each dependency's
raw source is `mimiciv_icu.inputevents`, and the FHIR-side source mapping is:

| Source table / role | FHIR resource | Mapping boundary |
|---|---|---|
| `mimiciv_icu.inputevents` (the seven dependency streams) | `MedicationAdministration` | One served ICU MedicationAdministration per inputevent row; itemid is in `medicationCodeableConcept.coding`, timing in `effective[x]`, values in `dosage` |
| `mimiciv_icu.icustays` (support for `stay_id`) | ICU `Encounter` | `MedicationAdministration.context` references the ICU Encounter; the relational stay id is the ICU Encounter identifier value |
| `mimiciv_hosp.patients` (subject support) | `Patient` | `MedicationAdministration.subject` references Patient; the relational subject id is the Patient identifier value |

The target must consume the seven published dependency views rather than
re-derive them from raw resources. The parent interval table has no standalone
FHIR resource: its `starttime`/`endtime` boundaries are computed from the
dependency timing columns, and its seven rate columns are the dependency
`vaso_rate` values. The full oracle manifest shape is
`stay_id INTEGER`, `starttime TIMESTAMP`, `endtime TIMESTAMP`, followed by
`dopamine`, `epinephrine`, `norepinephrine`, `phenylephrine`, `vasopressin`,
`dobutamine`, and `milrinone` as `FLOAT`. The candidate additionally must carry
the manifest-required opaque support keys `icu_encounter_key` and `patient_key`
as strings; they are not oracle value columns.

## Exact medication coding discriminator

The seven source literals are preserved exactly as FHIR coding codes. The
served system for all seven is:

`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`

The canonical coding group is constrained inside the repeating coding
projection, with one column per coding element:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and (code='221653' or code='221662' or code='221289' or code='221906' or code='221749' or code='222315' or code='221986'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The local executable probe used the equivalent code-constrained `forEach` and
then checked the projected `code_system` exactly, because this installed
Pathling parser rejected a URI literal containing `://` inside `where(system=…)`.
That parser behavior is not a data finding. The discriminator remains
`system + exact code`, and the implementer must retain the exact system test
(inside `forEach` where accepted, or in the immediately consuming SQL if the
same parser limitation occurs). `meta.profile` is never a discriminator.

The observed code counts were:

| Source itemid | Drug | Served system | coding rows | distinct MedicationAdministration keys | ratio |
|---:|---|---|---:|---:|---:|
| 221653 | dobutamine | `…/mimic-medication-icu` | 44 | 44 | 1.000 |
| 221662 | dopamine | `…/mimic-medication-icu` | 28 | 28 | 1.000 |
| 221289 | epinephrine | `…/mimic-medication-icu` | 36 | 36 | 1.000 |
| 221906 | norepinephrine | `…/mimic-medication-icu` | 947 | 947 | 1.000 |
| 221749 | phenylephrine | `…/mimic-medication-icu` | 625 | 625 | 1.000 |
| 222315 | vasopressin | `…/mimic-medication-icu` | 55 | 55 | 1.000 |
| 221986 | milrinone | `…/mimic-medication-icu` | 15 | 15 | 1.000 |

The target total was 1,750 rows/resources. Each exact code was absent under
every other observed medication coding system. The complete coding projection
was 56,535 rows for 56,535 distinct resources. System totals were:

| `code.coding.system` | coding rows | distinct resources |
|---|---:|---:|
| `…/mimic-medication-formulary-drug-cd` | 34,205 | 34,205 |
| `…/mimic-medication-icu` | 20,404 | 20,404 |
| `…/mimic-medication-name` | 1,624 | 1,624 |
| `…/mimic-medication-poe-iv` | 302 | 302 |

`d_items` independently returned the seven `(itemid, label, linksto)` rows,
with labels Dobutamine, Dopamine, Epinephrine, Norepinephrine, Phenylephrine,
Vasopressin, Milrinone and `linksto='inputevents'` for every row. No served
CodeSystem resource exists (`src.read("CodeSystem")` raised `No data found for
resource type: CodeSystem`), so the served MedicationAdministration coding and
the dimension table are the authority.

## Canonical support ViewDefinitions

### MedicationAdministration

Use `context`, not `encounter`, for the R4 Encounter reference. Resource and
reference keys below are opaque, type-prefixed strings used only for equality
joins, grouping, or provenance.

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
        { "path": "(dosage.rate).ofType(Quantity).system", "name": "rate_system" },
        { "path": "(dosage.rate).ofType(Quantity).code", "name": "rate_code" },
        { "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" },
        { "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" },
        { "path": "(dosage.dose).ofType(Quantity).system", "name": "amount_system" },
        { "path": "(dosage.dose).ofType(Quantity).code", "name": "amount_code" },
        { "path": "identifier.value", "name": "identifier_value" },
        { "path": "supportingInformation.reference", "name": "supporting_reference" }
      ]
    },
    {
      "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and (code='221653' or code='221662' or code='221289' or code='221906' or code='221749' or code='222315' or code='221986'))",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "code_system" },
        { "path": "display", "name": "code_display" }
      ]
    }
  ]
}
```

FHIR types and materialized types:

| Alias | FHIR type | Served/materialized observation |
|---|---|---|
| `medadmin_key` | `MedicationAdministration` resource key string | `STRING`, 1,750/1,750 non-null and distinct |
| `patient_key` | `Reference(Patient)` key string | `STRING`, 1,750/1,750 non-null |
| `encounter_key` | `Reference(Encounter)` key string | `STRING`, 1,750/1,750 non-null |
| `item_code`, `code_system`, `code_display` | `Coding.code`, `.system`, `.display` strings | 1,750/1,750 each |
| `effective_datetime` | `dateTime` | View alias `STRING`; 0/1,750 target rows, populated in the general ICU stream |
| `effective_period_start`, `effective_period_end` | `Period.start/end` `dateTime` | View aliases `STRING`; 1,750/1,750 each |
| `rate_value` | `Quantity.value` decimal | View alias `STRING`; raw encoded field `decimal(32,6)`; 1,750/1,750 |
| `amount_value` | `Quantity.value` decimal | View alias `STRING`; raw encoded field `decimal(32,6)`; 1,750/1,750 |
| `rate_unit`, `rate_system`, `rate_code` | `Quantity.unit/system/code` strings | 1,750/1,750 each |
| `amount_unit`, `amount_system`, `amount_code` | `Quantity.unit/system/code` strings | 1,750/1,750 each |
| `identifier_value` | `Identifier.value` string | 0/1,750; the resource has no inputevent identifier |
| `supporting_reference` | `Reference.reference` string | 0/1,750 |

The broader ICU MedicationAdministration stream independently confirmed the
choice polymorphism: 20,404 resources, with `effectiveDateTime` on 9,366,
`effectivePeriod.start/end` on 11,038/11,038, dose on 20,404, and rate on
11,038. The ETL rule is rate-presence based: non-NULL source rate writes a
Period from source start/end; NULL rate writes only source endtime as
effectiveDateTime. Project both effective variants and coalesce only the end
after casting each alias to `TIMESTAMP_NTZ`.

### ICU Encounter support

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
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

The executable probe used `forEach: "identifier"` and filtered the projected
system in SQL for the same URI. Across all 637 Encounter resources, identifier
systems were hosp 275, ICU 140, and ED 222. The ICU projection was 140 rows for
140 distinct Encounter keys, with `stay_id_str` non-null 140/140. Every one of
the 1,750 target MedicationAdministration context references matched an ICU
Encounter and a non-null stay identifier: 1,750/1,750. Preserve
`encounter_key` as the final `icu_encounter_key` support column and cast only
`stay_id_str` to the manifest's `stay_id INTEGER`.

`Encounter.period.start/end` are FHIR `dateTime` strings and are not consumed
by this source SQL; do not substitute them for the ICU identifier or for
inputevent timing.

### Patient support

```json
{
  "resource": "Patient",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "patient_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
      ]
    }
  ]
}
```

The probe materialized Patient identifiers with an unfiltered identifier
projection and applied the exact system in SQL. There were 100 Patient rows,
100/100 non-null patient identifier values, and all 1,750 target subject
references resolved and agreed with the source `subject_id` 1,750/1,750. The
parent output has no `subject_id` column, but `patient_key` is a required
published support key and must be retained.

## Source column → FHIRPath mapping

The following table states FHIR types separately from final SQL types. FHIR
identifier and quantity/date aliases are string-like in materialized
ViewDefinitions; the implementer must cast to the manifest types in SQL.

| Source column / role | Canonical `{path, name}` | FHIR type | Demo population / target handling |
|---|---|---|---|
| `itemid` filter | `{ "path": "code", "name": "item_code" }` inside constrained medication coding `forEach`; paired with `{ "path": "system", "name": "code_system" }` and `{ "path": "display", "name": "code_display" }` | `Coding.code/system/display` strings | 44, 28, 36, 947, 625, 55, 15 by the seven exact codes; system + code is the discriminator; not a parent output |
| `orderid` (ETL identity component, not source output) | `{ "path": "getResourceKey()", "name": "medadmin_key" }` only | Opaque resource-key string | 1,750/1,750; equality/grouping support only; never invert it to an input value |
| `subject_id` support | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | Reference key string → `Identifier.value` string | 1,750/1,750 source agreement; final `patient_key` is `VARCHAR`; no parent integer subject output |
| `stay_id` | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | Reference key string → `Identifier.value` string | 1,750/1,750 resolved; `CAST(stay_id_str AS INTEGER)` gives final `stay_id` |
| `linkorderid` | **No FHIRPath**; no usable `MedicationAdministration.identifier` is present | Not representable | Source non-null 1,750/1,750; parent does not consume it. Child dependency outputs must use typed `NULL AS INTEGER`, not an id surrogate |
| `starttime` on rate-bearing rows | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` `dateTime` | 1,750/1,750 target rows; alias `STRING`, direct `TIMESTAMP_NTZ` cast; source/FHIR interval-key agreement 1,750/1,750 |
| `starttime` on rate-null rows | No FHIRPath; the dateTime branch carries no start | Absent / not representable on that branch | 0/1,750 target rows in demo; branch is identifiable by NULL `rate_value`; can affect the parent boundary set if present at full scale |
| `endtime` on rate-bearing rows | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `Period.end` `dateTime` | 1,750/1,750; direct `TIMESTAMP_NTZ` cast |
| `endtime` on rate-null rows | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effective[x] = dateTime` | 0/1,750 target rows; reusable mapping must coalesce this after Period.end |
| `rate` | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value` decimal | 1,750/1,750; raw `decimal(32,6)`, alias `STRING`; direct source agreement within `1e-6` on 1,750/1,750 |
| `rateuom` branch discriminator | `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }`; optional provenance `{ "path": "(dosage.rate).ofType(Quantity).code", "name": "rate_code" }` | `Quantity.unit/code` strings | Source/FHIR unit agreement 1,750/1,750; FHIR ETL trims both before writing |
| rate unit provenance | `{ "path": "(dosage.rate).ofType(Quantity).system", "name": "rate_system" }` | `Quantity.system` string | 1,750/1,750; MIMIC units system; support only |
| `amount` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value` decimal | 1,750/1,750; raw `decimal(32,6)`, alias `STRING`; parent does not consume amount |
| `amountuom` | `{ "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }`; optional `{ "path": "(dosage.dose).ofType(Quantity).code", "name": "amount_code" }` | `Quantity.unit/code` strings | Source/FHIR unit agreement 1,750/1,750; parent does not select amountuom |
| amount unit provenance | `{ "path": "(dosage.dose).ofType(Quantity).system", "name": "amount_system" }` | `Quantity.system` string | 1,750/1,750; support only |
| `patientweight` | **No FHIRPath**; no dosage weight element or populated supporting-information weight reference | Not representable | Source non-null 1,750/1,750; no field in the served dosage schema; affects only the identified norepinephrine/phenylephrine CASE branches |

For the child dependency output, `vaso_rate` is not a new FHIR field: it is
derived from `rate_value` and `rate_unit` using the source CASE. The parent
consumes the dependency's `vaso_rate`, not raw `rate_value`, and carries the
dependency's `starttime`, `endtime`, `icu_encounter_key`, and `patient_key`.

## Source/oracle checks and branch counts

The read-only DuckDB query over `mimiciv_icu.inputevents` returned 1,750 rows:

| itemid | rows | non-null fields (each field count) |
|---:|---:|---|
| 221653 | 44 | `subject_id`, `stay_id`, `linkorderid`, `rate`, `amount`, `starttime`, `endtime`, `rateuom`, `amountuom`, `patientweight`: 44/44 each |
| 221662 | 28 | the same ten fields: 28/28 each |
| 221289 | 36 | the same ten fields: 36/36 each |
| 221906 | 947 | the same ten fields: 947/947 each |
| 221749 | 625 | the same ten fields: 625/625 each |
| 222315 | 55 | the same ten fields: 55/55 each |
| 221986 | 15 | the same ten fields: 15/15 each |

The source rate units were `mcg/kg/min` for every target except vasopressin,
which was `units/hour`; amount units were `mg` for every target except
vasopressin, which was `units`. All seven source rates were non-NULL, so the
demo exercised only the Period effective branch. The exact CASE branch counts
were zero for `rateuom='mg/kg/min'`, zero for `rateuom='mcg/min'`, and zero for
`rateuom='units/min'`; in particular, norepinephrine's patientweight branch and
phenylephrine's denominator branch were both unexercised in this demo.

An equality join on `(item_code, stay_id, starttime, endtime)` paired all
1,750 source rows to all 1,750 served rows, with zero source-only or
FHIR-only rows and no duplicate coordinate keys on either side. Subject ids
agreed 1,750/1,750. Direct rate values agreed within `rtol=1e-6,
atol=1e-6` on 1,750/1,750 (138/1,750 float32-bit exact; maximum absolute
difference `8.685302734789957e-7`). Direct amount values agreed within the same
tolerance on 1,750/1,750 (494/1,750 float32-bit exact; maximum absolute
difference `7.773437488367563e-6`). Applying all seven source CASE expressions
to the oracle rate and comparing with the direct FHIR rate gave the same
1,750/1,750 within tolerance. Rate and amount units agreed exactly 1,750/1,750.

The parent manifest is `full_tuple_multiset` with no oracle natural key and
requires `icu_encounter_key` and `patient_key` support columns. Do not use the
opaque resource keys as the comparison key or as `stay_id`.

## Gaps and representability bounds

### `linkorderid`

This is **not representable**: the ICU ETL writes no inputevent identifier,
`orderid`, or `linkorderid` element. The authoritative all-resource probe found
`identifier.value` non-null on 0/56,535 and `supportingInformation.reference`
non-null on 0/56,535. The source has `linkorderid` non-null on all 1,750 rows,
but the parent query neither selects nor consumes it. It is therefore ancillary
to this parent interval overlay, although each child dependency must preserve
its declared output shape with typed NULL. Resource ids may be compared for
identity only; parsing, UUID regeneration, hardcoded lookup, or inversion to
`linkorderid` is forbidden.

### `patientweight`

This is **not representable**: no served FHIR element carries the per-row
`inputevents.patientweight`. It is not safe to derive from a Patient or another
weight observation because that would be an approximation of a row-specific
source denominator. The demo source had patientweight on all 1,750 rows, but the
surviving source unit discriminator showed zero affected rows: 0/947
norepinephrine `mg/kg/min` rows and 0/625 phenylephrine `mcg/min` rows. Thus the
measured demo loss reaches zero rows.

If full data has either branch, `rate_unit` identifies exactly the affected
rows. The faithful handling is a typed NULL for `vaso_rate` only on those rows,
not a raw-rate estimate and not a whole-column unrepresentable declaration.
For the parent, this can make one drug rate clinically NULL while the timing
boundaries remain representable; no whole-concept block is recommended from
this bounded, branch-identifiable loss. The later full comparison/judge must
bound any affected full-data rows.

### `starttime` on the rate-null effective branch

The rate-null ETL branch preserves `endtime` as `effectiveDateTime` but drops
`starttime`; no exact FHIR derivation exists. The surviving discriminator is
the absence of `rate_value`, so the affected rows are identifiable. The demo
has 0/1,750 such rows, while the complete ICU stream has 9,366 dateTime-valued
resources. On affected vasoactive rows the missing start reaches the parent's
`UNION DISTINCT` boundary set, `LEAD` ordering, interval grain, and containment
joins, so it is potentially essential to the parent temporal derivation. Do not
infer it from an opaque id; the full run must determine the affected count and
the judge must assess the bounded loss.

### Quantity precision

The direct Quantity paths are the faithful mappings, but served values are
`decimal(32,6)` while relational rates/amounts are FLOAT-like. The discarded
low-order bits are not recoverable by any FHIR query. This is a deterministic,
bounded numeric approximation, measured above, and must not be replaced by a
resource-id side channel or a guessed rounding rule. It does not alter demo
row inclusion or interval keys.

### Datetime normalization and unit trimming

FHIR datetime aliases contain an offset and must be cast directly to
`TIMESTAMP_NTZ`, preserving the serialized wall-clock value; cast each choice
variant before coalescing. The curated datetime note records that upstream
`TIMESTAMPTZ` can irreversibly normalize a New York DST-gap wall time. No such
disagreement occurred in this 1,750-row demo coordinate join, but any full-data
shift can affect the parent boundary overlay and cannot be recovered from the
resource id.

The ETL also applies `TRIM` to `rateuom` and `amountuom` before writing Quantity
unit/code. The demo had no padded units, so unit agreement was 1,750/1,750. A
future raw padded unit could be indistinguishable after serialization and could
change an exact source CASE comparison; recheck any full-data unit residual.

## Curated notes and provisional fragments

The established `MIMIC_NOTES.md` entries that changed this mapping were:

* **MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a UUID**:
  forced `stay_id` and subject support through Encounter/Patient identifier
  values and kept resource/reference keys as join-only strings.
* **`getResourceKey()` is type-prefixed; `Resource.id` is the bare UUID** and
  the opaque-id rule: required the type-prefixed support keys and prohibited
  recovering `orderid`, `linkorderid`, `patientweight`, or timestamps from ids.
* **Polymorphic fields mix datatypes across rows — COALESCE them**: required
  both effective variants and Period.end/dateTime coalescing.
* **Quantity.value ViewDefinition aliases materialize as VARCHAR** and
  **ICU MedicationAdministration Quantity values are served at decimal scale
  six**: required string-to-numeric casts and direct Quantity mapping.
* **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never TIMESTAMP**:
  required wall-clock parsing and cast-before-coalesce.
* **Encounter has three identifier systems — class discriminates none**:
  required the exact ICU identifier system rather than Encounter.class.
* **ICU MedicationAdministration omits inputevent linkorderid**: confirmed
  that linkorderid cannot be recovered and is not a valid resource-id mapping.

The fragments read as provisional leads were `MIMIC_NOTES.d/README.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `milrinone.md`,
`norepinephrine.md`, `phenylephrine.md`, `vasopressin.md`, `neuroblock.md`,
and `arb.md`. The ICU medication leads were independently verified against
this concept's Delta and DuckDB probes; they were not treated as established
evidence and no sibling fragment was edited. `nsaid.md`, `acei.md`, and
`antibiotic.md` do not exist in `MIMIC_NOTES.d/` and were not cited as read.
No fragment claim changed the exact seven code counts, paths, or types without
direct verification.

This concept appended four dataset-wide findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/vasoactive_agent.md`: absent
`patientweight`, unit trimming, one coding per MedicationAdministration, and
absence of served CodeSystem resources. No ViewDefinition, concept SQL, or
immutable attempt implementation artifact was authored.
