# FHIR prober mapping — `norepinephrine_equivalent_dose`

**Concept:** `medication/norepinephrine_equivalent_dose`  
**Corrected attempt:** `attempt_0002`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/norepinephrine_equivalent_dose/source-analyst.md`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (read-only DuckDB)  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2

This replaces the invalidated attempt-0001 mapping. The runner's dependency
preprocessing uses the published/export shape, not the dependency attempt
shape. `strip_mimic_ids("vasoactive_agent", ...)` drops `stay_id` because the
outer projection also carries `icu_encounter_key`. The actual embedded runner
preprocessed the completed dependency and exposed exactly:

```text
starttime, endtime, dopamine, epinephrine, norepinephrine, phenylephrine,
vasopressin, dobutamine, milrinone, icu_encounter_key, patient_key
```

It did **not** expose `stay_id`. Published types were `timestamp_ntz` for the
two times, `float` for the seven rate columns, and `string` for the two opaque
keys. The corrected target therefore needs a real `encounter_icu` view and the
exact join:

```sql
vasoactive_agent.icu_encounter_key = encounter_icu.encounter_key
```

`stay_id` is recovered only from the ICU Encounter identifier value and is
cast to `INTEGER`; no resource id is parsed, regenerated, or used as a source
value.

## Source table → MIMIC-on-FHIR resource

| Source table/role | FHIR resource or published relation | Mapping decision |
|---|---|---|
| `mimiciv_derived.vasoactive_agent` | published derived relation `vasoactive_agent` (not a FHIR resource) | Consume the completed dependency. It is the interval overlay and must not be rederived from raw FHIR. Its published shape has no `stay_id`. |
| Transitive `mimiciv_icu.inputevents` | `MedicationAdministration` | One ICU medication administration per source inputevent in the served demo; medication itemid is `medication.coding`, context is the ICU Encounter reference, effective time is `effective[x]`, and rate/amount are dosage Quantities. |
| Transitive `mimiciv_icu.icustays` | ICU `Encounter` | Select with `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; its resource key is the dependency join key and its identifier value carries `stay_id`. |
| Transitive `mimiciv_hosp.patients` | `Patient` | `MedicationAdministration.subject` and `Encounter.subject` carry the opaque Patient reference key. A separate Patient view is unnecessary for this target. |

The authoritative Delta contains 637 Encounter resources, 140 ICU Encounter
identifier rows, 56,535 MedicationAdministration resources, 20,404 ICU-coded
MedicationAdministration resources, and 100 Patient resources.

## Corrected ICU Encounter ViewDefinition mapping

The implementer must author a ViewDefinition with filename/label/name
`encounter_icu`, resource `Encounter`, and this canonical column shape:

```json
{ "path": "getResourceKey()", "name": "encounter_key" }
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
```

inside the flat `column` group, plus:

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    { "path": "system", "name": "stay_system" },
    { "path": "value", "name": "stay_id_str" }
  ]
}
```

| Output alias | Canonical `{path, name}` | FHIR type | Probe count |
|---|---|---|---:|
| `encounter_key` | `{ "path": "getResourceKey()", "name": "encounter_key" }` | opaque type-prefixed `Encounter` resource-key string | 140/140 non-null and distinct |
| `patient_key` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque type-prefixed `Patient` reference-key string | 140/140 non-null |
| `stay_system` | `{ "path": "system", "name": "stay_system" }` under the ICU identifier `forEach` | `Identifier.system` URI string | 140/140 non-null; all exact ICU URI |
| `stay_id_str` | `{ "path": "value", "name": "stay_id_str" }` under the ICU identifier `forEach` | `Identifier.value` string | 140/140 non-null; 140 distinct values |

The 140 FHIR `stay_id_str` values had exact set agreement with the 140
`mimiciv_icu.icustays.stay_id` values in the DuckDB oracle. The corrected
published-dependency join matched all 1,874/1,874 dependency interval rows;
all 1,874 had a matching `stay_id_str`. The join covered 52 distinct ICU
Encounter keys in the demo dependency output. The source-side cast is
`CAST(encounter_icu.stay_id_str AS INTEGER) AS stay_id`.

The ICU identifier system, not `Encounter.class`, is the discriminator. The
served demo has 275 hosp, 140 ICU, and 222 ED identifier rows, and `class`
does not separate those streams.

## Transitive MedicationAdministration ViewDefinition mapping

The target itself names no coded literal, but the completed
`vasoactive_agent` dependency has seven exact child itemids. The reusable
MedicationAdministration view uses resource `MedicationAdministration` and
the following flat columns:

| Source/role | Canonical `{path, name}` | FHIR type | Selected seven-code count |
|---|---|---|---:|
| administration identity | `{ "path": "getResourceKey()", "name": "medadmin_key" }` | opaque type-prefixed `MedicationAdministration` key string | 1,750/1,750 non-null; 1,750 distinct |
| patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque `Patient` reference-key string | 1,750/1,750 non-null |
| ICU context | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" }` | opaque `Encounter` reference-key string | 1,750/1,750 non-null |
| rate value | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value` decimal; materialized ViewDefinition alias `STRING` | 1,750/1,750 non-null |
| rate unit | `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }` | `Quantity.unit` string | 1,750/1,750 non-null |
| rate system | `{ "path": "(dosage.rate).ofType(Quantity).system", "name": "rate_system" }` | `Quantity.system` URI string | 1,750/1,750 non-null |
| rate code | `{ "path": "(dosage.rate).ofType(Quantity).code", "name": "rate_code" }` | `Quantity.code` string | 1,750/1,750 non-null |
| amount value | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value` decimal; materialized ViewDefinition alias `STRING` | 1,750/1,750 non-null |
| amount unit | `{ "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }` | `Quantity.unit` string | 1,750/1,750 non-null |
| amount system | `{ "path": "(dosage.dose).ofType(Quantity).system", "name": "amount_system" }` | `Quantity.system` URI string | 1,750/1,750 non-null |
| amount code | `{ "path": "(dosage.dose).ofType(Quantity).code", "name": "amount_code" }` | `Quantity.code` string | 1,750/1,750 non-null |
| rate-null effective branch | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effective[x] = dateTime`; materialized alias `STRING` | 0/1,750 non-null in selected rows; 9,366/20,404 in complete ICU stream |
| rate-bearing effective start | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` dateTime; materialized alias `STRING` | 1,750/1,750; 11,038/20,404 in complete ICU stream |
| rate-bearing effective end | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `Period.end` dateTime; materialized alias `STRING` | 1,750/1,750; 11,038/20,404 in complete ICU stream |

