# FHIR prober mapping — `norepinephrine`

**Concept:** `medication/norepinephrine`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/norepinephrine/source-analyst.md`  
**Probe date:** 2026-08-13  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Resource and source-table mapping

`mimiciv_icu.inputevents` maps to the ICU
`MedicationAdministration` resource stream. The upstream ETL creates one
resource per inputevent row from `mimic-fhir/sql/fhir_medication_administration_icu.sql`.
The source output itself has no relational join, but the FHIR-side recovery of
`stay_id` uses the `MedicationAdministration.context` reference to the ICU
`Encounter` stream. `mimiciv_icu.icustays` is the relational source represented
by that ICU Encounter support stream; it is not an additional source relation in
the canonical norepinephrine SQL. The Patient resource is support for the
subject reference and is not needed by the six source output columns.

The authoritative Delta contained 56,535 `MedicationAdministration` resources,
including 20,404 ICU resources, 637 `Encounter` resources (140 ICU identifier
rows), and 100 `Patient` resources.

## Exact code discriminator

The source filter is the literal `itemid = 221906`. In served Delta it is the
exact medication coding:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu
code   = "221906"
display = "Norepinephrine"
```

Use the exact system plus exact string code. Do not use `meta.profile` or the
display. The source dimension row is `(221906, 'Norepinephrine',
'inputevents')`, so the code is an ICU inputevent item, not a hospital
medication stream. In the complete served medication coding projection the
system counts were:

| `code.coding.system` | coding rows | distinct resources |
|---|---:|---:|
| `.../mimic-medication-formulary-drug-cd` | 34,205 | 34,205 |
| `.../mimic-medication-icu` | 20,404 | 20,404 |
| `.../mimic-medication-name` | 1,624 | 1,624 |
| `.../mimic-medication-poe-iv` | 302 | 302 |

Code `221906` occurred as 947 rows / 947 resources under the ICU system and
0 rows under every other served coding system. Thus the target coding
ratio is `947 / 947 = 1.000`, and the complete ICU-system ratio is
`20,404 / 20,404 = 1.000`. A constrained coding `forEach` is therefore
safe and should be used to avoid unrelated medication streams:

```json
{ "path": "code", "name": "item_code" }
{ "path": "system", "name": "code_system" }
{ "path": "display", "name": "code_display" }
```

These three columns are inside:

```text
medication.ofType(CodeableConcept).coding.where(
  system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
  and code='221906'
)
```

The served Delta has one coding per ICU MedicationAdministration resource;
the exact item code and system, not a profile, are the discriminator.

## Canonical support columns and identifiers

Resource and reference keys are opaque strings used only for equality joins.
They must not be parsed or used to recover `stay_id`, `subject_id`,
`orderid`, `linkorderid`, timestamps, or dosage values.

### MedicationAdministration support paths

| Purpose | Canonical `{path, name}` | FHIR type | Probe result |
|---|---|---|---|
| Resource identity / one-row support key | `{ "path": "getResourceKey()", "name": "medication_administration_id" }` | resource key string | 947/947 non-null and 947 distinct target keys |
| Subject reference join | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `Reference(Patient)` key string | 947/947 non-null |
| ICU Encounter reference join | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_id" }` | `Reference(Encounter)` key string | 947/947 non-null |

The field is `context`, not `encounter`, on this served
`MedicationAdministration` schema. A reference value has the type-prefixed
form `Patient/<opaque-key>` or `Encounter/<opaque-key>`; equality with the
corresponding resource `getResourceKey()` is the permitted operation.

### Subject and Encounter identifier paths

| Source identifier | Canonical `{path, name}` | FHIR type | Final output handling |
|---|---|---|---|
| source `subject_id` support | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` on `Patient` | `Identifier.value` string | cast to `INTEGER` only if an output is required; not a norepinephrine output |
| source `stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` on `Encounter` | `Identifier.value` string | `CAST(stay_id_str AS INTEGER)` → manifest `INTEGER` |

The ICU Encounter support projection is keyed by
`{ "path": "getResourceKey()", "name": "encounter_id" }` and iterates
`identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')`
for `system` and `value`. It returned 140 rows / 140 distinct Encounters,
with `stay_id_str` non-null on 140/140. Every target administration resolved
through `context.getReferenceKey(Encounter)` to an ICU identifier: 947/947.
The Patient support projection returned 100 rows / 100 distinct Patients,
with `subject_id_str` non-null on 100/100; every target subject reference
resolved and agreed with the source subject identifier on 947/947 paired rows.

