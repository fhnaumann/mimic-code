# FHIR prober mapping — `epinephrine`

**Concept:** `medication/epinephrine`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/epinephrine/source-analyst.md`  
**Probe date:** 2026-08-11  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Resource mapping and exact discriminator

`mimiciv_icu.inputevents` maps to the ICU `MedicationAdministration` resource
stream. The resource is generated one-for-one by
`/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql`.
The source filter `itemid = 221289` is carried by
`MedicationAdministration.medicationCodeableConcept.coding` as:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu
code   = "221289"
display = "Epinephrine"
```

The exact system plus exact string code is the discriminator. Do not use
`meta.profile` or the display. The authoritative Delta target had 36 coding
rows for 36 distinct `MedicationAdministration` keys. Across all
MedicationAdministration resources, the coding projection had 56,535 rows for
56,535 distinct resource keys; the ICU medication system had 20,404/20,404.
Thus the coding-per-resource ratio is **1.000** for both the target and the
complete stream, and this `forEach` does not multiply rows.

Use this constrained coding group:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221289')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The served Delta has no `CodeSystem` resource table (`src.read('CodeSystem')`
raises `No data found for resource type: CodeSystem`). The code is confirmed
from the served MedicationAdministration coding itself. The local ETL
terminology SQL, `mimic-fhir/sql/codesystem/cs-medication-icu.sql:10-15`, takes
the code and display from `mimiciv_icu.d_items` for rows with
`linksto='inputevents'`; the DuckDB dimension row is
`(221289, 'Epinephrine', 'inputevents')`.

## Canonical support ViewDefinitions

### MedicationAdministration

These are FHIRPath support columns. UUID/resource-reference keys remain strings
and are join columns only; they are not MIMIC integer identifiers.

```json
{
  "resource": "MedicationAdministration",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "medication_administration_id" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
        { "path": "context.getReferenceKey(Encounter)", "name": "encounter_id" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
        { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
        { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
        { "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" },
        { "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" },
        { "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" },
        { "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }
      ]
    },
    {
      "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='221289')",
      "column": [
        { "path": "code", "name": "item_code" },
        { "path": "system", "name": "code_system" },
        { "path": "display", "name": "code_display" }
      ]
    }
  ]
}
```

`context` is the FHIR R4 `MedicationAdministration.context` reference field in
the served schema; do not write `encounter.getReferenceKey(Encounter)` here.
The local ICU profile confirms `context 1..1`, `medication[x] only
CodeableConcept`, `effective[x] 1..1`, `dosage.dose 0..1`, and
`dosage.rateQuantity 0..1` in `SD_MimicMedicationAdministrationICU.fsh:7-31`.

### ICU Encounter identifier support

The source output's `stay_id` comes from the ICU Encounter identifier, not from
the Encounter UUID:

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "encounter_id" }
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

The ICU Encounter probe returned 140 rows, 140 distinct resource keys, and
140/140 non-null `stay_id_str` values. All 36 target administrations had a
non-null `context.getReferenceKey(Encounter)`, joined to an ICU Encounter, and
then to a non-null `stay_id_str` (36/36). The final output must use
`CAST(stay_id_str AS INTEGER) AS stay_id`; `getResourceKey()` and
`context.getReferenceKey(Encounter)` are UUID strings and must never be emitted
as `stay_id`.

`subject.getReferenceKey(Patient)` was non-null on all 36 target rows (36/36),
but no Patient join is required by the six-column source output.

## Source column → FHIRPath mapping

Final types below are the immutable oracle manifest types. A ViewDefinition
alias is often string-like even when its FHIR element is decimal or dateTime;
the implementer must cast to the manifest type in the final SQL.

