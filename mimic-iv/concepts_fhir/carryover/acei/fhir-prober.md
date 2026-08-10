# FHIR Mapping: `acei`

**Concept:** `medication/acei`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/acei/source-analyst.md`  
**Probe date:** 2026-08-08, corrected mapping for attempt 0004  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, authoritative
Delta queried with embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Corrected result

`mimiciv_hosp.prescriptions` maps to the pharmacy-backed hospital
`MedicationRequest` stream. The request has one row per `pharmacy_id`, so the
prescription drug row is recovered in two mutually exclusive branches:

1. **Direct branch:** `MedicationRequest.medicationReference` points to a
   prescription `Medication` carrying one `mimic-medication-name` identifier.
2. **Medication-mix branch:** the request points to a mix `Medication` carrying
   one `medication-mix` identifier and repeated
   `Medication.ingredient.itemReference` components. Each component reference
   resolves to a name-bearing `Medication`.

The final concept query must `UNION ALL` these branches. It must not use
`DISTINCT`: each ingredient component is one source prescription row, and the
same mix resource is reused by many requests. The output still has exactly the
five source columns (`subject_id`, `hadm_id`, `acei`, `starttime`, `stoptime`);
`pharmacy_id` and UUID reference keys are support columns only.

## Canonical ViewDefinition mappings

The canonical structure is the `select[].column[]` / `select[].forEach` format
from `v_observation.viewdefinition.json`. Use separate materialized labels for
the request, patient, encounter, name-bearing Medication, and mix Medication
views. The name-bearing Medication view is shared by both direct requests and
mix component references.

### `MedicationRequest` — common prescription spine

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
    }
  ]
}
```

