# FHIR mapping: `medication/antibiotic`

**Source analysis:** `mimic-iv/concepts_fhir/carryover/antibiotic/source-analyst.md`  
**Source SQL:** `mimic-iv/concepts/medication/antibiotic.sql`  
**Probe date:** 2026-08-08  
**Authoritative FHIR data:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

This is a medication-name classifier. It has no itemid or ICD code set. The
FHIR-side discriminator is the exact medication-name identifier system plus
the source SQL's case-insensitive substring predicate. The source output named
`antibiotic` is the original `prescriptions.drug` string; the SQL's integer
`abx.antibiotic` CASE result is only an internal filter flag.

## Resource graph

`mimiciv_hosp.prescriptions` is represented by pharmacy-backed
`MedicationRequest` resources, plus referenced `Medication` resources.
There are two request-to-drug branches and both are required:

1. **Direct branch:** `MedicationRequest.medicationReference` resolves
   directly to a name-bearing `Medication`.
2. **Medication-mix branch:** the request reference resolves to a mix
   `Medication`; each repeated `Medication.ingredient.itemReference` resolves
   to a name-bearing component `Medication`.

The final query must expand the two branches with `UNION ALL`. Do not use
`DISTINCT`: the mix ingredient references preserve source-row multiplicity.
The request has one row per `pharmacy_id`, while a multi-drug pharmacy group
has one ingredient per source prescription row.

The request's `subject` joins to `Patient`; its `encounter` joins to the
hospital `Encounter`. ICU assignment uses an ICU `Encounter` whose
`partOf` points to that hospital Encounter, then applies the source half-open
time predicate against ICU `period`: `[period.start, period.end)`.

## Canonical ViewDefinition mappings

The snippets use the `select[].column[]` and `select[].forEach` structure from
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
The UUID/reference columns below are join-only support columns.

### MedicationRequest

```json
{
  "resource": "MedicationRequest",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "medication_request_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" },
        { "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" },
        { "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" },
        { "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }
      ]
    },
    {
      "forEach": "dosageInstruction.route.coding",
      "column": [
        { "path": "code", "name": "route_code" },
        { "path": "system", "name": "route_system" },
        { "path": "display", "name": "route_display" }
      ]
    }
  ]
}
```

The pharmacy identifier is a support discriminator, not an output column.
Require `pharmacy_id_str IS NOT NULL`; this selects the prescription-backed
request stream and excludes POE-only `MedicationRequest` rows, which use
`medicationCodeableConcept` rather than `medicationReference`.

### Name-bearing Medication: direct and ingredient target

```json
{
  "resource": "Medication",
  "select": [
    { "column": [
      { "path": "getResourceKey()", "name": "medication_key" }
    ] },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name')",
      "column": [
        { "path": "system", "name": "drug_system" },
        { "path": "value", "name": "drug_name" }
      ]
    }
  ]
}
```

The source `drug` is `drug_name`, not `Medication.code.coding.code`. The
direct branch joins `mr.medication_key = medication_name.medication_key`.
The mix branch joins `mr.medication_key = medication_mix.mix_key`, then
`medication_mix.ingredient_medication_key = medication_name.medication_key`.
Apply every source drug-name predicate to `LOWER(drug_name)` in both branches.

### Medication mix and ingredients

```json
{
  "resource": "Medication",
  "select": [
    { "column": [
      { "path": "getResourceKey()", "name": "mix_key" }
    ] },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-mix')",
      "column": [
        { "path": "system", "name": "mix_system" },
        { "path": "value", "name": "mix_identifier" }
      ]
    },
    {
      "forEach": "ingredient",
      "column": [
        { "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }
      ]
    }
  ]
}
```

The `mix_identifier` is useful to establish the branch but is not the source
drug. Keep the repeated ingredient rows; a combined identifier/ingredient
view has the mix identifier repeated once per ingredient, which is expected.
Alternatively, materialise the identifier and ingredient groups separately.

### Patient and hospital Encounter identifiers

```json
{
  "resource": "Patient",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "patient_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
    ]
  }]
}
```

```json
{
  "resource": "Encounter",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "encounter_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
    ]
  }]
}
```

Join request `patient_key` and `encounter_key` to the resource keys above.
Filter the hospital Encounter view with `hadm_id_str IS NOT NULL`; do not use
`Encounter.class`.

### ICU Encounter and temporal assignment

