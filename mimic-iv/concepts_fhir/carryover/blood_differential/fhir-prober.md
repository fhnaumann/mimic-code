# FHIR probe and corrected mapping: `blood_differential`

**Attempt:** `attempt_0002` (re-probe after the attempt-0001 mapping was
invalidated)  
**Probed:** 2026-08-10  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2. No HTTP server, raw
ndjson, ViewDefinition artifact, or attempt artifact was used or modified by
this stage.

## Source and target

The source is only `mimiciv_hosp.labevents`, grouped by `specimen_id`. Its
FHIR source stream is `Observation` generated from labevents. `Specimen`,
`Patient`, and hospital-stream `Encounter` provide the identifier spines
needed to recover the relational IDs.

| Source table/role | FHIR resource | Discriminator/join |
|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` and exact `code` |
| `labevents.specimen_id` | `Specimen` | `Observation.specimen.getReferenceKey(Specimen)` → lab Specimen identifier system |
| `labevents.subject_id` | `Patient` | `Observation.subject.getReferenceKey(Patient)` → patient identifier system |
| `labevents.hadm_id` | hospital `Encounter` | `Observation.encounter.getReferenceKey(Encounter)` → hospital Encounter identifier system; always `LEFT JOIN` |

The source allowlist is exactly the 23 active itemids in the source SQL. The
commented itemids are not part of the port. The output remains the 20-column
manifest shape with natural key `specimen_id`; `granulocytes_abs` is an
intermediate for item `51218`, not an output column.

## Corrected Observation ViewDefinition projections

The canonical flat projection is:

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "observation_key"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
    {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
    {"path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key"},
    {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
    {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
    {"path": "(effective).ofType(instant)", "name": "effective_instant"},
    {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
    {"path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator"},
    {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
    {"path": "(value).ofType(Quantity).code", "name": "quantity_code"},
    {"path": "(value).ofType(string)", "name": "value_string"}
  ]
}
```