| Source column | FHIRPath mapping (`{path, name}`) | FHIR type | Materialized/output type |
|---|---|---|---|
| `pharmacy_id` (support only) | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" }` | `Identifier.value` string | `VARCHAR`; use only to select pharmacy-backed requests and validate cardinality |
| `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, then Patient identifier below | `Reference` UUID plus `Identifier.value` string | final `CAST(subject_id_str AS INTEGER)` → `INTEGER` |
| `hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`, then hosp Encounter identifier below | `Reference` UUID plus `Identifier.value` string | final `CAST(hadm_id_str AS INTEGER)` → `INTEGER` |
| `drug` / output `acei` | `{ "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" }` into either Medication branch | `Reference` UUID | resolved name is FHIR string; final bounded `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `starttime` | `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | `dateTime` | Pathling alias is `VARCHAR`; `TRY_CAST(starttime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |
| `stoptime` | `{ "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }` | `dateTime` | Pathling alias is `VARCHAR`; `TRY_CAST(stoptime_str AS TIMESTAMP_NTZ)` → `TIMESTAMP` |

`authoredOn` is not a source start or stop time and must not substitute for a
missing validity period.

### Patient and hospital Encounter identifier joins

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

Join request `patient_key`/`encounter_key` to resource keys. Filter
`hadm_id_str IS NOT NULL`; do not use `Encounter.class` to select the hospital
stream. The UUIDs are join-only and must never be emitted as MIMIC IDs.

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

The direct branch joins `MedicationRequest.medication_key` directly to this
view. The mix branch joins
`ingredient_medication_key` to the same view. The source drug string is
`Medication.identifier.value`, not `Medication.code.coding.code`.

### Medication-mix ingredient branch

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

Within the `forEach: "ingredient"` group, the full element is
`Medication.ingredient.itemReference`; the materialized path is
`itemReference.getReferenceKey(Medication)`. Join `MedicationRequest.medication_key`
to `mix_key`, then join each repeated `ingredient_medication_key` to the
name-bearing Medication view. Do not project only the mix identifier or use
`DISTINCT` after this join.

Concept SQL shape:

```sql
SELECT ... FROM medication_request mr
JOIN medication_name mn ON mr.medication_key = mn.medication_key
WHERE mr.pharmacy_id_str IS NOT NULL AND ...name predicate...
UNION ALL
SELECT ... FROM medication_request mr
JOIN medication_mix mm ON mr.medication_key = mm.mix_key
JOIN medication_name mn ON mm.ingredient_medication_key = mn.medication_key
WHERE mr.pharmacy_id_str IS NOT NULL AND ...name predicate...
```

The first branch is one row per direct request. The second is one row per
ingredient reference. The ten predicates below must be applied to
`UPPER(mn.drug_name)` in both branches.

The predicate is exactly:

```sql
UPPER(mn.drug_name) LIKE '%BENAZEPRIL%'
OR UPPER(mn.drug_name) LIKE '%CAPTOPRIL%'
OR UPPER(mn.drug_name) LIKE '%ENALAPRIL%'
OR UPPER(mn.drug_name) LIKE '%FOSINOPRIL%'
OR UPPER(mn.drug_name) LIKE '%LISINOPRIL%'
OR UPPER(mn.drug_name) LIKE '%MOEXIPRIL%'
OR UPPER(mn.drug_name) LIKE '%PERINDOPRIL%'
OR UPPER(mn.drug_name) LIKE '%QUINAPRIL%'
OR UPPER(mn.drug_name) LIKE '%RAMIPRIL%'
OR UPPER(mn.drug_name) LIKE '%TRANDOLAPRIL%'
```

## Probe counts and literal filter confirmation

### Resource and cardinality counts

| Probe | Rows total | Rows non-null / resolved | Result |
|---|---:|---:|---|
| `MedicationRequest` | 17,552 | `pharmacy_id_str` 15,225; `medication_key` 15,225 | pharmacy request spine |
| `MedicationRequest.subject` reference | 17,552 | 17,552 | all request subjects populated |
| `MedicationRequest.encounter` reference | 17,552 | 17,552 | all request encounters populated |
| `dispenseRequest.validityPeriod.start` | 17,552 | 14,574 | absent when ETL validity guard fails |
| `dispenseRequest.validityPeriod.end` | 17,552 | 14,574 | absent when ETL validity guard fails |
| `Medication` | 1,794 | name identifier 1,480/1,480 resources | one name identifier per direct/component Medication |
| name identifier values | 1,480 | 1,480 non-null; 631 distinct strings | exact source drug strings |
| medication-mix identifier | 314 | 314/314 mix resources | exact system below |
| `Medication.ingredient.itemReference` | 634 | 634/634 non-null and 634/634 resolve to name Medication | repeated component branch |
| Patient identifier | 100 | 100/100 | patient identifier system |
| Encounter hospital identifier | 637 | 275/637 | hospital stream; other Encounter streams excluded |
| request → Patient join | 15,225 pharmacy requests | 15,225/15,225 | no pharmacy-request join loss |
| request → Encounter join | 15,225 pharmacy requests | 15,225/15,225 | no pharmacy-request join loss |

Ingredient multiplicity is **310 mix resources with 2 components, 2 with 3,
and 2 with 4**, for 634 references total. The mix resources are reused: 2,843
pharmacy-backed requests use the mix branch, while 12,382 use the direct
branch. The expanded mix branch has 5,705 rows, exactly the 5,705 source
prescription rows in multi-row pharmacy groups.

There is no formal source code set in `acei.sql`. The discriminator is the
exact identifier system plus the source text predicate, never `meta.profile`:

- direct/component name discriminator:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name`;
  1,480 identifier occurrences / 1,480 resources = **1.000 identifier per
  resource**;
- mix discriminator:
  `http://mimic.mit.edu/fhir/mimic/identifier/medication-mix`;
  314 identifier occurrences / 314 mix resources = **1.000 identifier per
  resource**;
- component references: 634 / 314 mix resources = **2.019 references per
  mix resource**, with the multiplicity distribution above.

`Medication.code.coding` is not the ACEI discriminator. The supporting code
probe had one coding per direct Medication (1,480/1,480); its systems were
1,402 NDC, 72 formulary, and 6 medication-name. Filtering those codings would
not implement the source SQL.

### Exact ten ACEI predicates

All selected direct/component rows carried the exact name identifier system
above. Counts are source DuckDB rows, direct FHIR rows, and mix-component FHIR
rows respectively:

| Source predicate on `UPPER(drug)` | Oracle demo | Direct FHIR | Mix FHIR |
|---|---:|---:|---:|
| `%BENAZEPRIL%` | 0 | 0 | 0 |
| `%CAPTOPRIL%` | 19 | 19 | 0 |
| `%ENALAPRIL%` | 9 | 9 | 0 |
| `%FOSINOPRIL%` | 0 | 0 | 0 |
| `%LISINOPRIL%` | 76 | 76 | 0 |
| `%MOEXIPRIL%` | 0 | 0 | 0 |
| `%PERINDOPRIL%` | 0 | 0 | 0 |
| `%QUINAPRIL%` | 0 | 0 | 0 |
| `%RAMIPRIL%` | 3 | 3 | 0 |
| `%TRANDOLAPRIL%` | 0 | 0 | 0 |
| **Total** | **107** | **107** | **0** |

The zero mix counts are a demo-cohort fact, not permission to omit the mix
branch. Attempt 0003 full data showed the consequence: direct-only filtering
returned 590 `Enalaprilat` rows versus 776 oracle rows, missing 186 rows from
186 two-row pharmacy groups. The corrected branch is required for full data.

## Oracle agreement and timestamp semantics

The DuckDB/Delta comparison on the demo established:

- all 631 distinct source `drug` strings are exactly the 631 FHIR name values;
- all 314 source mix identifiers are exactly the 314 Delta mix identifiers;
- all 314 mix ingredient name multisets agree exactly, covering 634/634
  component references;
- expanded mix drug multiplicity agrees exactly: 5,705 source rows versus
  5,705 FHIR ingredient rows;
- the 107 direct ACEI request keys agree 107/107 with source ACEI rows, and
  the drug/`acei` value agrees 107/107; `starttime` and `stoptime` agree
  95/107 each. The 12 timestamp discrepancies are invalid source intervals
  whose FHIR validity period is intentionally absent.

For the complete demo multi-drug branch, 2,843 pharmacy groups expand to
5,705 source rows and 5,705 FHIR component rows. Source drug multiplicity is
exact. The FHIR request validity fields are populated for 2,727 groups and
null for 116 groups; the latter expand to 232 candidate rows with null start
and stop while the source timestamps are non-null. This is the ETL guard, not
a join or multiplicity error.

The FHIR ETL writes validity only when both coalesced request times are
present and `start <= stop` (`mimic-fhir/sql/fhir_medication_request.sql:172-177`).
Thus invalid or incomplete source times are **absent and not representable**;
do not use `authoredOn` or estimate them. Use the FHIR values as wall-clock
strings and cast to `TIMESTAMP_NTZ`, not timezone-converting `TIMESTAMP`.
The full run also found 14 DST-normalized prescription timestamp conflicts
from the upstream `TIMESTAMPTZ` cast (`fhir_medication_request.sql:43-44`);
the original wall time is unrecoverable, while `TIMESTAMP_NTZ` preserves the
FHIR value faithfully.

## Diagnosis addressed and gaps

Attempt 0003 (`comparison.full.json`) had schema success but candidate 111,828
versus oracle 112,014 rows. Its mismatch diagnosis identified the missing
`Medication.ingredient.itemReference` branch and 186 missing full-data
`Enalaprilat` rows. This corrected mapping addresses that fixable gap with
`UNION ALL` and repeated ingredient projection.

Remaining representability gaps are intrinsic to the served FHIR transform:

- **Absent and not representable:** invalid/incomplete source validity
  intervals, because the ETL omits `dispenseRequest.validityPeriod` entirely;
  output typed NULL timestamps.
- **Absent and not representable:** original source wall times for the small
  upstream DST-gap normalization set; no query can invert the ETL's
  `TIMESTAMPTZ` rewrite.
- **No gap:** drug strings, direct/mix branch identity, component
  multiplicity, patient IDs, and hospital admission IDs were all represented
  by the paths above. No approximation is used.

## Shared-note changes

The existing MIMIC_NOTES entry **“Prescription Medication.code prefers
NDC/formulary; the source drug name is in an identifier”** was updated in
place to sharpen the exact mix identifier URI and the verified 314-resource /
634-component multiplicity. No new dataset-wide note was added. The existing
entries on identifier strings, Encounter stream discrimination, omitted
validity periods, and `TIMESTAMP_NTZ` continue to determine the casts and
filters above.

No immutable attempt artifact was edited.
