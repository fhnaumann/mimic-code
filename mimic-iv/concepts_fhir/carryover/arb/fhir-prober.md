# FHIR mapping: `medication/arb`

**Source analysis:** `mimic-iv/concepts_fhir/carryover/arb/source-analyst.md`  
**Source SQL:** `mimic-iv/concepts/medication/arb.sql`  
**Probe date:** 2026-08-08  
**Authoritative FHIR warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Result

`mimiciv_hosp.prescriptions` is represented by pharmacy-backed
`MedicationRequest` resources and their referenced `Medication` resources.
The source output is the original free-text `prescriptions.drug` value, not a
boolean FHIR code. There are two request-to-name paths and both must be kept:

1. **Direct:** `MedicationRequest.medicationReference` resolves directly to a
   name-bearing `Medication`.
2. **Medication mix:** the request reference resolves to a mix `Medication`,
   whose repeated `ingredient.itemReference` values resolve to component
   name-bearing `Medication` resources.

The final query must `UNION ALL` these branches. It must not use `DISTINCT`:
one mix ingredient represents one source prescription row, and a mix resource
can be referenced by multiple requests. The demo has no ARB match in the mix
branch, but the branch is required for full data.

There is no itemid, ICD, or other `code.coding` filter in `arb.sql`. The exact
discriminator is the medication-name **identifier** system plus the literal
case-insensitive substring predicate on its value. `Medication.code.coding`
is not the source drug field: the served direct/component medications carry
NDC/formulary/name code systems by ETL priority, while the original source
drug text is in the name identifier.

## Canonical ViewDefinition mappings

The snippets use the authoritative `select[].column[]` and
`select[].forEach` format from
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
UUID resource/reference keys are join-only support columns.

### MedicationRequest spine

```json
{
  "resource": "MedicationRequest",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "medication_request_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
      { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" },
      { "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" },
      { "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" },
      { "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }
    ]
  }]
}
```

