# FHIR prober mapping — `phenylephrine`

**Concept:** `medication/phenylephrine`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/phenylephrine/source-analyst.md`  
**Probe date:** 2026-08-13  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Resource, medication code, and discriminator

`mimiciv_icu.inputevents` maps to the ICU `MedicationAdministration` resource
stream. The served demo has 56,535 MedicationAdministration resources, of
which 20,404 carry the ICU medication coding system. The source filter
`itemid = 221749` is represented by the exact medication coding:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu
code   = "221749"
display = "Phenylephrine"
```

The DuckDB `d_items` lookup independently returned
`(221749, 'Phenylephrine', 'inputevents')`. The target coding projection
returned 625 rows for code `221749`, on 625 distinct resources. No target row
carried this code under another system. The discriminator is therefore
`Coding.system` plus exact `Coding.code`; do not use `meta.profile`, display,
or a terminology translation. The exact code is also safe within the ICU
system because `d_items.itemid` is a global key and the dimension row has
`linksto = 'inputevents'`.

Use this constrained coding group, rather than an unconstrained coding
projection:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221749')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The complete MedicationAdministration coding projection was 56,535 rows for
56,535 distinct resource keys: **1.000 coding per resource**. The ICU-system
projection was 20,404/20,404, also **1.000**. The phenylephrine constrained
projection was 625/625, **1.000**. Thus the constrained `forEach` does not
fan out this target.

The observed medication systems and row counts were:

| `medicationCodeableConcept.coding.system` | rows |
|---|---:|
| `.../mimic-medication-formulary-drug-cd` | 34,205 |
| `.../mimic-medication-icu` | 20,404 |
| `.../mimic-medication-name` | 1,624 |
| `.../mimic-medication-poe-iv` | 302 |

The exact source code count was `221749: 625` under the ICU system and
`221749: 0` under other observed medication systems in the target projection.
The local orchestration fixture `orchestration-new/tests/fixtures/fhir/case01/MedicationAdministration.ndjson`
contains generic RxNorm examples, not MIMIC phenylephrine data; it was not
used as authority. No authoritative phenylephrine NDJSON snapshot was found.
The Delta table, not stale raw snapshots, is the source of truth.

## Canonical support ViewDefinitions

### MedicationAdministration