Do not emit `getResourceKey()` or `context.getReferenceKey(Encounter)` as
`stay_id`; those are UUID-like join keys, not MIMIC identifiers.

## Source column → FHIRPath mapping

The final types are the oracle manifest types. Pathling materialized the
ViewDefinition aliases below as `STRING` for this resource, even where the
FHIR element is decimal or dateTime. The implementer must cast the aliases in
the final SQL; this file does not author that SQL.

| Source column / output | Canonical `{path, name}` | FHIR type | Target population / final type |
|---|---|---|---|
| `itemid` filter | `{ "path": "code", "name": "item_code" }` inside constrained `medication.ofType(CodeableConcept).coding` `forEach`; paired with `{ "path": "system", "name": "code_system" }` | `Coding.code` / `Coding.system`, strings | exact system + code: 947/947; not emitted |
| `stay_id` | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_id" }` → ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | Reference key string, then `Identifier.value` string | 947/947 resolved; final `INTEGER` |
| source `subject_id` support | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | Reference key string, then `Identifier.value` string | 947/947 resolved and source agreement; not emitted |
| `linkorderid` | **No FHIRPath**; `MedicationAdministration.identifier` is absent | not representable | source 947/947 non-null; preserve output shape as typed `NULL` → manifest `INTEGER` |
| `rate` → `vaso_rate` input | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value` decimal | 947/947; materialized alias `STRING`, final `FLOAT` |
| `rateuom` / unit discriminator | `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }` | `Quantity.unit` string | source `mcg/kg/min` and FHIR `mcg/kg/min`: 947/947; support only, not selected |
| rate unit system/code support | `{ "path": "(dosage.rate).ofType(Quantity).system", "name": "rate_system" }` and `{ "path": "(dosage.rate).ofType(Quantity).code", "name": "rate_code" }` | `Quantity.system` / `Quantity.code` strings | ETL writes the MIMIC units system/code; source SQL does not select them |
| `patientweight` | **No FHIRPath**; no dosage/supporting-information element carries it | not represented | source 947/947 non-null; target demo has no `mg/kg/min` branch, but the missing value can affect `vaso_rate` if that branch occurs |
| `vaso_rate` derived result | no single direct FHIR path; derive from `rate_value` and `rate_unit` using the source CASE where its discriminator is represented | output `FLOAT` | demo source formula vs FHIR rate: 1/947 bitwise exact, 947/947 within `1e-6`; see precision gap |
| `amount` → `vaso_amount` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value` decimal | 947/947; materialized alias `STRING`, final `FLOAT` |
| `amountuom` support | `{ "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }` | `Quantity.unit` string | source/FHIR unit `mg`: 947/947; source SQL does not select or transform it |
| dose unit system/code support | `{ "path": "(dosage.dose).ofType(Quantity).system", "name": "amount_system" }` and `{ "path": "(dosage.dose).ofType(Quantity).code", "name": "amount_code" }` | `Quantity.system` / `Quantity.code` strings | informational; source SQL copies only amount |
| `starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `effective[x] = Period.start`, dateTime | target 947/947; alias `STRING`, direct `TRY_CAST(... AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` |
| `endtime` for rate non-null | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `effective[x] = Period.end`, dateTime | target 947/947; direct `TIMESTAMP_NTZ` cast → manifest `TIMESTAMP` |
| `endtime` for rate-null | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effective[x] = dateTime` | target 0/947; required for the general ICU stream; coalesce with Period.end after each string variant is cast to `TIMESTAMP_NTZ` |

For this target, all 947 source rows have `rate` non-null and therefore use
the Period branch. In the complete ICU stream the corresponding counts are
9,366 dateTime resources and 11,038 Period resources (11,038 Period starts,
ends, and rate quantities), so both effective variants are required in a
reusable mapping. The ETL writes Period from source start/end when `rate IS
NOT NULL`, otherwise it writes only dateTime from source `endtime`.

## Nulls, multiplicity, datatypes, and timestamps

The exact constrained target ViewDefinition returned 947 rows and 947
distinct resource keys. Rows/non-null counts were:

| Alias | total | non-null |
|---|---:|---:|
| `medadmin_key` | 947 | 947 |
| `patient_key` | 947 | 947 |
| `encounter_key` | 947 | 947 |
| `item_code` / `code_system` / `code_display` | 947 | 947 each |
| `effective_datetime` | 947 | 0 |
| `effective_period_start` / `effective_period_end` | 947 | 947 each |
| `rate_value` / `rate_unit` | 947 | 947 each |
| `amount_value` / `amount_unit` | 947 | 947 each |

The raw encoded Delta schema reports `dosage.dose.value` and
`dosage.rateQuantity.value` as `decimal(32,6)`. The ViewDefinition aliases
`amount_value` and `rate_value` are string-like and need a final numeric cast.
The source DuckDB `FLOAT` values have more precision than the served six-place
FHIR decimal representation.

FHIR datetime aliases are offset-bearing strings. Use direct
`TIMESTAMP_NTZ`/`TRY_CAST(... AS TIMESTAMP_NTZ)` semantics, and cast each
choice variant before coalescing. Do not cast to timezone-aware `TIMESTAMP` or
parse the offset as an instant: the MIMIC datetimes are de-identified wall-clock
values. The demo target comparison found starttime exact on 947/947 and
endtime exact on 947/947 after the direct wall-clock cast. The existing
dataset-wide DST-gap note still applies: an upstream New York `TIMESTAMPTZ`
normalization can make a source 02:xx wall time irrecoverable as 03:xx.

## Source-vs-served oracle checks

Read-only DuckDB source query `inputevents WHERE itemid=221906` returned:

| Source column/check | total | non-null / count |
|---|---:|---:|
| qualifying rows | 947 | 947 |
| `stay_id` | 947 | 947 |
| `linkorderid` | 947 | 947 |
| `rate` | 947 | 947 |
| `amount` | 947 | 947 |
| `starttime` / `endtime` | 947 | 947 each |
| `patientweight` | 947 | 947 |
| `rateuom` | 947 | 947 |
| exact `rateuom='mg/kg/min'` | 947 | **0** |
| exact `rateuom='mg/kg/min' AND patientweight=1` | 947 | **0** |

All source target rows use `rateuom='mcg/kg/min'`; there are no null rate,
amount, patientweight, or selected timestamp values. The source had 184
distinct `linkorderid` values but 947 distinct `(linkorderid,starttime)` keys,
947 distinct `(stay_id,starttime)` keys, and 947 distinct
`(stay_id,starttime,endtime)` keys in the demo. The source primary key
`(orderid,itemid)` was also unique for the 947 target rows (947 distinct
`orderid` values), but `orderid` is not selected by the concept and must not be
recovered from a FHIR id.

The FHIR-to-source clinical join on `stay_id,starttime` paired 947/947 rows
with no source-only or candidate-only rows and no duplicate clinical keys on
either side. Agreement was:

| Output/check | exact | total | additional result |
|---|---:|---:|---|
| `stay_id` through ICU Encounter identifier | 947 | 947 | exact identifier join |
| `subject_id` support through Patient identifier | 947 | 947 | exact identifier join |
| `starttime` | 947 | 947 | direct `TIMESTAMP_NTZ` wall-clock comparison |
| `endtime` | 947 | 947 | direct `TIMESTAMP_NTZ` wall-clock comparison |
| source-derived `vaso_rate` vs FHIR `rate_value` | 1 | 947 | 947/947 within `1e-6`; max absolute difference `5.189590454035553e-7` |
| `vaso_amount` vs FHIR `amount_value` | 2 | 947 | 947/947 within `1e-6`; max absolute difference `9.073486317845436e-7` |
| source/FHIR rate unit | 947 | 947 | `mcg/kg/min` ↔ `mcg/kg/min` |
| source/FHIR amount unit | 947 | 947 | `mg` ↔ `mg` |

The numeric residual is the served `decimal(32,6)` representation versus
source `FLOAT`, not a different FHIR path or a unit conversion.

## Gaps and essentiality

These are representability findings for the later comparator/judge; this
prober does not make a terminal accept or block decision.

### `linkorderid`: not representable and potentially essential

The ICU ETL writes no `MedicationAdministration.identifier`, `orderid`, or
`linkorderid`. Raw Delta probing found identifier arrays populated on 0/56,535
MedicationAdministration resources, including 0/947 target resources; the
target `supportingInformation` field was also populated on 0/56,535 resources.
The resource id is opaque and cannot be parsed, regenerated, brute-forced, or
used as a semantic witness for `linkorderid`. No alternate FHIR element carries
the value. Emit a typed NULL `INTEGER` if preserving the six-column shape.

This is not merely an ancillary missing label: `linkorderid` is explicitly in
the source output, distinguishes source order linkage, and is the immutable
full manifest comparison key component `(linkorderid,starttime)` for
`norepinephrine` (manifest row count 336,000). Its loss can change keyed row
matching and downstream linkage, so it is potentially whole-concept
essential; the later equivalence judge must assess it rather than silently
substituting the opaque resource key.

### `patientweight`: not exactly representable; target-specific branch unexercised

No `MedicationAdministration.dosage` or other served FHIR field carries the
source per-row `inputevents.patientweight`; the demo source has 947/947
non-null values, while the exact norepinephrine target has 0/947 rows in the
`mg/kg/min` branch and therefore 0/947 rows where `patientweight=1` could
change the source CASE. A separately observed patient weight would be a
heuristic from another stream, not an exact recovery of the source operation,
and was not used or measured here.

For this demo target, `rate_unit='mcg/kg/min'` means the source-derived
`vaso_rate` is the raw rate and the omission is nonessential. If full data
contains exact `rateuom='mg/kg/min'` rows, absent patientweight can change the
clinically meaningful `vaso_rate` (including the special exact-weight-1
branch), making the loss essential for those rows. Recheck the full target
before any semantic conclusion.

### `starttime` on rate-null rows: absent and not representable

The dateTime effective branch contains only source `endtime`; it has no FHIR
element carrying source `starttime`. This is a temporal loss that can affect
interval meaning and downstream temporal logic. It was not exercised by the
demo target because `rate` was non-null on 947/947 rows and Period.start was
present on 947/947. Both effective variants must nevertheless be projected.

### Quantity precision: not exactly representable, deterministically approximable

The FHIR Quantity values are served at decimal scale six. Directly using the
FHIR quantity is the faithful mapping; rounding/reconstructing source FLOAT
values is not an exact inversion. In the demo, the direct FHIR values were
within `1e-6` for 947/947 rate-derived values and 947/947 amount values, with
only 1/947 and 2/947 bitwise exact after FLOAT casts. This is a measured
bounded approximation, not a reason to invent another dosage path. Numeric
precision is clinically meaningful but does not alter demo row inclusion or
keys; the later comparator handles the declared numeric tolerance.

### Datetime normalization: not exactly representable when a DST gap occurs

The curated `MIMIC_NOTES.md` datetime entry establishes that the upstream ETL
casts ICU MedicationAdministration endpoints through `TIMESTAMPTZ`, which can
normalize a nonexistent New York spring-forward 02:xx wall time to 03:xx.
Direct `TIMESTAMP_NTZ` casting preserves the served wall time but cannot recover
the original. The demo target had 947/947 exact start and end times, so this
gap was not observed in the target probe. If present at full scale, it is
temporal and potentially essential for interval ordering; do not use a
resource id to recover it.

## Notes and fragments read

The mapping decisions changed because of these curated `MIMIC_NOTES.md`
entries:

* **MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a
  UUID**: forced `stay_id` and subject support through identifier values and
  kept reference/resource keys join-only.
* **Polymorphic fields mix datatypes across rows — COALESCE them**: required
  both `effective.ofType(dateTime)` and `effective.ofType(Period)` variants.
* **Quantity.value ViewDefinition aliases materialize as VARCHAR**: required
  final numeric casts; raw Quantity values are `decimal(32,6)`.
* **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never TIMESTAMP**:
  required wall-clock parsing and cast-before-coalesce.
* **Encounter has three identifier systems — class discriminates none**:
  required the ICU `encounter-icu` identifier system for `stay_id`.
* **Essential source loss blocks the whole derived concept** and the opaque
  resource-id policy: prevented using the MedicationAdministration UUID as a
  surrogate for linkorderid or patientweight.
* **Raw `Mimic*.ndjson.gz` files are stale**: all code, null, and multiplicity
  observations above came from Delta; ETL SQL was used only to explain the
  served transformation.

All existing `mimic-iv/concepts_fhir/MIMIC_NOTES.d/*.md` fragments and
`MIMIC_NOTES.d/README.md` were read, including the provisional ICU medication
leads in `dobutamine.md`, `dopamine.md`, `epinephrine.md`, and `milrinone.md`.
They were treated as leads and independently verified against the norepinephrine
Delta target. The other fragments concerned observations, procedures,
encounters, labs, and medications and did not change this mapping. No other
concept fragment was edited.

## Probe artifact and ownership

No ViewDefinition, concept SQL, implementation artifact, or immutable attempt
artifact was authored. This reusable mapping is
`mimic-iv/concepts_fhir/carryover/norepinephrine/fhir-prober.md` and must be
recorded with:

```text
mimic_utils carryover-record norepinephrine --stage fhir-prober
```