| Source column / output | Canonical `{path, name}` | FHIR type | Target population / final type |
|---|---|---|---|
| `itemid` (filter only) | `{ "path": "code", "name": "item_code" }` inside the constrained medication-coding `forEach`; paired with `{ "path": "system", "name": "code_system" }` | `Coding.code` / `Coding.system`, strings | Exact system + code returned 36 rows / 36 resources; display `Epinephrine` 36/36; not emitted |
| resource key | `{ "path": "getResourceKey()", "name": "medication_administration_id" }` | MedicationAdministration resource key string | 36/36 non-null and 36 distinct; support only |
| `stay_id` | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_id" }` → `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key string, then `Identifier.value` string | 36/36 reference and identifier joins; final `CAST(stay_id_str AS INTEGER)` → `INTEGER` |
| source `subject_id` (not selected) | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `Reference(Patient)` key string | 36/36 non-null target support values; no output column |
| `linkorderid` | **No FHIRPath**; no usable `MedicationAdministration.identifier` is present | Not representable | Source DuckDB 36/36 non-null; served `identifier` non-empty on 0/56,535 resources; emit typed `CAST(NULL AS INTEGER)` if preserving the six-column output |
| `rate` → `vaso_rate` | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | `Quantity.value` decimal | 36/36 non-null; ViewDefinition alias `STRING`; final `CAST(rate_value AS FLOAT)` → `FLOAT` |
| `amount` → `vaso_amount` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value" }` | `Quantity.value` decimal | 36/36 non-null; ViewDefinition alias `STRING`; final `CAST(amount_value AS FLOAT)` → `FLOAT` |
| source `rateuom` (not selected) | `{ "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }` | `Quantity.unit` string | `mcg/kg/min` on 36/36; informational support only; no source unit filter/conversion |
| source `amountuom` (not selected) | `{ "path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit" }` | `Quantity.unit` string | `mg` on 36/36; informational support only; no source unit filter/conversion |
| `starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `effective[x]` = `Period.start`, dateTime | 36/36 non-null in target; alias `STRING`; final `TRY_CAST(... AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` |
| `endtime` (rate non-null branch) | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `effective[x]` = `Period.end`, dateTime | 36/36 non-null in target; alias `STRING`; final `TRY_CAST(... AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` |
| `endtime` (rate-null branch) | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effective[x]` = dateTime | 0/36 target rows; required for the general ICU stream; coalesce with Period.end after each string choice is cast to `TIMESTAMP_NTZ` |

The materialized ViewDefinition schema was:
`medadmin_key:string, patient_key:string, encounter_key:string,
effective_datetime:string, effective_period_start:string,
effective_period_end:string, amount_value:string, amount_unit:string,
rate_value:string, rate_unit:string, item_code:string, code_system:string,
code_display:string`. The canonical names in the table above use the more
explicit `medication_administration_id`, `patient_id`, and `encounter_id` for
support; the Pathling types and paths are unchanged.

## Effective, dosage, and schema counts

The exact constrained ViewDefinition probe over `MedicationAdministration`
returned the following total/non-null counts:

| Alias | Total | Non-null |
|---|---:|---:|
| `medication_administration_id` / resource key | 36 | 36 |
| `patient_id` | 36 | 36 |
| `encounter_id` | 36 | 36 |
| `item_code` | 36 | 36 |
| `code_system` | 36 | 36 |
| `code_display` | 36 | 36 |
| `effective_datetime` | 36 | 0 |
| `effective_period_start` | 36 | 36 |
| `effective_period_end` | 36 | 36 |
| `amount_value` | 36 | 36 |
| `amount_unit` | 36 | 36 |
| `rate_value` | 36 | 36 |
| `rate_unit` | 36 | 36 |

The raw served `MedicationAdministration` schema exposes
`effectiveDateTime:string`, `effectivePeriod.start/end:string`,
`dosage.dose.value:decimal(32,6)`, and
`dosage.rateQuantity.value:decimal(32,6)`. Across the full ICU medication
system (20,404 resources), the raw counts were: subject reference 20,404,
context reference 20,404, non-empty identifier 0, effectiveDateTime 9,366,
effectivePeriod 11,038, dose 20,404, and rateQuantity 11,038. The ETL branch is
therefore confirmed independently of the target code: non-null rate writes a
Period containing source start/end; null rate writes only source endtime as a
dateTime. A reusable view must project both effective variants even though the
epinephrine demo target is entirely Period-valued.

## Code confirmation and discriminator warrant

The complete coding `forEach` over the served Delta reported:

```text
system                                                                  coding rows  distinct resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-formulary-drug-cd 34205 34205
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu              20404 20404
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name              1624  1624
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-poe-iv             302   302
```

For the source literal lifted verbatim from the analyst, the per-code result
was:

```text
system                                                                  code    rows resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu          221289  36   36
```

`221289` occurred under no other medication coding system (0 rows). The
coding-per-resource ratio is `36 / 36 = 1.000` for the target and
`20,404 / 20,404 = 1.000` for the ICU stream. The warrant for using exact
system + code is that the served ETL writes the source `d_items.itemid` as the
coding code and the item dimension row has one global `itemid` with
`linksto='inputevents'`; no profile discriminator is needed or allowed.

## Cardinality, resource identity, and oracle checks

The ICU ETL creates the MedicationAdministration UUID from
`stay_id || '-' || orderid || '-' || itemid` at
`fhir_medication_administration_icu.sql:19-23`, then emits one resource for
each inputevent row. The raw MIMIC primary key is `(orderid, itemid)`
(`buildmimic/postgres/constraint.sql:162-167`). The source query does not
project `orderid`, so the source output has no declared key and
`linkorderid` is not a unique key.

On the demo DuckDB oracle, `inputevents WHERE itemid=221289` had 36 rows:
`stay_id`, `linkorderid`, `rate`, `amount`, `starttime`, and `endtime` were
each non-null 36/36; `orderid` had 36 distinct values; `(stay_id,starttime)`
had 36 distinct keys; `(linkorderid,starttime)` had 36 distinct keys; and
the six projected tuples had zero duplicates. The FHIR target had 36 distinct
resource keys and 36 distinct `(stay_id,starttime)` keys.

> **CORRECTION (2026-08-13, human — do not carry the demo result forward).**
> `(stay_id,starttime)` being unique on these 36 demo rows is a small-sample
> artefact. **It is not unique at full scale.** `oracle_manifest.py:99-131`
> emits a deterministic candidate order for these six columns — `1:(stay_id)`,
> `2:(linkorderid)`, `3:(stay_id,linkorderid)`, `4:(stay_id,starttime)`,
> `5:(stay_id,endtime)`, `6:(linkorderid,starttime)` — and the manifest records
> `key_probes: 6` for `epinephrine`, so probe 4 was tried on the full 24,470
> rows and **failed**. Compare `dopamine`, `dobutamine`, `vasopressin` and
> `milrinone`, all `key_probes: 4`: for them probe 4 succeeded, which is the
> only reason they keyed on `(stay_id,starttime)` and reached the judge while
> `epinephrine` and `norepinephrine` (both `key_probes: 6`) keyed on
> `linkorderid` and were auto-blocked.
>
> Concretely: the full data contains at least one stay with two concurrent
> epinephrine orders sharing a `starttime`, distinguishable in relational MIMIC
> only by `linkorderid`. Do not assume a clean representable key exists. If a
> future attempt needs one, `(stay_id,starttime,endtime)` is the only remaining
> representable candidate and its uniqueness is **untested** — the key search
> stops at first success, so it was never probed. Note that `phenylephrine`
> reports `key_probes: 11`, meaning it exhausted every candidate including the
> three-column ones and found nothing unique at all.
>
> The demo agreement figures below remain valid *as demo figures*. They are not
> full-scale evidence, and `attempt_0001` produced no usable full-scale diff:
> its comparison was void because the join keyed on the all-NULL
> `linkorderid` (`comparison.full.json` reports `only_oracle: 48,940` against
> `oracle_rows: 24,470`, which is arithmetically impossible and is a separate
> anchor-column bug in `compare_port_results.py:1168`, still open).

The exact DuckDB/FHIR join on `(stay_id,starttime)` paired 36/36 rows with no
oracle-only or FHIR-only rows. After parsing the offset-bearing FHIR strings as
wall-clock values with `TIMESTAMP_NTZ` semantics, agreement was:

| Output | Agreement |
|---|---:|
| `stay_id` through ICU Encounter identifier | 36/36 exact |
| `starttime` from Period.start | 36/36 exact |
| `endtime` from Period.end | 36/36 exact |
| `vaso_rate` after `FLOAT` cast | 0/36 bitwise exact; 36/36 within `1e-6`; max absolute difference `4.819223880792034e-7` |
| `vaso_amount` after `FLOAT` cast | 0/36 bitwise exact; 36/36 within `1e-6`; max absolute difference `4.965009689356092e-7` |
| `linkorderid` | no FHIR value/path; source 36/36 non-null |

The numeric loss is the served Quantity's six-decimal representation versus
the source FLOAT, not a different mapping. The source `TIMESTAMPTZ` ETL emits
offset-bearing strings; direct `TIMESTAMP_NTZ` casting preserves the MIMIC
wall-clock values. The shared datetime note still applies: upstream
TIMESTAMPTZ conversion can irreversibly normalize DST-gap times, although no
such mismatch occurred in this 36-row demo target.

The immutable full oracle manifest declares six output columns with types
`INTEGER, INTEGER, FLOAT, FLOAT, TIMESTAMP, TIMESTAMP`, comparison
`keyed_join`, key `(linkorderid,starttime)`, and full row count 24,470. That
manifest key is comparison metadata, not a FHIR resource key; because
`linkorderid` is absent from FHIR, it must be emitted as a typed NULL and is an
intrinsic representability gap rather than a substitute identifier.

## Gaps

* **`linkorderid`: not representable.** The ICU ETL writes no
  `MedicationAdministration.identifier`, `orderid`, or `linkorderid`. The
  resource UUID is opaque and cannot be inverted to `linkorderid`; do not use
  `getResourceKey()` as a numeric surrogate. Preserve the manifest shape with
  `CAST(NULL AS INTEGER)` and document the null-only divergence.
* **`starttime` for a rate-null inputevent: absent and not representable.** The
  dateTime branch contains only source `endtime`; it has no start element and
  no exact derivation for source `starttime`. The epinephrine demo has rate
  non-null 36/36, so this gap is not exercised by its target rows.
* **Full source precision of `rate` and `amount`: not representable but
  deterministically approximable.** Served Quantity values are decimal scale
  six. Direct FHIR values are the faithful mapping; the measured demo was
  within `1e-6` for 36/36 but bitwise exact for 0/36 for both numeric outputs.
  Do not introduce a unit conversion or heuristic.
* **DST-gap wall-clock source times: not exactly recoverable when present.**
  This is the existing dataset-wide ETL transformation documented in
  `MIMIC_NOTES.md`; `TIMESTAMP_NTZ` preserves the already-serialized FHIR wall
  time but cannot invert a prior `TIMESTAMPTZ` normalization. No target demo row
  exhibited it.

No source-selected column has an absent-but-derivable or safely approximable
replacement beyond the explicitly measured numeric approximation. `itemid` is
not an output column, but its exact value survives in the medication coding
used for the discriminator.

## Repository material read

Curated notes that changed the mapping decision:

* **MIMIC ids live in `identifier.value` as strings**: forced `stay_id` through
  the ICU Encounter identifier and kept resource/reference UUIDs join-only.
* **Encounter has three identifier systems — class discriminates none of them**:
  forced the `encounter-icu` identifier system for the `stay_id` support join,
  rather than filtering or joining on `Encounter.class`.
* **Polymorphic fields mix datatypes across rows**: required both effective
  variants and the Period.end/dateTime end-time coalesce.
* **FHIR datetimes carry an offset — cast to `TIMESTAMP_NTZ`, never `TIMESTAMP`**:
  determines the datetime conversion and preserves wall-clock values.
* **Quantity.value ViewDefinition aliases materialize as VARCHAR**: requires
  final numeric casts; the fresh schema probe measured raw decimal scale six.
* **`Observation.code.coding.code` is source itemid verbatim** and the coding
  policy: applied analogously only after directly probing this
  MedicationAdministration coding system; no terminology translation or
  `meta.profile` filter was used.
* **Raw NDJSON is stale**: the resource and code claims above came from Delta;
  local FSH/IG and ETL SQL were used only as structural/transformation support.

All existing provisional fragments were read: `README.md`, `crrt.md`,
`complete_blood_count.md`, `coagulation.md`, `cardiac_marker.md`,
`blood_differential.md`, `code_status.md`, `chemistry.md`, `dobutamine.md`, and
`dopamine.md`. The dobutamine/dopamine ICU inputevent hypotheses were treated as
leads and independently verified against the epinephrine target and complete
ICU stream; no other concept fragment was edited. New dataset-wide findings
were appended only to `MIMIC_NOTES.d/epinephrine.md`.

No implementation artifact or immutable attempt artifact was created.