`pharmacy_id_str IS NOT NULL` selects prescription-backed requests and excludes
the 2,327 POE requests. `authoredOn` is not a substitute for either source
validity endpoint.

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
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
    ]
  }]
}
```

Join `MedicationRequest.patient_key` to `Patient.patient_key` and
`MedicationRequest.encounter_key` to `Encounter.encounter_key`. Filter
`hadm_id_str IS NOT NULL`; do not use `Encounter.class` to select the hospital
stream. The final output casts `subject_id_str` and `hadm_id_str` to `INTEGER`.

### Direct/component name-bearing Medication

```json
{
  "resource": "Medication",
  "select": [
    { "column": [{ "path": "getResourceKey()", "name": "medication_key" }] },
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

The direct branch joins `MedicationRequest.medication_key` to this view. The
mix branch joins `ingredient_medication_key` to the same view. The source
`prescriptions.drug` and output `arb` are `drug_name`.

### Medication-mix identifier and ingredient references

Use a separate mix-identifier view to avoid accidental identifier/ingredient
fan-out:

```json
{
  "resource": "Medication",
  "select": [
    { "column": [{ "path": "getResourceKey()", "name": "mix_key" }] },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-mix')",
      "column": [
        { "path": "system", "name": "mix_system" },
        { "path": "value", "name": "mix_identifier" }
      ]
    }
  ]
}
```

```json
{
  "resource": "Medication",
  "select": [
    { "column": [{ "path": "getResourceKey()", "name": "mix_key" }] },
    {
      "forEach": "ingredient",
      "column": [
        { "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }
      ]
    }
  ]
}
```

Within the `forEach: "ingredient"` group, the full element is
`Medication.ingredient.itemReference`; the materialized path is
`itemReference.getReferenceKey(Medication)`. Join request `medication_key` to
`mix_key`, then each `ingredient_medication_key` to the name-bearing
Medication view. Preserve every repeated ingredient.

## Source-column mapping and target types

`identifier.value` is a FHIR string even when it contains digits. Pathling
ViewDefinition aliases for FHIR `dateTime` are also `StringType()` values with
an ISO-8601 offset. The implementer must keep these intermediate names typed
as strings, then cast numeric identifiers to `INTEGER`, drug text to bounded
`VARCHAR(255)`, and datetimes with `TRY_CAST(... AS TIMESTAMP_NTZ)` to the
manifest's `TIMESTAMP` type. Do not use timezone-converting `TIMESTAMP`.

| Source table.column | FHIRPath mapping (`{path, name}`) | FHIR type | Materialized type | Final output/type |
|---|---|---|---|---|
| `prescriptions.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, joined to Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference` UUID plus `Identifier.value` string | `StringType()` | `CAST(subject_id_str AS INTEGER)` → `INTEGER` |
| `prescriptions.hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`, joined to hospital Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Reference` UUID plus `Identifier.value` string | `StringType()` | `CAST(hadm_id_str AS INTEGER)` → `INTEGER` |
| `prescriptions.drug`, direct | `{ "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" }` then name Medication `{ "path": "value", "name": "drug_name" }` under the name-identifier `forEach` | `Reference` UUID then `Identifier.value` string | `StringType()` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.drug`, mix ingredient | `{ "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }` under `forEach: "ingredient"`, then name Medication `{ "path": "value", "name": "drug_name" }` | repeated `Reference` UUID then `Identifier.value` string | `StringType()` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.starttime` | `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | `Period.start` `dateTime` | `StringType()` with offset | `TRY_CAST(starttime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `prescriptions.stoptime` | `{ "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }` | `Period.end` `dateTime` | `StringType()` with offset | `TRY_CAST(stoptime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `prescriptions.pharmacy_id` (support only) | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" }` | `Identifier.value` string | `StringType()` | support-only `VARCHAR`; do not emit |

The FHIR resource keys (`getResourceKey()` and
`getReferenceKey(ResourceType)`) are UUID join keys, never output
`subject_id`, `hadm_id`, or `arb` values.

## Delta population and cardinality probes

All counts below came from materialized ViewDefinitions and Spark `count(*)`
versus `count(column)` over the authoritative Delta warehouse.

| Probe | Rows | Non-null / resolved |
|---|---:|---:|
| `MedicationRequest` | 17,552 | `patient_key` 17,552; `encounter_key` 17,552 |
| Pharmacy identifier (`phid`) | 17,552 request rows | 15,225 |
| Pharmacy-backed `medicationReference` | 17,552 request rows | 15,225 |
| `dispenseRequest.validityPeriod.start` | 17,552 | 14,574 |
| `dispenseRequest.validityPeriod.end` | 17,552 | 14,574 |
| `authoredOn` | 17,552 | 17,552; not a source validity substitute |
| Direct request → name Medication | 12,382 pharmacy requests | 12,382 resolved |
| Mix requests | 15,225 pharmacy requests | 2,843 mix; 12,382 direct |
| Name-bearing Medication | 1,480 | name identifier/value 1,480/1,480 |
| Name values | 1,480 | 1,480 non-null; 631 distinct strings |
| Mix Medication | 314 | mix identifier/value 314/314 |
| Mix `ingredient.itemReference` | 634 | 634/634 references resolve to name Medications |
| Patient identifier | 100 | 100/100; 100 distinct values |
| Encounter hospital identifier | 637 | 275/637; 275 distinct values |

The identifier occurrence ratios are 1,480/1,480 = **1.000 name identifier
per name-bearing Medication**, 314/314 = **1.000 mix identifier per mix
Medication**, and 15,225/15,225 = **1.000 pharmacy identifier per pharmacy
request**. The mix ingredient ratio is 634/314 = **2.019 references per mix
resource**, distributed as 310 resources with 2 ingredients, 2 with 3, and 2
with 4. These are identifier/ingredient probes, not `code.coding` probes;
`arb.sql` has no `code.coding` filter. The observed name and mix systems are
the exact systems in the FHIRPath predicates above. The request system also
has 2,327 `medication-request-poe` identifiers, which are deliberately not
selected.

The direct and mix branches expand to 12,382 and 5,705 rows respectively.
Across all pharmacy-backed prescriptions, `(pharmacy_id, drug)` multiplicity
agreed exactly: 18,087 source rows / 18,087 FHIR rows, 18,087 groups, zero
source-only groups, zero FHIR-only groups, and zero count mismatches. The
demo source has no pharmacy group with differing start or stop values, and
the ARB rows are all direct in this cohort; neither observation permits
dropping the mix branch for full data.

## Literal substring confirmation

There is no terminology code set to resolve. These are the 16 exact source
`UPPER(drug) LIKE '%TOKEN%'` literals. Counts are raw oracle rows, direct
FHIR name rows, mix-ingredient FHIR name rows, and their FHIR total. Zero is a
served-demo count, not a declaration that the literal is removable.

| Source token | Oracle | Direct | Mix | FHIR total |
|---|---:|---:|---:|---:|
| `AZILSARTAN` | 0 | 0 | 0 | 0 |
| `EDARBI` | 0 | 0 | 0 | 0 |
| `CANDESARTAN` | 0 | 0 | 0 | 0 |
| `ATACAND` | 0 | 0 | 0 | 0 |
| `IRBESARTAN` | 8 | 8 | 0 | 8 |
| `AVAPRO` | 1 | 1 | 0 | 1 |
| `LOSARTAN` | 23 | 23 | 0 | 23 |
| `COZAAR` | 0 | 0 | 0 | 0 |
| `OLMESARTAN` | 0 | 0 | 0 | 0 |
| `BENICAR` | 0 | 0 | 0 | 0 |
| `TELMISARTAN` | 0 | 0 | 0 | 0 |
| `MICARDIS` | 0 | 0 | 0 | 0 |
| `VALSARTAN` | 3 | 3 | 0 | 3 |
| `DIOVAN` | 0 | 0 | 0 | 0 |
| `SACUBITRIL` | 1 | 1 | 0 | 1 |
| `ENTRESTO` | 0 | 0 | 0 | 0 |

The OR of the 16 predicates contains 35 source/FHIR rows. The per-token sum
is 36 because `Sacubitril-Valsartan (24mg-26mg)` matches both `VALSARTAN` and
`SACUBITRIL`. The name-system discriminator is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name`; use the
identifier value and `UPPER(drug_name) LIKE`, never `Medication.code.coding`
or `display`. The source-to-FHIR ARB name expansion was exact at 35/35 rows.

## Oracle agreement, natural-key shape, and timestamps

The ARB-only source probe returned 35 rows with all five source fields
populated: `subject_id`, `hadm_id`, `drug`, `starttime`, and `stoptime` were
35/35 non-null. It contained 28 valid intervals and 7 reversed intervals
(`starttime > stoptime`), with no incomplete interval. The joined FHIR result
had 35/35 non-null subject/admission IDs, 28/35 non-null starts and stops,
and the following exact checks:

- `(pharmacy_id, drug)` keys: 35 source / 35 FHIR, all 35 keys present;
- `subject_id` and `hadm_id`: **35/35 exact**;
- valid `starttime` and `stoptime`: **28/28 exact** after parsing the FHIR
  offset as a wall-clock value with `TIMESTAMP_NTZ`;
- the 7 reversed source intervals: **7/7** represented by FHIR `NULL`/`NULL`
  validity endpoints.

Served values are strings such as
`2142-08-02T10:00:00-04:00`. `TRY_CAST(value AS TIMESTAMP_NTZ)` returned
28/28 valid starts and stops with zero parse failures. `TIMESTAMP_NTZ` is
required: these are de-identified wall-clock values, and timezone-converting
casts shift them. The existing dataset note also records the upstream
`TIMESTAMPTZ` DST-gap rewrite, which is irreversible if encountered in full
data.

The demo ARB output has 35 distinct full tuples, but smaller anchored
combinations are not unique: subject only 7, subject+hadm 26,
subject+hadm+drug 26, subject+hadm+starttime 34, and subject+hadm+drug+starttime
34. The full oracle manifest is authoritative for full-data shape:
`arb` has `key: null`, `comparison: full_tuple_multiset`, and 39,534 rows.
Do not invent a keyed join from the demo or use a FHIR UUID as a source key.

## Gaps

### Absent and not representable: invalid or incomplete validity intervals

`MedicationRequest.dispenseRequest.validityPeriod` is emitted only when the
ETL's grouped source times are both present and `start <= stop`. The 7 demo
ARB rows with reversed source intervals therefore lose both endpoint values;
`authoredOn` is a request timestamp, not a source start or stop. Emit typed
NULL timestamps for these rows rather than estimating them. This is the
existing dataset-wide `MIMIC_NOTES.md` finding, not an ARB-specific filter bug.

No absent-but-derivable or exact approximation was found for the requested
ARB columns. No approximation is admissible for the omitted validity values.
The direct/mix references, drug strings, ingredient multiplicity, subject IDs,
and hospital admission IDs are represented by the paths above.

## Shared-note changes

No `MIMIC_NOTES.md` entry was added or changed. Existing entries that changed
this mapping decision were:

- **“MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a UUID”**:
  use Patient/Encounter identifier values and cast them at the final SQL
  boundary.
- **“Prescription Medication.code prefers NDC/formulary; the source drug name
  is in an identifier”**: use the medication-name identifier, and preserve
  both direct and mix ingredient paths.
- **“MedicationRequest omits invalid or incomplete prescription validity
  periods”**: use FHIR validity paths and typed NULL for omitted endpoints;
  never use `authoredOn`.
- **“FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never to
  TIMESTAMP”**: retain the served wall-clock value while casting.

The probe found no genuinely new dataset-wide quirk after checking these
entries for duplicates. No immutable attempt artifact was edited.
