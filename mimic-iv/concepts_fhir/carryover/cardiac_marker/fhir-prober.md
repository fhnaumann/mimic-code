# FHIR probe mapping: `cardiac_marker`

## Probe basis

- Concept: `cardiac_marker`, attempt `0001`.
- Source analysis: `mimic-iv/concepts_fhir/carryover/cardiac_marker/source-analyst.md`.
- Canonical SQL: `mimic-iv/concepts/measurement/cardiac_marker.sql`.
- Canonical ViewDefinition shape: `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Served data probed with embedded Pathling 9.6.0 / Spark over
  `/Users/nau025/warehouses/mimic-iv-demo/delta`, not the HTTP server.
- The only available `MIMIC_NOTES.d/*.md` fragment was
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`; there were no concept
  fragments to adopt. The shared notes and the README protocol were read
  before probing.

## Resource mapping

| MIMIC source | FHIR resource/path | Result |
|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` with `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | Confirmed. The active itemids are carried verbatim as `code.coding.code`. |
| `labevents.specimen_id` | `Observation.specimen` → `Specimen`; `Specimen.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value` | Confirmed. The identifier value is the source specimen ID as a string and is the grouping spine. |
| `labevents.subject_id` | `Observation.subject` → `Patient`; `Patient.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value` | Confirmed. Reference key joins are UUID/string keys; the identifier value is the source subject ID as a string. |
| `labevents.hadm_id` | `Observation.encounter` → hospital `Encounter`; `Encounter.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value` | Confirmed for this target. Use a LEFT JOIN: 282/386 numeric target observations had a hospital encounter reference and 104/386 had no reference; those populations exactly matched source non-null/null `hadm_id`. |

## Canonical source-column to FHIRPath mapping

The `_key` and `_str` aliases retain the FHIR/materialized types. The final
concept SQL must cast the identifier strings to the manifest's integer output
types and the Quantity/dateTime aliases to the source output types.

| Source column/use | Canonical FHIR mapping (`{path, name}`) | FHIR type / materialized type | Required final output type |
|---|---|---|---|
| `le.itemid` filter and pivot discriminator | `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')"`; `{ "path": "code", "name": "item_code" }` | `string` / `StringType` | cast `item_code` to `INTEGER` only for comparisons |
| code system for `le.itemid` | `{ "path": "system", "name": "code_system" }` inside the coding `forEach` | `uri`/string / `StringType` | `VARCHAR` if retained |
| code display (supporting field) | `{ "path": "display", "name": "code_display" }` inside the coding `forEach` | `string` / `StringType` | not used by the source SQL |
| `le.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` join key / `StringType` | join only; do not emit as `subject_id` |
| source subject identifier | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` on `Patient` | `string` / `StringType` (`VARCHAR`) | `CAST(subject_id_str AS INTEGER)` → `subject_id` |
| `le.hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | `Reference(Encounter)` join key / `StringType` | join only; do not emit UUID as `hadm_id` |
| source hospital admission identifier | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` on hospital `Encounter` | `string` / `StringType` (`VARCHAR`) | `CAST(hadm_id_str AS INTEGER)` → nullable `hadm_id` |
| `le.specimen_id` grouping key | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key" }` on `Observation`, joined to `{ "path": "getResourceKey()", "name": "specimen_key" }` on `Specimen` | `Reference(Specimen)`/resource key / `StringType` | join only |
| source specimen identifier | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", "name": "specimen_id_str" }` on `Specimen` | `string` / `StringType` (`VARCHAR`) | `CAST(specimen_id_str AS INTEGER)` → `specimen_id` |
| `le.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` / materialized `StringType` (`VARCHAR`) | `CAST(effective_datetime AS TIMESTAMP_NTZ)` → `charttime` |
| `le.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "value" }` | FHIR `decimal`; Pathling ViewDefinition alias is `StringType` (`VARCHAR`) | `CAST(value AS DOUBLE)` → numeric analyte value |

Useful resource keys, although not source output columns, are:

```json
{ "path": "getResourceKey()", "name": "observation_key" }
{ "path": "getResourceKey()", "name": "patient_key" }
{ "path": "getResourceKey()", "name": "encounter_key" }
{ "path": "getResourceKey()", "name": "specimen_key" }
```

The first belongs to `Observation`; the latter three belong to the joined
`Patient`, hospital `Encounter`, and `Specimen` views respectively. They are
UUID/string join keys, never the relational `subject_id`, `hadm_id`, or
`specimen_id` output columns.

## Literal code set and discriminator

The source SQL's active literals are exactly `51003`, `50911`, and `50963`.
The commented `51002` and `52598` are not active filters and are not mapped.
The served Delta confirmed the one system below; no terminology translation is
needed or permitted.

| Literal | Served `code.coding.system` | All coded Observation rows | Numeric Quantity rows (`value` non-null) | Served display |
|---:|---|---:|---:|---|
| `51003` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | 278 | 133 | `Troponin T` |
| `50911` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | 187 | 179 | `Creatine Kinase, MB Isoenzyme` |
| `50963` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | 76 | 74 | `NTproBNP` |
| **total** | one system only | **541** | **386** | |

The same per-code totals were returned by the DuckDB source oracle. The
discriminator is `code.coding.system` plus exact string `code`; do not use
`meta.profile`. The target coded stream had 541 coding rows over 541 distinct
Observation resource keys, ratio **1.0 coding/resource**. Restricting to the
numeric source-equivalent rows gives 386/386, also **1.0**. A constrained
`forEach` is still required so a future second coding cannot fan out the
comparison.

## Probe counts and oracle checks

- Active source-equivalent FHIR input is `value` non-null: 386 rows,
  386 distinct Observations, and 283 distinct Specimen identifiers.
- On those 386 rows, field population was: `quantity_value` 386/386,
  `subject.getReferenceKey(Patient)` 386/386, `specimen.getReferenceKey(Specimen)`
  386/386, `effective.ofType(dateTime)` 386/386, and `encounter` reference
  282/386. Joining the specimen reference to the lab identifier returned
  386/386 observations and 283/283 distinct specimen IDs.
- The `Patient` identifier join returned 386/386 subject identifiers. The
  hospital `Encounter` identifier join returned 282/282 admission identifiers;
  the remaining 104 observations had no encounter reference. The source oracle
  also had 282 non-null and 104 null `hadm_id` values on these 386 rows, and
  null-aware row matching was exact 386/386.
- The three code-specific numeric populations were 50911: 179 rows and
  157 encounter/hadm references; 50963: 74 rows and 28 references; 51003:
  133 rows and 97 references. Quantity, specimen reference/identifier, and
  effective datetime were non-null for every row in each population.
- DuckDB row-level join on `(itemid, specimen_id)` was 386/386, with no
  candidate-only or oracle-only rows. Exact agreement was subject ID 386/386,
  hadm ID (including nulls) 386/386, numeric value 386/386, and effective
  datetime 384/386.
- Grouping the FHIR observations by joined `specimen_id` and reproducing the
  source `MAX`/pivot produced 283/283 groups. Exact agreement was
  `subject_id` 283/283, `hadm_id` 283/283, `troponin_t` 283/283, `ck_mb`
  283/283, and `ntprobnp` 283/283. `charttime` agreed for 282/283 groups.
- The two datetime conflicts are the two target observations in specimen
  `48555540`, source `charttime = 2116-03-08 02:52:00` and served FHIR
  `effectiveDateTime = 2116-03-08T03:52:00-04:00`. This is the established
  DST-gap rewrite in the shared notes, not an additional mapping error;
  `TIMESTAMP_NTZ` preserves the served wall-clock value but cannot recover the
  source 02:52.

## Gaps and representability

- **Subject, specimen, numeric value:** representable and oracle-confirmed.
  Identifier values must remain string aliases until the final integer casts.
- **Hospital admission ID:** representable for this concept's target rows and
  oracle-confirmed, but the mapping is not a guaranteed FHIR invariant. Use a
  LEFT JOIN because lab encounter references are generally incomplete; if a
  future target has a non-null source `hadm_id` with no reference, only a
  patient/time heuristic exists and it is not an exact derivation.
- **Effective datetime:** present for all 386 active target observations but
  **not exactly representable for 2/386 rows (1/283 grouped outputs)** because
  the upstream ETL normalizes the DST-gap wall-clock value. This is a
  not-representable transformation gap, not an absent-but-derivable field.
- **Non-numeric source rows:** the FHIR resources exist (541 coded rows), but
  `value` is absent for 155 rows (8 for 50911, 2 for 50963, 145 for 51003),
  matching the source SQL's `valuenum IS NOT NULL` filter. They must be
  excluded from the numeric pivot rather than approximated from `valueString`.

## Shared-note impact

The established `MIMIC_NOTES.md` entries that changed or constrained this
mapping were: Delta tables are authoritative; itemid code values are verbatim
and use the `mimic-d-labitems` system; MIMIC identifiers are string values and
resource/reference keys are UUID join keys; Quantity.value aliases materialize
as strings; lab Observation.specimen preserves the source specimen identifier;
lab encounter references require a LEFT JOIN; subtype `meta.profile` is not a
safe discriminator; and FHIR datetimes require `TIMESTAMP_NTZ`, with known DST
gap rewrites. A new dataset-wide casting quirk was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/cardiac_marker.md`: the merged Observation
table also contains non-numeric LOINC codes, so itemid code filters must use
the system and exact string code before any integer cast.
