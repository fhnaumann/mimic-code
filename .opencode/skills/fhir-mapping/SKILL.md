---
name: fhir-mapping
description: Map MIMIC-IV source tables and columns to MIMIC-on-FHIR resource paths and author FHIR ViewDefinitions using the proven select.column path/name format with forEach/forEachOrNull patterns (from orchestration-new/scripts/sofa_provisioning). Trigger phrases include "FHIR mapping", "map to FHIR", "ViewDefinition", "element path", "FHIRPath".
---

# fhir-mapping

Mapping MIMIC-IV source tables and columns to MIMIC-on-FHIR resource paths
and authoring FHIR ViewDefinitions using the canonical format from
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/`.

## ViewDefinition format (authoritative)

The `scripts/sofa_provisioning/v_observation.viewdefinition.json` is the
canonical reference. Every concept port ViewDefinition MUST follow this
exact structural pattern:

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "url": "https://fhnaumann.masters/pathling/ViewDefinition/<name>",
  "name": "<name>",
  "resource": "<FHIR_ResourceType>",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "<resource>_fhir_id" },
        { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_fhir_id" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_fhir_id" },
        { "path": "(value).ofType(Quantity).value", "name": "value" },
        { "path": "(value).ofType(Quantity).unit", "name": "unit" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }
      ]
    },
    {
      "forEach": "code.coding",
      "column": [
        { "path": "code", "name": "code" },
        { "path": "system", "name": "system" },
        { "path": "display", "name": "display" }
      ]
    }
  ]
}
```

Key format rules:
- `select` is an array of **column groups**. Each group is an object with
  either a `column` array (flat extraction) or a `forEach` + `column` pair
  (iterating over repeating elements).
- Within `column`, each entry has `path` (the FHIRPath expression) and
  `name` (the output column name).
- **NOT** `select.expression` or `select.name` at the object level — that
  shape is hallucinated.
- `forEach`/`forEachOrNull` wraps `code.coding`, `identifier`, etc.

## Proven provisioning flow (from sofa_provisioning)

The canonical flow for executing a concept port, as demonstrated in
`register_patient_sofa.py`:

1. **PUT ViewDefinition** — register the ViewDefinition on the Pathling
   server via `PUT ViewDefinition/<id>`.
2. **PUT Library** — register a `Library` resource of type `sql-view` with
   `relatedArtifact` labels referencing the registered ViewDefinition:
   ```json
   {
     "resourceType": "Library",
     "status": "active",
     "url": "<library_url>",
     "type": { "coding": [{ "system": "http://terminology.hl7.org/CodeSystem/library-type", "code": "sql-view" }] },
     "content": [{ "contentType": "application/sql", "data": "<base64-sql>" }],
     "relatedArtifact": [{ "type": "depends-on", "label": "<vd_label>", "resource": "<vd_url>" }]
   }
   ```
3. **Execute** — run SQL through `$sqlquery-run` or the Pathling client's
   `sqlquery_run_sync()` with the ViewDefinition label references.

## FHIRPath idioms (from MIMIC_NOTES.md)

- **`getResourceKey()`** — for the FHIR resource key. This is not a raw MIMIC
  identifier.
- **`getReferenceKey(ResourceType)`** — for foreign-key references
  (e.g. `subject.getReferenceKey(Patient)`, `encounter.getReferenceKey(Encounter)`).
- **`.ofType(X)`** — for choice-type (polymorphic) fields. Each variant
  gets its own column:
  - `(effective).ofType(dateTime)` → `effective_datetime`
  - `(effective).ofType(Period).start` → `effective_period_start`
  - The derived SQL then `COALESCE`s the variants as needed.

## Identifier spine

Exact comparison requires raw MIMIC identifiers, not FHIR UUIDs. Project
these identifiers with `forEachOrNull: "identifier"`, retain both `system`
and `value`, and select the values for the systems used by the actual data:

- Patient identifier ending in `/identifier/patient` → `subject_id`.
- Hospital Encounter identifier ending in `/identifier/encounter-hosp` →
  `hadm_id`.
- ICU Encounter identifier ending in `/identifier/encounter-icu` → `stay_id`.

Probe and record the complete identifier system URLs before relying on them.
An Observation's `subject.getReferenceKey(Patient)` and
`encounter.getReferenceKey(Encounter)` are join keys into these identifier
views; they are not themselves `subject_id`, `hadm_id`, or `stay_id`.

## MIMIC source-table → FHIR resource mapping

| MIMIC Table (Schema) | Likely FHIR Resource | Required Probe |
|---|---|---|
| `admissions` (hosp) | `Encounter` | id, subject, period, class |
| `patients` (hosp) | `Patient` | id, birthDate, gender |
| `diagnoses_icd` (hosp) | `Condition` | id, subject, encounter, code, recordedDate |
| `labevents` (hosp) | `Observation` | id, subject, encounter, code, value, effective |
| `microbiologyevents` (hosp) | `Observation` | id, subject, encounter, code, value, effective |
| `prescriptions` (hosp) | `MedicationRequest` | id, subject, encounter, medication, authoredOn |
| `chartevents` (icu) | `Observation` | id, subject, encounter, code, value, effective |
| `inputevents` (icu) | `MedicationAdministration` | id, subject, encounter, medication, effective |
| `outputevents` (icu) | `Observation` | id, subject, encounter, code, value, effective |
| `procedureevents` (icu) | `Procedure` | id, subject, encounter, code, performed |
| `icustays` (icu) | `Encounter` | id, subject, period, class |

## IG probing

To probe the live IG for field definitions:
```
GET <pathling_base>/fhir/StructureDefinition/<resource_type>
```

The StructureDefinition's `snapshot.element` array contains every field
with its path, type, cardinality, and binding. Local FHIR JSON snapshots
from `../master_thesis_pipeline/orchestration-new/` provide cached IG data
for offline resolution. Treat the table above as a starting hypothesis;
confirm the populated resource type, profile, coding system, identifiers,
choice variants, and units against the actual MIMIC-on-FHIR 2.1 data.