The ICU resource uses the FHIR R4 field `context`, not `encounter`, for its
Encounter reference. Resource and reference keys below are opaque equality
join keys only.

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
      "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221749')",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "code_system" },
        { "path": "display", "name": "code_display" }
      ]
    }
  ]
}
```

All materialized ViewDefinition aliases in this probe were Spark `STRING`,
including Quantity values and effective date/time values. The encoded Delta
schema reports `dosage.dose.value` and `dosage.rateQuantity.value` as
`decimal(32,6)`. The implementer must cast numeric aliases to the manifest's
`FLOAT` and FHIR datetime aliases to `TIMESTAMP_NTZ` in the final SQL. The
rate path must use the `(dosage.rate).ofType(Quantity)` form; the served field
is encoded as `rateQuantity`.

### ICU Encounter

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

The demo has 637 Encounter resources, but only 140 populated
`encounter-icu` identifiers. All 140/140 ICU identifier values are non-null.
The phenylephrine target's `context.getReferenceKey(Encounter)` resolved to an
ICU Encounter and its `stay_id_str` on 625/625 rows. Emit
`CAST(stay_id_str AS INTEGER) AS stay_id`; never emit or parse the opaque
Encounter UUID.

The subject support path is:

```json
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
```

The demo has 100/100 Patient resources with a non-null patient identifier
value, and an equality join from the target's patient reference through that
key agreed with the source `subject_id` on 625/625 rows. If a subject id is
needed, use a separate Patient view:

```json
{ "path": "getResourceKey()", "name": "patient_key" }
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
```

`patient_key` and `encounter_key` are join-only UUID strings. They must not be
parsed, regenerated, hashed, hardcoded, or used as side channels for source
values.

## Source column → FHIRPath mapping

The final types in the last column are the phenylephrine manifest types. FHIR
element types and materialized alias types are shown separately where they
differ.

| Source column / output | Canonical FHIR extraction (`{path, name}`) | FHIR type | Probe result and target type |
|---|---|---|---|
| `itemid` (filter only) | In constrained coding `forEach`: `{ "path": "code", "name": "item_code" }`; also `{ "path": "system", "name": "code_system" }` and `{ "path": "display", "name": "code_display" }` | `Coding.code`, `Coding.system`, `Coding.display`: strings | Exact system/code/display 625/625; not emitted; discriminator is system + code |
| `stay_id` | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" }` → `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key string → `Identifier.value` string | Equality join and source agreement 625/625; final `CAST(stay_id_str AS INTEGER)` → `INTEGER` |
| `subject_id` (support only; not selected by source SQL) | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key string → `Identifier.value` string | Equality join to source subject id 625/625; final integer cast if emitted |
| `linkorderid` | **No FHIRPath; no `select.column`** | Not represented | Source 625/625 non-null; `MedicationAdministration.identifier.value` 0/625 and 0/20,404 ICU resources; typed `CAST(NULL AS INTEGER)` is the only honest output-preserving declaration |
| `rateuom` (branch support) | `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }`; optionally system/code with names `rate_system`/`rate_code` | `Quantity.unit`, `Quantity.system`, `Quantity.code`: strings | Target unit `mcg/kg/min` 625/625; unit system/code are MIMIC units and were populated 625/625; not a final source column |
| `rate` → `vaso_rate` | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value`: decimal; materialized alias `STRING` | 625/625 non-null; source/FHIR exact 8/625, within `1e-6` 625/625; final `CAST(rate_value AS FLOAT)` → `FLOAT` |
| `patientweight` (branch input) | **No FHIRPath**; no served dosage/supporting-information weight field | Not represented | Source 625/625 non-null; target has no weight element. Demo `rateuom='mcg/min'` rows: 0/625, so this branch is unexercised in demo. The source analysis notes one full-data `mcg/min` row; if confirmed, its conversion cannot be reproduced exactly |
| `amount` → `vaso_amount` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value`: decimal; materialized alias `STRING` | 625/625 non-null; source/FHIR exact 1/625, within `1e-6` 591/625 (max absolute difference about `5.63e-6`); final `CAST(amount_value AS FLOAT)` → `FLOAT` |
| `starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `effectivePeriod.start`: dateTime | Target Period.start 625/625; equality agreement with source wall time 625/625; materialized `STRING`, final `TIMESTAMP_NTZ` |
| `endtime` when `rate` non-null | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `effectivePeriod.end`: dateTime | Target Period.end 625/625; equality agreement 625/625; materialized `STRING`, final `TIMESTAMP_NTZ` |
| `endtime` when `rate` null | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effectiveDateTime`: dateTime | Target `effective_datetime` 0/625; required for the general ICU stream, where it was 9,366/20,404 and carries source endtime only |
| `orderid` (raw source identity, not selected) | **No FHIRPath for the source value**; `getResourceKey()` is only `{ "path": "getResourceKey()", "name": "medadmin_key" }` | Resource key string, opaque | ICU ETL uses orderid only inside opaque resource identity; do not invert it. The canonical six-column output does not emit orderid |

The source output manifest is
`INTEGER, INTEGER, FLOAT, FLOAT, TIMESTAMP, TIMESTAMP` for
`stay_id, linkorderid, vaso_rate, vaso_amount, starttime, endtime`.

## Effective choice and dosage counts

For the exact phenylephrine target, the Delta probe counted:

| Alias | Total | Non-null |
|---|---:|---:|
| `medadmin_key` | 625 | 625 |
| `patient_key` | 625 | 625 |
| `encounter_key` | 625 | 625 |
| `item_code` | 625 | 625 |
| `code_system` | 625 | 625 |
| `code_display` | 625 | 625 |
| `effective_datetime` | 625 | 0 |
| `effective_period_start` | 625 | 625 |
| `effective_period_end` | 625 | 625 |
| `rate_value` | 625 | 625 |
| `rate_unit` | 625 | 625 |
| `amount_value` | 625 | 625 |
| `amount_unit` | 625 | 625 |
| `identifier_value` | 625 | 0 |
| `supporting_reference` | 625 | 0 |

Across all ICU-coded MedicationAdministration resources, the corresponding
counts were Period.start/end 11,038/20,404, effectiveDateTime 9,366/20,404,
dosage dose 20,404/20,404, dosage rate 11,038/20,404, context reference
20,404/20,404, and non-empty identifier 0/20,404. The local ETL SQL confirms
the branch: non-null raw `rate` writes `effectivePeriod` from source
start/end; null raw `rate` writes only source endtime as
`effectiveDateTime`. Project both effective variants and coalesce them in the
derived SQL. For the source `starttime`, the dateTime branch is a genuine gap:
that branch retains endtime but discards starttime.

## DuckDB oracle checks

The demo DuckDB query `inputevents WHERE itemid=221749` returned 625 rows.
All nine inspected source fields were non-null on 625/625:
`stay_id`, `subject_id`, `linkorderid`, `rateuom`, `rate`, `patientweight`,
`amount`, `starttime`, and `endtime`. The only observed `rateuom` was
`mcg/kg/min` (625/625), so the source `CASE` used the ELSE/raw-rate branch on
all demo rows. There were 33 distinct stays, 137 distinct linkorderids, and
no duplicate `(stay_id,starttime,endtime)` tuples in this target.

An equality join using only represented values — ICU Encounter identifier,
Patient identifier, and Period start/end — paired FHIR to DuckDB 625/625 with
zero source-only or FHIR-only rows. This did not inspect or parse any resource
id. Agreement was:

| Check | Agreement |
|---|---:|
| stay id | 625/625 exact |
| subject id | 625/625 exact |
| starttime via Period.start | 625/625 exact |
| endtime via Period.end | 625/625 exact |
| item code | 625/625 exact |
| medication system | 625/625 exact |
| rate after FLOAT cast | 8/625 bitwise exact; 625/625 within `1e-6` |
| amount after FLOAT cast | 1/625 bitwise exact; 591/625 within `1e-6` |

The small numeric differences are the served six-decimal Quantity
representation. Preserve the direct FHIR Quantity values; do not use an
opaque resource key to recover source precision.

## Gaps and representability

### `linkorderid` — not representable, ancillary here

The ICU MedicationAdministration ETL does not serialize inputevent
`linkorderid`, `orderid`, or an inputevent identifier. The served target has no
non-empty `MedicationAdministration.identifier` (0/625; 0/20,404 in the ICU
stream), and no supporting reference containing it. This is **not representable**:
there is no FHIRPath or measured approximation. Never parse, regenerate,
brute-force, hardcode, or otherwise use the opaque MedicationAdministration id
as a side channel. A typed NULL `INTEGER` preserves the manifest shape.

For this concept, the loss is ancillary to row inclusion and the source
stream's six-column output has no declared key (`full_tuple_multiset`). It does
change each output tuple and can matter to a downstream consumer needing
inputevent linkage, but it does not select rows or control the rate branch.

### `patientweight` — not representable and potentially essential

No served FHIR element carries source `inputevents.patientweight`: the target
has no dosage weight field and no populated supporting-information weight
reference. This is **not representable**, not absent-but-derivable, and no
approximation was measured. The demo has patientweight on 625/625 source rows,
but zero `mcg/min` rows, so the missing value does not affect the demo
`vaso_rate`. The source analysis reports one `mcg/min` row in the full source;
that must be confirmed during the full comparison.

If any full-data row has `rateuom = 'mcg/min'`, patientweight changes the
clinically meaningful `vaso_rate = rate / patientweight`. It can therefore
change a derived output, making the loss potentially essential for the whole
concept rather than an ancillary NULL column. Recommend whole-concept blocking
to the judge if the full run confirms an affected row; this prober does not
make the terminal decision. The `rateQuantity.unit` value survives and
identifies the branch, but it does not supply the missing denominator.

### `starttime` on rate-null rows — absent and not representable

The rate-null FHIR branch stores only source `endtime` as
`effectiveDateTime`; no FHIR element carries source `starttime` for those
resources. This branch is not exercised by phenylephrine's 625-row demo
target, where all rates are non-null, but both effective variants remain
mandatory in a reusable view.

### Quantity precision and datetime normalization

The source FLOAT precision is not fully retained by the served six-decimal
Quantity values. This is an upstream representation loss; use the direct
Quantity paths and the manifest FLOAT casts. FHIR datetime strings include an
offset; cast to `TIMESTAMP_NTZ` to preserve the serialized MIMIC wall clock,
not to an offset-aware `TIMESTAMP`. Upstream TIMESTAMPTZ conversion can also
irreversibly normalize DST-gap wall times; do not try to undo it with an
opaque resource id.

## Notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

* **MIMIC ids live in `identifier.value` as strings**: forced the ICU
  Encounter identifier for `stay_id`, separate Patient identifier support for
  `subject_id`, final integer casts, and join-only opaque resource/reference
  keys.
* **Polymorphic fields mix datatypes across rows — COALESCE them**: required
  both `effective` variants and Period.end/dateTime handling.
* **Quantity.value ViewDefinition aliases materialize as VARCHAR**: required
  numeric casts for the rate and amount aliases.
* **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ**: determines safe
  datetime handling and preserves wall-clock values.
* **Code systems are proprietary / no terminology translation**: required
  taking the exact system and code from served Delta and using `221749`
  literally.
* **Raw `Mimic*.ndjson.gz` snapshots are stale**: made the Delta warehouse,
  not raw snapshots, authoritative.

The provisional fragments read were `MIMIC_NOTES.d/README.md`,
`MIMIC_NOTES.d/dopamine.md`, `dobutamine.md`, `epinephrine.md`, `milrinone.md`,
`norepinephrine.md`, and `neuroblock.md`. Their ICU medication hypotheses
were treated as leads and independently verified against the authoritative
Delta target and complete ICU stream; no sibling fragment was cited as proof
and no sibling fragment was edited.

No implementation file or immutable attempt artifact was authored.

---

## CORRECTION — recorded by a human after attempt 0001, 2026-08-13

**The blocking recommendation above for `patientweight` is withdrawn.** The
finding is right; the recommendation drawn from it is not, and it was taken.

`patientweight` is genuinely not representable — that stands. What does not
follow is whole-concept blocking, because the branch that needs it is
identifiable from what FHIR *does* carry. `fhir_medication_administration_icu.sql:95-97`
writes `rateuom` to `dosage.rateQuantity.unit`, this file already records it as
served 625/625, and `phenylephrine.sql`'s own comment says one row in the full
table is `mcg/min`. So the port knows precisely which rows it cannot compute,
and it is one row in 193,260.

The correct handling, per `LOOP_CONTRACT.md` "The rule is per *value*, not per
column":

```sql
CASE WHEN rate_unit = 'mcg/min' THEN CAST(NULL AS FLOAT) ELSE rate_value END
```

Attempt 0001 emitted the raw `rate` on that row instead, which is the
estimate-instead-of-an-absence failure at row scale: it manufactures a
`differing_conflict` where a `differing_null_only` was available. Do not
declare `vaso_rate` in `unrepresentable.json` — the declaration is verified as
100% NULL and this column is not. State the row-level gap in the handback.

Also do not read attempt 0001's comparison artifact as evidence about the port.
Its 190,872 conflicts and 0.00% identical were comparator artifacts on the
unkeyed path — exact float comparison against Pathling's `decimal(32,6)`, and a
pairing degraded to `stay_id` alone by the 100%-NULL `linkorderid`. Both are
fixed in `compare_port_results.py` as of 2026-08-13. Measured directly against
the demo oracle, attempt 0001 matched `(stay_id, starttime, endtime)` on 625/625
rows with every value inside tolerance.