The exact coding group is:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')",
  "column": [
    {"path": "code", "name": "code"},
    {"path": "system", "name": "system"},
    {"path": "display", "name": "display"}
  ]
}
```

The new `quantity_comparator` projection is required. The upstream ETL first
uses `lab.valuenum` when it is non-NULL, but otherwise parses comparator text
such as `<0.1` into `lab_VALUENUM`; it then writes that value as a
`valueQuantity` and writes the comparator separately. Thus a source row with
`valuenum IS NULL`, `value='<0.1'` becomes Quantity `value=0.1`,
`comparator='<'`, with no `valueString`. It must not satisfy this concept's
source numeric filter.

For this concept, the SQL row filter must therefore be equivalent to:

```sql
CAST(quantity_value AS DOUBLE) IS NOT NULL
AND quantity_comparator IS NULL
AND CAST(quantity_value AS DOUBLE) >= 0
```

The comparator test fixes attempt 0001, which accepted every non-NULL Quantity.
Do not use `value_string` as a numeric fallback. In the demo Delta the
comparator-bearing `<0.1` rows are absent, so `quantity_comparator` is NULL for
all 11,908 targeted rows; the probe nevertheless confirms that this path
materializes as a string column and the full-data diagnosis observed the five
source-null `<0.1` rows as comparator-bearing Quantities.

The ETL computes `VALUE_COMPARATOR` from source text independently of the
`lab.valuenum` branch. The `comparator IS NULL` guard is consequently a
dataset-observed discriminator for this source set, not a general FHIR rule
that can distinguish every possible future combination of numeric value and
comparator-looking text.

## Supporting identifier projections

### Specimen

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "specimen_key"}
  ]
}
```

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab')",
  "column": [
    {"path": "value", "name": "specimen_id_str"},
    {"path": "system", "name": "specimen_id_system"}
  ]
}
```

`specimen_id_str` is FHIR `string` / materialized `STRING`; the final SQL
casts it to manifest `INTEGER`. `getResourceKey()` is only the UUID join key,
never the output `specimen_id`.

### Patient

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "patient_key"}
  ]
}
```

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient')",
  "column": [
    {"path": "value", "name": "subject_id_str"},
    {"path": "system", "name": "subject_id_system"}
  ]
}
```

`subject_id_str` is FHIR `string` / materialized `STRING`; final SQL casts it
to manifest `INTEGER`. Join `patient_key` to the Observation reference key.

### Hospital Encounter

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "encounter_key"}
  ]
}
```

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')",
  "column": [
    {"path": "value", "name": "hadm_id_str"},
    {"path": "system", "name": "hadm_id_system"}
  ]
}
```

`hadm_id_str` is FHIR `string` / materialized `STRING`; final SQL casts it to
nullable manifest `INTEGER`. The encounter join must be a `LEFT JOIN` because
lab Observation encounter references are incomplete.

## Source-column mapping and types

The `_key` aliases are FHIR UUID/reference strings. The `_str` aliases are
FHIR identifier strings and require casts in the final SQL. ViewDefinition
aliases for Quantity values and comparator are also materialized as Spark
`STRING`, even though the underlying FHIR Quantity value is decimal.

| Source column or role | Canonical FHIR mapping (`{path, name}`) | FHIR type | Observed materialized type | Final/source use |
|---|---|---|---|---|
| `labevent_id` (only if row identity is needed) | `{path: "getResourceKey()", name: "observation_key"}` | resource key `string` | `STRING` | not in canonical output |
| `subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` plus Patient `{path: "value", name: "subject_id_str"}` under the patient identifier group | `Reference(Patient)` plus identifier `string` | `STRING` | join by UUID; `CAST(subject_id_str AS INTEGER)` |
| `hadm_id` | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` plus Encounter `{path: "value", name: "hadm_id_str"}` under the hospital identifier group | `Reference(Encounter)` plus identifier `string` | `STRING` | nullable left join; `CAST(hadm_id_str AS INTEGER)` |
| `specimen_id` | `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` plus Specimen `{path: "value", name: "specimen_id_str"}` under the lab identifier group | `Reference(Specimen)` plus identifier `string` | `STRING` | `CAST(specimen_id_str AS INTEGER)`; group and output natural key |
| `itemid` | under the lab coding group `{path: "code", name: "code"}` | `code` | `STRING` | exact text code or `CAST(code AS INTEGER)` |
| coding system | under the lab coding group `{path: "system", name: "system"}` | `uri` | `STRING` | exact discriminator |
| item label | under the lab coding group `{path: "display", name: "display"}` | `string` | `STRING` | informational only; never filter on it |
| `charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | `STRING` | `CAST(... AS TIMESTAMP_NTZ)` before `MAX` |
| alternate effective variant | `{path: "(effective).ofType(Period).start", name: "effective_period_start"}` | `Period.start` `dateTime` | `STRING` | 0/11,908 in target; diagnostic fallback only |
| alternate effective variant | `{path: "(effective).ofType(instant)", name: "effective_instant"}` | `instant` | `TIMESTAMP` | 0/11,908 in target; diagnostic fallback only |
| `valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value` `decimal` | `STRING` | `CAST(... AS DOUBLE)`; exclude comparator-bearing synthesized values |
| source-text comparator marker | `{path: "(value).ofType(Quantity).comparator", name: "quantity_comparator"}` | `Quantity.comparator` `code` | `STRING` | require `IS NULL` for this source's `valuenum IS NOT NULL` branch |
| source unit (not selected by SQL) | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | `string` | `STRING` | informational; source SQL uses itemid branches, not unit |
| Quantity code (not selected by SQL) | `{path: "(value).ofType(Quantity).code", name: "quantity_code"}` | `code` | `STRING` | informational only |
| source `value` / comments (not selected by SQL) | `{path: "(value).ofType(string)", name: "value_string"}` | `string` | `STRING` | never substitute for `valuenum`; text rows are excluded |

Every pivoted output value comes from `quantity_value` after the exact source
item branch, `/1000.0` conversion where specified, independent `MAX` by
`specimen_id`, and the source imputation/rounding rules. The five rounded
absolute outputs are final `DECIMAL(38,4)`; WBC and all percentage/other
outputs are final `DOUBLE`.

## Coded-filter confirmation

The observed coding system was exactly:

```text
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems
```

The coding projection produced 11,908 coding rows over 11,908 distinct
targeted Observation resources: **1.000 coding per resource**. The
discriminator is `system + exact code`, never `meta.profile`. The system and
code are sufficient here because the source stream is labevents and the code
is the verbatim itemid; profile metadata is warehouse-version dependent.

Counts below are `Delta total / Delta Quantity.value non-null / Delta
comparator non-null / DuckDB source total / DuckDB valuenum non-null and >= 0`.
The final source-faithful eligible count is Quantity non-null, comparator NULL,
and nonnegative.

| itemid | Delta total | Quantity | comparator | source total | source eligible |
|---:|---:|---:|---:|---:|---:|
| 51146 | 943 | 938 | 0 | 943 | 938 |
| 52069 | 569 | 565 | 0 | 569 | 565 |
| 51199 | 0 | 0 | 0 | 0 | 0 |
| 51200 | 943 | 939 | 0 | 943 | 939 |
| 52073 | 569 | 565 | 0 | 569 | 565 |
| 51244 | 943 | 939 | 0 | 943 | 939 |
| 51245 | 16 | 16 | 0 | 16 | 16 |
| 51133 | 569 | 565 | 0 | 569 | 565 |
| 52769 | 16 | 16 | 0 | 16 | 16 |
| 51253 | 0 | 0 | 0 | 0 | 0 |
| 51254 | 943 | 939 | 0 | 943 | 939 |
| 52074 | 569 | 565 | 0 | 569 | 565 |
| 51256 | 943 | 939 | 0 | 943 | 939 |
| 52075 | 569 | 565 | 0 | 569 | 565 |
| 51143 | 404 | 404 | 0 | 404 | 404 |
| 51144 | 395 | 395 | 0 | 395 | 395 |
| 51218 | 2 | 2 | 0 | 2 | 2 |
| 52135 | 227 | 226 | 0 | 227 | 226 |
| 51251 | 397 | 397 | 0 | 397 | 397 |
| 51257 | 115 | 115 | 0 | 115 | 115 |
| 51300 | 16 | 16 | 0 | 16 | 16 |
| 51301 | 2,760 | 2,759 | 0 | 2,760 | 2,759 |
| 51755 | 0 | 0 | 0 | 0 | 0 |

Totals: 11,908 targeted rows; 11,865 source numeric eligible rows; 11,865
FHIR Quantity rows with comparator NULL and nonnegative numeric value. The demo
has no negative value in this code set. The 43 non-Quantity rows are text
values, including one item `51301` `valueString='___'`; that row has no
`valueQuantity` and is correctly excluded.

The attempt-0001 full-data diagnosis identified the five problematic rows:
specimens `21438597`, `27736375`, `34063806`, `55540346`, and `72269481`, all
item `51301`, source `value='<0.1'` with `valuenum=NULL`. The served full-data
FHIR representation was Quantity `value=0.1`, `comparator='<'`, with no
`valueString`. The upstream transform is
`mimic-fhir/sql/fhir_observation_labevents.sql:27-47,123-136`.

## Field population and oracle checks

Counts over the 11,908 targeted demo Observation rows:

| Mapped alias | Total | Non-null |
|---|---:|---:|
| `observation_key` | 11,908 | 11,908 |
| `patient_key` | 11,908 | 11,908 |
| `encounter_key` | 11,908 | 6,408 |
| `specimen_key` | 11,908 | 11,908 |
| joined `specimen_id_str` | 11,908 | 11,908 |
| `effective_datetime` | 11,908 | 11,908 |
| `effective_period_start` | 11,908 | 0 |
| `effective_instant` | 11,908 | 0 |
| `quantity_value` | 11,908 | 11,865 |
| `quantity_comparator` | 11,908 | 0 |
| `quantity_unit` | 11,908 | 11,865 |
| `quantity_code` | 11,908 | 11,865 |
| `value_string` | 11,908 | 43 |
| `code` | 11,908 | 11,908 |
| `system` | 11,908 | 11,908 |
| `display` | 11,908 | 11,908 |

The relevant Observation-to-Specimen and Observation-to-Patient joins were
11,908/11,908. Hospital Encounter references were 6,408/11,908, matching the
non-NULL source `hadm_id` population for the targeted demo rows.

For the cheap row-level check, the 11,865 source rows with
`valuenum IS NOT NULL AND valuenum >= 0` were compared to FHIR Quantity rows
using `(specimen_id, itemid, effective wall-clock time)`. There were 11,864
matching keys and one row on each side. All 11,864 matching Quantity values
agreed exactly with `valuenum` (11,864/11,864). The sole key difference is the
known DST normalization: source specimen `55500529`, item `51301`, is
`2116-03-08 02:52:00`, while FHIR effective time is `03:52:00`; the value is
`0.1` on both sides. Use `TIMESTAMP_NTZ`, not an offset-aware conversion.

## Gaps

* **`hadm_id`: absent but only heuristically derivable when the Encounter
  reference is missing.** The demo target had a complete match for all
  6,408 non-NULL source admissions, but the curated notes show this is not a
  universal guarantee. Preserve a missing value with a `LEFT JOIN` and typed
  nullable `INTEGER`; patient-plus-time matching is an approximation, not an
  exact inversion.
* **`charttime`: not representable exactly for DST-gap rows.** The FHIR ETL
  writes an already-normalized timestamp. The original wall-clock value cannot
  be recovered by another FHIRPath; the observed demo discrepancy was 1 of
  11,865 eligible source rows (and one grouped specimen).
* **Unselected source fields:** `labevents.value`, `valueuom`, `comments`,
  `storetime`, reference ranges, flags, and the source `labevent_id` are not
  part of the canonical output. `value_string` is projectable for diagnosis,
  but is not a representation of `valuenum` and must not enter the numeric
  pivots.
* **No terminology gap:** the itemids are carried verbatim in the proprietary
  lab system. No LOINC mapping is specified or required.

## Notes and fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping were:

* identifier values are strings while resource/reference keys are UUIDs;
* itemid-derived Observation codes are verbatim and require system + exact
  code, not `meta.profile`;
* lab Observation specimens preserve `specimen_id` through the lab Specimen
  identifier;
* lab Observation encounter references are incomplete, requiring a left join;
* Quantity ViewDefinition aliases are string-like and require numeric casts;
* datetimes require `TIMESTAMP_NTZ`, with the DST-gap loss documented; and
* Delta tables, not stale ndjson, are authoritative.

I read `MIMIC_NOTES.d/README.md` and the current provisional
`MIMIC_NOTES.d/blood_differential.md`. The fragment's comparator-synthesis
claim was checked against the attempt-0001 full-data diagnosis and the ETL
SQL; the current demo Delta did not contain a `<0.1` row, so it independently
verified the ordinary numeric/text split but did not reproduce the comparator
case. No new dataset-wide claim was needed, so no section was appended to the
fragment and `MIMIC_NOTES.md` was not edited.