```json
{
  "resource": "Encounter",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "icu_encounter_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "icu_patient_key" },
      { "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
      { "path": "period.start", "name": "intime_str" },
      { "path": "period.end", "name": "outtime_str" }
    ]
  }]
}
```

`icustays.hadm_id` is represented by `hospital_encounter_key` through
`Encounter.partOf`; the ICU Encounter itself carries `stay_id_str`, not a
hospital identifier. Join
`icu.hospital_encounter_key = mr.encounter_key`, and require
`TRY_CAST(mr.starttime_str AS TIMESTAMP_NTZ) >= TRY_CAST(icu.intime_str AS TIMESTAMP_NTZ)`
and `< TRY_CAST(icu.outtime_str AS TIMESTAMP_NTZ)`. This is the FHIR form of
`pr.hadm_id = ie.hadm_id AND pr.starttime >= ie.intime AND pr.starttime < ie.outtime`.
The patient reference can also be checked against `mr.patient_key`.

## Source-column mapping and types

`identifier.value` and Pathling ViewDefinition aliases for FHIR dateTime are
strings. They are not the final oracle types. The implementer must cast numeric
MIMIC identifiers to `INTEGER`, medication/route strings to bounded
`VARCHAR(255)`, and dateTime strings with `TRY_CAST(... AS TIMESTAMP_NTZ)` to
the manifest's `TIMESTAMP` output type. `TIMESTAMP_NTZ` is required by the
existing `MIMIC_NOTES.md` datetime entry; timezone-converting `TIMESTAMP` is
wrong for these de-identified wall-clock values.