For the medication coding group, use the exact system-constrained repeating
projection and these aliases:

```json
{ "path": "code", "name": "item_code" }
{ "path": "system", "name": "code_system" }
{ "path": "display", "name": "code_display" }
```

with `forEach` constrained to
`medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and (code='221653' or code='221662' or code='221289' or code='221906' or code='221749' or code='222315' or code='221986'))`.
These three aliases have FHIR types `Coding.code` string, `Coding.system` URI
string, and `Coding.display` string; each was populated on 1,750/1,750
selected coding rows. The materialized aliases are Spark `STRING`.

`MedicationAdministration.context`, not `encounter`, is the populated ICU
Encounter reference. The raw schema has `context` and no `encounter` field.

## Exact transitive code set and discriminator

The target SQL has no itemid or other coded filter of its own. Its transitive
dependency uses these exact source itemids:

| Dependency rate column | Code | Served display | `code.coding.system` | coding rows | distinct resources | codings/resource |
|---|---:|---|---|---:|---:|---:|
| `dobutamine` (boundary-only) | `221653` | Dobutamine | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu` | 44 | 44 | 1.000 |
| `dopamine` | `221662` | Dopamine | same ICU system | 28 | 28 | 1.000 |
| `epinephrine` | `221289` | Epinephrine | same ICU system | 36 | 36 | 1.000 |
| `norepinephrine` | `221906` | Norepinephrine | same ICU system | 947 | 947 | 1.000 |
| `phenylephrine` | `221749` | Phenylephrine | same ICU system | 625 | 625 | 1.000 |
| `vasopressin` | `222315` | Vasopressin | same ICU system | 55 | 55 | 1.000 |
| `milrinone` (boundary-only) | `221986` | Milrinone | same ICU system | 15 | 15 | 1.000 |

The exact projection total was 1,750 coding rows over 1,750 distinct
MedicationAdministration resources. The complete unfiltered coding system
counts were: formulary-drug `34,205/34,205` (ratio 1.000), ICU
`20,404/20,404` (1.000), medication-name `1,624/1,624` (1.000), and POE-IV
`302/302` (1.000). Each exact code above was observed only under the ICU
system. The discriminator is `code_system + item_code`, never `meta.profile`.
The exact codes remain safe because `mimiciv_icu.d_items.itemid` is a global
primary key and each listed item has `linksto = 'inputevents'`; code alone is
therefore sufficient within the established ICU system, but the system must
still be projected and filtered.

No terminology translation is used. `CodeSystem` resources are absent from
the authoritative Delta; the served MedicationAdministration coding and the
DuckDB `d_items` dimension are the authorities.

## Published dependency column mappings

These are the columns the target actually consumes after runner publication.
The FHIR paths are transitive through the completed `vasoactive_agent`
dependency; the target must read the dependency and must not repeat extraction
from MedicationAdministration.

| Source/dependency column | Canonical FHIR mapping | FHIR/materialized type | Demo coverage and target handling |
|---|---|---|---|
| `stay_id` | **Not in published `vasoactive_agent`**; `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` on `encounter_icu` | FHIR `Identifier.value` string; final `stay_id` `INTEGER` | 140/140 Encounter values and 1,874/1,874 dependency joins; cast only after the exact opaque-key join |
| `starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` (rate-bearing child branch), carried through published `vasoactive_agent.starttime` | FHIR dateTime alias `STRING`; published dependency `TIMESTAMP_NTZ`; manifest `TIMESTAMP` | published 1,874/1,874 non-null; target selects it unchanged apart from manifest-compatible typing |
| `endtime` | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }`, or `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` on the rate-null branch, carried through published `vasoactive_agent.endtime` | FHIR dateTime aliases `STRING`; published dependency `TIMESTAMP_NTZ`; manifest `TIMESTAMP` | published 1,874/1,874 non-null; target selects it unchanged apart from manifest-compatible typing |
| `norepinephrine` | code `221906` + `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` and unit discriminator `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }` | raw Quantity decimal `decimal(32,6)`, ViewDefinition alias `STRING`, published normalized rate `FLOAT` | published 1,089/1,874 non-null; consume `vasoactive_agent.norepinephrine` |
| `epinephrine` | code `221289`; same rate value/unit paths | raw decimal `decimal(32,6)` → alias `STRING` → published `FLOAT` | published 56/1,874 non-null; consume dependency |
| `phenylephrine` | code `221749`; same rate value/unit paths | raw decimal `decimal(32,6)` → alias `STRING` → published `FLOAT` | published 742/1,874 non-null; consume dependency |
| `dopamine` | code `221662`; same rate value/unit paths | raw decimal `decimal(32,6)` → alias `STRING` → published `FLOAT` | published 32/1,874 non-null; consume dependency |
| `vasopressin` | code `222315`; same rate value/unit paths | raw decimal `decimal(32,6)` → alias `STRING` → published `FLOAT` | published 418/1,874 non-null; consume dependency |
| `icu_encounter_key` | `{ "path": "getResourceKey()", "name": "encounter_key" }` on `encounter_icu` | opaque type-prefixed key `VARCHAR`/Spark `STRING` | published 1,874/1,874 non-null; preserve verbatim and join on equality |
| `patient_key` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` on `encounter_icu` (also present on MedicationAdministration) | opaque type-prefixed key `VARCHAR`/Spark `STRING` | published 1,874/1,874 non-null; preserve verbatim |
| `norepinephrine_equivalent_dose` | no direct FHIRPath; computed from the five published rate columns | final manifest `DECIMAL(38,4)` | source predicate retains 1,748/1,874 dependency rows; formula is non-null on 1,748/1,748 retained rows |

The dependency's other published rates are retained because dobutamine and
milrinone affect upstream interval boundaries, even though they are not terms
in this target formula. The target must preserve duplicate dependency rows;
the demo dependency has 1,874 rows and 1,746 distinct
`(stay_id,starttime,endtime)` coordinates, so no deduplication is permitted.

## Required casts and temporal handling

`Identifier.value`, all resource/reference keys, and all ViewDefinition
aliases are strings. Cast only the identifier to the manifest integer at the
final source-value boundary; preserve resource keys with their `Type/uuid`
prefix. Cast FHIR datetime aliases to `TIMESTAMP_NTZ`, not offset-aware
`TIMESTAMP`, before using them as dependency times. Cast Quantity value
aliases to numeric before the upstream dependency's rate CASE; the target
consumes the published `FLOAT` rates and casts/rounds its final sum to
`DECIMAL(38,4)`.

## Representability gaps and bounds

The prober records these for the implementer and later judge; it does not make
a terminal decision.

### Published `stay_id` omission — absent from dependency but exactly derivable

`stay_id` is absent from the published dependency solely because the runner's
export rule strips an identifier when its paired resource key is projected.
It is not a FHIR coverage loss: `encounter_icu.stay_id_str` is the exact
`Encounter.identifier.value`, and the surviving `icu_encounter_key` identifies
the Encounter to join. The observed bound is 1,874/1,874 dependency rows
matched and 140/140 ICU identifiers exact against `icustays.stay_id`. This is
not a reason to parse `Encounter.id` or any resource key.

### `inputevents.patientweight` — not representable, branch-bounded

The ICU MedicationAdministration resource has no patientweight field or
supporting reference. The source patientweight was non-null for all 1,750
selected child rows in the demo. The surviving `rate_unit` path identifies
the affected normalization branches: `mg/kg/min` for norepinephrine,
`mcg/min` for phenylephrine, and `units/min` for vasopressin. Those branches
were exercised on 0/947, 0/625, and 0/55 selected rows respectively in the
demo, so the measured demo loss reaches zero rows. At full scale, a missing
weight can make a normalized dependency rate NULL; if no other selected
pressor is active in that interval, it can change target row inclusion and
the dose. The discriminator survives, so this is a row-level gap: the
upstream dependency should emit a typed NULL only on the identifiable affected
rows rather than estimate weight or use an opaque id. Whole-concept blocking
is not recommended from the demo bound; the full run must measure propagation.

### `inputevents.linkorderid` — not representable but ancillary here

No FHIRPath carries `linkorderid`: selected `MedicationAdministration`
identifier and supporting reference projections were both 0/1,750. Resource
ids are opaque and cannot recover it. This target does not consume
`linkorderid`, so the loss reaches zero target inclusion, key, grouping, time,
or dose rows. Child concepts that expose it must use a typed NULL, never a
resource-id surrogate.

### Rate-null child `starttime` — not representable on an identifiable branch

For a rate-null ICU administration, the ETL writes source `endtime` as
`effectiveDateTime` and does not write source `starttime`. The surviving
discriminator is `rate_value` at
`(dosage.rate).ofType(Quantity).value`; the selected seven-code demo had
0/1,750 such rows, while the complete ICU stream had 9,366 dateTime-valued
resources. The missing start can affect the upstream boundary set and thus
interval rows, so full-data propagation must be measured. Do not infer it
from an opaque resource id.

### Quantity precision — approximable, not exact

Served raw Quantity values are `decimal(32,6)` and ViewDefinition aliases are
strings. Against the DuckDB source, selected child rate values agreed within
absolute `1e-6` on 1,750/1,750 rows; amount values agreed within
`rtol=1e-6, atol=1e-6` on 1,750/1,750. Low-order source precision is absent
from FHIR. Direct extraction plus the dependency's numeric casts is the
measured approximation; do not use resource identity to reconstruct the
discarded bits. The demo bound changed no row inclusion or interval grain.

### ICU datetime normalization — not exactly representable at DST gaps

The upstream ICU MedicationAdministration ETL casts effective endpoints
through `TIMESTAMPTZ`, so a nonexistent New York spring-forward wall time can
be written one hour later. `TIMESTAMP_NTZ` preserves the served wall clock but
cannot recover the original. A shifted endpoint can alter interval boundaries
and dose row pairing at full scale; the original wall time is not in any FHIR
element and must not be inferred from identity. The demo selected seven-code
child rows had exact Period start/end agreement on 1,750/1,750.

## Notes/fragments read and findings ownership

Established `MIMIC_NOTES.md` entries that changed this mapping were:

* **MIMIC ids live in `identifier.value` as STRINGs** — forced `stay_id` to
  come from the ICU Encounter identifier and kept resource keys separate.
* **`getResourceKey()` is type-prefixed; `Resource.id` is the bare UUID** —
  required verbatim `encounter_key`, `icu_encounter_key`, and `patient_key`,
  and prohibited all id inversion.
* **Polymorphic fields mix datatypes across rows — COALESCE them** — required
  both effective variants in the upstream mapping.
* **Quantity.value aliases materialize as VARCHAR** and **ICU
  MedicationAdministration Quantity values are decimal scale six** —
  required string aliases followed by numeric casts and bounded precision.
* **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ** — required the
  wall-clock cast for dependency times.
* **Encounter has three identifier systems — class discriminates none** —
  required the exact ICU identifier system and `stay_system` predicate.
* **Essential source loss blocks a whole derived concept** — required
  branch-level bounds for patientweight and the rate-null timing loss instead
  of silently estimating or publishing a partial derivation.
* **ICU MedicationAdministration omits inputevent linkorderid** — confirmed
  the ancillary gap is irrelevant to this target.

The provisional fragments read were `MIMIC_NOTES.d/README.md`,
`norepinephrine_equivalent_dose.md`, `vasoactive_agent.md`,
`norepinephrine.md`, `phenylephrine.md`, `dobutamine.md`, `epinephrine.md`,
`dopamine.md`, `vasopressin.md`, `milrinone.md`, and `neuroblock.md`. They were
treated as leads, not evidence. Their common MedicationAdministration claims
about `context`, one coding per resource, effective variants, Quantity paths,
decimal scale, absent patientweight, and absent linkorderid were checked
against the authoritative Delta in this rerun. No sibling fragment was
edited.

No genuinely new dataset-wide finding was established in this rerun, so
`MIMIC_NOTES.d/norepinephrine_equivalent_dose.md` was not appended and
`MIMIC_NOTES.md` was not edited. No attempt ViewDefinition, candidate SQL, or
attempt artifact was authored.