| Source table.column | FHIRPath mapping (`{path, name}`) | FHIR/logical type | Materialized type | Final output/type |
|---|---|---|---|---|
| `prescriptions.pharmacy_id` (support) | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" }` | `Identifier.value` string | `string` | support-only `VARCHAR` |
| `prescriptions.drug`, direct | `{ "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" }` then name Medication `{ "path": "value", "name": "drug_name" }` | `Reference` UUID then string | `string` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.drug`, mix ingredient | `{ "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }` then name Medication `{ "path": "value", "name": "drug_name" }` | repeated `Reference` UUID then string | `string` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.route` | `{ "path": "code", "name": "route_code" }` within `forEach: "dosageInstruction.route.coding"` | `CodeableConcept.coding.code` string | `string` | `CAST(route_code AS VARCHAR(255))` → `VARCHAR` |
| route system (discriminator) | `{ "path": "system", "name": "route_system" }` within the same `forEach` | `uri` string | `string` | filter only; do not emit unless required |
| `prescriptions.starttime` | `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | `Period.start` `dateTime` | `string` | `TRY_CAST(starttime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `prescriptions.stoptime` | `{ "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }` | `Period.end` `dateTime` | `string` | `TRY_CAST(stoptime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `prescriptions.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` joined to Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference` UUID plus `Identifier.value` string | `string` | `CAST(subject_id_str AS INTEGER)` → `INTEGER` |
| `prescriptions.hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` joined to hospital Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Reference` UUID plus `Identifier.value` string | `string` | `CAST(hadm_id_str AS INTEGER)` → `INTEGER` |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` string | `string` | `CAST(stay_id_str AS INTEGER)` → `INTEGER`, nullable left join |
| `icustays.hadm_id` | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }` joined to the request/hospital Encounter key | `Reference` UUID | `string` | join-only; final `hadm_id` comes from hospital identifier |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_str" }` | `Period.start` `dateTime` | `string` | `TIMESTAMP_NTZ` for temporal predicate |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime_str" }` | `Period.end` `dateTime` | `string` | `TIMESTAMP_NTZ` for temporal predicate |
| output `antibiotic` | resolved name Medication `{ "path": "value", "name": "drug_name" }` | string | `string` | bounded `VARCHAR(255)` |

The resource keys (`getResourceKey()` and `getReferenceKey(...)`) are UUID
join keys. They must not be emitted as `subject_id`, `hadm_id`, or `stay_id`.

## Delta cardinality and population probes

All counts below were obtained by materialising the paths above and running
`count(*)` versus `count(column)` in Spark. Counts are demo-warehouse counts,
not full-data claims.

| Probe/view | Rows | Non-null observations |
|---|---:|---|
| `MedicationRequest` | 17,552 | `patient_key` 17,552; `encounter_key` 17,552; pharmacy identifier 15,225; medication reference 15,225; validity start 14,574; validity end 14,574 |
| name-bearing `Medication` | 1,480 | name identifier system/value 1,480/1,480; one name identifier per resource |
| medication-mix identifier-only view | 314 | mix system/value 314/314; one mix identifier per resource |
| medication-mix ingredient view | 634 | ingredient reference 634/634 across 314 mix resources |
| `Medication.code.coding` on direct/component Medication | 1,480 | code/system 1,480/1,480; display 0/1,480 |
| `MedicationRequest.dosageInstruction.route.coding` | 15,219 | route code/system 15,219/15,219; display 0/15,219; one route coding per coded request |
| `Patient` patient identifier | 100 | identifier value 100/100 |
| `Encounter` all identifier systems | 637 | hospital 275, ICU 140, ED 222; each identifier value populated |
| ICU `Encounter` targeted view | 140 | ICU identifier, `partOf`, `period.start`, and `period.end` all 140/140 |

The mix ingredient multiplicity is 310 resources with 2 ingredients, 2 with 3,
and 2 with 4: 634 references / 314 mix resources = **2.019 references per
mix resource**. The request branches are 12,382 direct requests and 2,843 mix
requests; the expanded rows are 12,382 direct plus 5,705 mix ingredients.
Thus 15,225 pharmacy requests expand to 18,087 source-row-equivalent drug
rows. The direct/component name identifier ratio is 1,480/1,480 = **1.000**;
the mix identifier ratio is 314/314 = **1.000**; route codings per coded
request are 15,219/15,219 = **1.000**.

`Medication.code.coding` is not the antibiotic discriminator. Its systems
were 1,402 NDC, 72 formulary-drug-code, and 6 medication-name rows, one coding
per code-bearing Medication, with `display` null on all 1,480 rows. Route
coding `display` is also null on all 15,219 rows. Mix resources have no single
medication code. Filter and join on the observed systems and codes, never on
display text.

## Systems, discriminators, and literal confirmation

The observed systems are:

- medication-name identifier:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name`;
- medication-mix identifier:
  `http://mimic.mit.edu/fhir/mimic/identifier/medication-mix`;
- medication route coding:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-route`;
- Patient identifier:
  `http://mimic.mit.edu/fhir/mimic/identifier/patient`;
- hospital Encounter identifier:
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`;
- ICU Encounter identifier:
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`.

The discriminator is `system` plus exact code/value where a coding or
identifier is projected. `meta.profile` is not used. The direct/mix split is
also warranted by the reference target: a name-bearing Medication has the
name identifier; a mix Medication has the medication-mix identifier and
ingredient references. The source SQL does not name a formal FHIR code set;
its name fragments and route/type literals below are lifted verbatim.

### Route/type and exclusion literals

The source route-code exclusion is `route NOT IN ('OU', 'OS', 'OD', 'AU',
'AS', 'AD', 'TP')`. Source DuckDB and FHIR route-coding counts were identical:

| Literal | Source rows | FHIR route-code rows |
|---|---:|---:|
| `OU` | 0 | 0 |
| `OS` | 1 | 1 |
| `OD` | 0 | 0 |
| `AU` | 0 | 0 |
| `AS` | 0 | 0 |
| `AD` | 0 | 0 |
| `TP` | 157 | 157 |

The route substring exclusions had source/FHIR counts `%ear%` = 5
(`RIGHT EAR` 2, `LEFT EAR` 2, `BOTH EARS` 1) and `%eye%` = 52
(`BOTH EYES` 39, `LEFT EYE` 11, `RIGHT EYE` 2). The drug-name exclusion
counts were `%cream%` = 32, `%desensitization%` = 0, `%ophth oint%` = 2,
and `%gel%` = 118. These values are all present in the FHIR name strings or
route codes and are therefore directly filterable.

The source `drug_type NOT IN ('BASE')` literal was confirmed against the
oracle: 3,677 source rows have `drug_type='BASE'`, but zero rows matching any
antibiotic fragment had `drug_type='BASE'` in the demo (944 fragment-hit rows
were `MAIN`; no `ADDITIVE` fragment hits). FHIR has no `drug_type` path. This
filter is therefore not exactly representable even though it is neutral on
the demo antibiotic rows.

### Antibiotic name fragments, in source order

Each count is `source DuckDB raw prescription rows / expanded FHIR rows`
matching that one `LOWER(drug) LIKE '%fragment%'` predicate. Counts are not
disjoint because the source predicates are OR'ed and some strings match more
than one fragment. Duplicate source literals are intentionally retained:
`septra` occurs twice and `trimethoprim` occurs twice.

```text
adoxa=0/0; ala-tet=0/0; alodox=0/0; amikacin=0/0; amikin=0/0; amoxicill=6/6; amphotericin=0/0; anidulafungin=0/0; ancef=0/0; clavulanate=0/0; ampicillin=14/14; augmentin=0/0; avelox=0/0; avidoxy=0/0; azactam=0/0; azithromycin=23/23; aztreonam=1/1; axetil=0/0; bactocill=0/0; bactrim=0/0; bactroban=0/0; bethkis=0/0; biaxin=0/0; bicillin l-a=0/0; cayston=0/0
cefazolin=49/49; cedax=0/0; cefoxitin=0/0; ceftazidime=14/14; cefaclor=0/0; cefadroxil=0/0; cefdinir=0/0; cefditoren=0/0; cefepime=82/82; cefotan=0/0; cefotetan=0/0; cefotaxime=0/0; ceftaroline=0/0; cefpodoxime=1/1; cefpirome=0/0; cefprozil=0/0; ceftibuten=0/0; ceftin=0/0; ceftriaxone=58/58; cefuroxime=0/0; cephalexin=3/3; cephalothin=0/0; cephapririn=0/0; chloramphenicol=0/0; cipro=88/88; ciprofloxacin=88/88; claforan=0/0; clarithromycin=3/3; cleocin=0/0; clindamycin=7/7
cubicin=0/0; dicloxacillin=0/0; dirithromycin=0/0; doryx=0/0; doxycy=6/6; duricef=0/0; dynacin=0/0; ery-tab=0/0; eryped=0/0; eryc=0/0; erythrocin=0/0; erythromycin=11/11; factive=0/0; flagyl=46/46; fortaz=0/0; furadantin=0/0; garamycin=0/0; gentamicin=2/2; kanamycin=0/0; keflex=0/0; kefzol=0/0; ketek=0/0; levaquin=0/0; levofloxacin=33/33; lincocin=0/0; linezolid=2/2; macrobid=1/1; macrodantin=0/0; maxipime=0/0; mefoxin=0/0; metronidazole=59/59; meropenem=43/43; methicillin=0/0; minocin=0/0; minocycline=0/0
monodox=0/0; monurol=0/0; morgidox=0/0; moxatag=0/0; moxifloxacin=1/1; mupirocin=19/19; myrac=0/0; nafcillin=0/0; neomycin=36/36; nicazel doxy 30=0/0; nitrofurantoin=1/1; norfloxacin=0/0; noroxin=0/0; ocudox=0/0; ofloxacin=121/121; omnicef=0/0; oracea=0/0; oraxyl=0/0; oxacillin=0/0; pc pen vk=0/0; pce dispertab=0/0; panixine=0/0; pediazole=0/0; penicillin=0/0; periostat=0/0; pfizerpen=0/0; piperacillin=59/59; tazobactam=59/59; primsol=0/0; proquin=0/0; raniclor=0/0; rifadin=0/0; rifampin=0/0; rocephin=0/0; smz-tmp=0/0; septra=0/0; septra ds=0/0; septra=0/0
solodyn=0/0; spectracef=0/0; streptomycin=0/0; sulfadiazine=0/0; sulfamethoxazole=3/3; trimethoprim=25/25; sulfatrim=0/0; sulfisoxazole=0/0; suprax=0/0; synercid=0/0; tazicef=0/0; tetracycline=0/0; timentin=0/0; tobramycin=7/7; trimethoprim=25/25; unasyn=0/0; vancocin=0/0; vancomycin=291/291; vantin=0/0; vibativ=0/0; vibra-tabs=0/0; vibramycin=0/0; zinacef=0/0; zithromax=0/0; zosyn=0/0; zyvox=0/0
```

The OR of the name fragments matches 944 raw source rows and 944 expanded
FHIR rows. After the route/name exclusions and the source `drug_type` filter,
the oracle has 903 antibiotic rows (903 pharmacy groups; 41 distinct drug
strings). The FHIR-side representable filters also produce 903 rows; the
demo equality is expected because no fragment-hit source row is `BASE`.

## Oracle checks and ETL transformations

The following cheap source/FHIR comparisons were run:

- All 631 distinct source drug strings equal the 631 distinct FHIR name
  identifier values.
- Expanded `(pharmacy_id, drug, route)` multiplicity is exact: 18,087 source
  rows versus 18,087 FHIR rows, 18,087 tuple groups, zero mismatched groups.
- The representable antibiotic filter is exact on the demo for 903 rows before
  ICU expansion: subject/hospital admission/name/route/pharmacy support values
  all agree row-for-row.
- The source temporal output has 903 rows: 439 without an ICU stay and 464
  with one. The FHIR temporal query has 903 rows: 470 without a stay and 433
  with one. The 31 source ICU assignments that are absent from FHIR are all
  among the 48 source antibiotic rows whose individual interval has
  `starttime > stoptime`; the source `stay_id` value is therefore not
  recoverable from the request.
- Source antibiotic validity status is 855 valid and 48 invalid, with no
  incomplete rows in the demo. FHIR validity start/end are populated for the
  855 valid rows and absent for the 48 invalid rows. Full output tuples agree
  for 855/903 rows; the remaining 48 have unavailable start/end, and 31 of
  those also have unavailable temporal ICU assignment. Do not substitute
  `authoredOn`.

The relevant ETL transformations are:

- `mimic-fhir/sql/medication/medication_prescriptions.sql:19-54` chooses
  Medication code by NDC, formulary code, then drug name, while preserving the
  original drug text in the name identifier.
- `mimic-fhir/sql/medication/medication_mix.sql:21-35,80-84` creates one mix
  Medication per multi-row pharmacy group and preserves component references;
  `drug_type` only orders those ingredients.
- `mimic-fhir/sql/fhir_medication_request.sql:12-37` groups requests by
  `pharmacy_id`; `:172-177` emits `dispenseRequest.validityPeriod` only when
  both coalesced request times exist and start is no later than stop. The
  request's grouped times are not a per-ingredient time store.
- The existing `MIMIC_NOTES.md` datetime entry records that the upstream
  TIMESTAMPTZ cast can normalize DST-gap wall times. Use `TIMESTAMP_NTZ` to
  preserve the served FHIR value; the original wall time is unrecoverable if
  the ETL already rewrote it.

## Gaps

### Absent and not representable: `prescriptions.drug_type`

No FHIR element carries `drug_type`. The mix ingredient order is not a typed
field and cannot exactly distinguish `BASE` from `MAIN`/`ADDITIVE` for an
arbitrary resource. The demo has 3,677 BASE rows overall but zero BASE rows
matching the antibiotic fragments, so this gap is invisible in the demo
classifier result; it must not be treated as a proof that the filter can be
omitted on full data. No approximation is used.

### Absent and not representable: invalid prescription times

The ETL drops `dispenseRequest.validityPeriod` for invalid or incomplete
grouped intervals. The 48 demo antibiotic rows with invalid source intervals
cannot recover `starttime` or `stoptime`; `authoredOn` is a request-entry time,
not either source endpoint. Since temporal ICU assignment needs source
`starttime`, 31 of those rows also lose their source ICU `stay_id` assignment.
These are coverage/ETL gaps, not a reason to invent a time or use a heuristic.

### Potential inherited transformation gap: DST normalization

The served FHIR endpoint may contain an already-normalized DST-gap endpoint,
as documented in `MIMIC_NOTES.md`. No query can invert that ETL operation. The
demo antibiotic rows with available validity times had exact timestamp
agreement; any full-data DST-gap conflicts should be classified using the
existing dataset-level note rather than “fixed” with timezone conversion.

No gap was found for drug-name strings, direct/mix branch identity, ingredient
multiplicity, route codes, Patient IDs, hospital admission IDs, or ICU IDs and
period bounds when the validity start exists.

## Shared-note change

The existing `MIMIC_NOTES.md` entry **“Prescription Medication.code prefers
NDC/formulary; the source drug name is in an identifier”** was updated to make
the absent `prescriptions.drug_type` explicit. That entry changed the mapping
decision: the implementer must not claim that the source `drug_type NOT IN
('BASE')` filter is reproduced by the FHIR mix ingredient path. Existing notes
on string identifiers, hospital/ICU Encounter stream systems, omitted validity
periods, and `TIMESTAMP_NTZ` also changed the casts and joins above. A new
`MIMIC_NOTES.md` entry, **“Prescription route and Medication code displays are
null,”** records the display-null probe and prevents display-based filtering.

No attempt ViewDefinition or SQL artifact was authored.
