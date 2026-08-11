# FHIR probe and mapping: `complete_blood_count`

**Attempt:** `attempt_0001`  
**Probed:** 2026-08-11  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB 1.5.5, read-only

No HTTP Pathling server or raw NDJSON was used. The Delta warehouse is the
authoritative served data for this mapping.

## Source contract and target shape

The source analyst identifies only `mimiciv_hosp.labevents`, with a positive
numeric filter and a specimen-level pivot:

```sql
itemid IN (51221, 51222, 51248, 51249, 51250,
           51265, 51279, 51277, 52159, 51301)
AND valuenum IS NOT NULL
AND valuenum > 0
GROUP BY specimen_id
```

The full oracle manifest requires 13 output columns, a `keyed_join` comparison,
natural key `specimen_id`, and 3,362,503 full-data rows:

```text
subject_id   INTEGER
hadm_id      INTEGER (nullable)
charttime    TIMESTAMP
specimen_id  INTEGER
hematocrit   DOUBLE
hemoglobin   DOUBLE
mch          DOUBLE
mchc         DOUBLE
mcv          DOUBLE
platelet     DOUBLE
rbc          DOUBLE
rdw          DOUBLE
rdwsd        DOUBLE
wbc          DOUBLE
```

`specimen_id` is not an Observation UUID. It is recovered exactly from the
Observation-to-Specimen reference and the lab Specimen identifier, then used
as the grouping/pivot key. The source has no joins, but the FHIR query needs
Patient, Specimen, and hospital Encounter support views to recover the source
identifiers.

## Source table to FHIR resource mapping

| Source table/role | FHIR resource | Exact discriminator or join |
|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` generated from labevents | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` and exact string `code` |
| `labevents.subject_id` | `Patient` | `Observation.subject.getReferenceKey(Patient)` → `Patient.getResourceKey()`; emit the patient identifier value, not the UUID |
| `labevents.hadm_id` | hospital `Encounter` | `Observation.encounter.getReferenceKey(Encounter)` → hospital Encounter UUID; use the `encounter-hosp` identifier value, with a `LEFT JOIN` |
| `labevents.specimen_id` | lab `Specimen` | `Observation.specimen.getReferenceKey(Specimen)` → `Specimen.getResourceKey()`; use the `specimen-lab` identifier value |
| `specimen_id` grouping | lab `Specimen` | group on `CAST(specimen_id_str AS INTEGER)`, not on patient/time or Observation UUID |

The current demo has 813,540 Observation resources, 12,458 Specimens, 100
Patients, and 637 Encounters. The target lab coding system is one of several
Observation systems in the warehouse; it is the only system used for this
source stream. The target system had 107,727 coding rows over 107,727 distinct
resources, a ratio of **1.000 coding/resource**. The CBC subset had 25,087
coding rows over 25,087 distinct resources, also **1.000**. The discriminator
is system plus exact code, never `meta.profile`.

All observed Observation systems and coding ratios were:

```text
.../mimic-chartevents-d-items       668862 / 668862 = 1.000
.../mimic-d-labitems                107727 / 107727 = 1.000
.../mimic-d-items                    24642 / 24642  = 1.000
http://loinc.org                      9042 / 9042   = 1.000
.../mimic-microbiology-test           1893 / 1893   = 1.000
.../mimic-microbiology-antibiotic     1036 / 1036   = 1.000
.../mimic-microbiology-organism        338 / 338    = 1.000
```

The lab system is therefore required before the literal code filter. No
outputevents/datetimeevents shared-system ambiguity applies to this
labevents-only concept.

## Canonical ViewDefinition projections

These are the exact `{path, name}` projections. `_key`/`_str` aliases are
recommended in implementation SQL to keep UUID join keys and final MIMIC IDs
distinct; the canonical resource-key names below show the FHIR meaning.

### Observation (labevents stream)

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "resource": "Observation",
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_id"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_id"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id"},
        {"path": "specimen.getReferenceKey(Specimen)", "name": "specimen_id"},
        {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
        {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
        {"path": "(value).ofType(Quantity).code", "name": "quantity_code"},
        {"path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator"},
        {"path": "(value).ofType(string)", "name": "value_string"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
        {"path": "(effective).ofType(Period).end", "name": "effective_period_end"},
        {"path": "(effective).ofType(instant)", "name": "effective_instant"}
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')",
      "column": [
        {"path": "code", "name": "code"},
        {"path": "system", "name": "system"},
        {"path": "display", "name": "display"}
      ]
    }
  ]
}
```

FHIR semantic types and observed materialized Spark types:

| Role | Canonical `{path, name}` | FHIR type | Observed Pathling type / output use |
|---|---|---|---|
| Observation primary key (support only) | `{ "path": "getResourceKey()", "name": "observation_id" }` | resource key string | `STRING` UUID; never source `labevent_id` or output key |
| Patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `Reference(Patient)` | `STRING` UUID; join to Patient |
| Encounter reference | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }` | `Reference(Encounter)` | nullable `STRING` UUID; left join |
| Specimen reference | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_id" }` | `Reference(Specimen)` | `STRING` UUID; join/group support |
| `labevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal | materialized `STRING`; cast to `DOUBLE` |
| `labevents.valueuom` (not an output column) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | string | materialized `STRING`; 25,011/25,087 non-null |
| Quantity code (not an output column) | `{ "path": "(value).ofType(Quantity).code", "name": "quantity_code" }` | code | materialized `STRING`; 25,011/25,087 non-null |
| Comparator diagnostic | `{ "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" }` | code | materialized `STRING`; 0/25,087 in demo |
| Source text fallback (not numeric) | `{ "path": "(value).ofType(string)", "name": "value_string" }` | string | materialized `STRING`; 76/25,087; exclude from numeric filter |
| `labevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` | materialized `STRING` with offset; cast to `TIMESTAMP_NTZ` |
| Alternate effective choice | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` dateTime | `STRING`, 0/25,087 |
| Alternate effective choice | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `Period.end` dateTime | `STRING`, 0/25,087 |
| Alternate effective choice | `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | `instant` | native Spark `TIMESTAMP`, 0/25,087; do not coalesce |
| `labevents.itemid` | coding `{ "path": "code", "name": "code" }` inside the constrained `forEach` | code | `STRING`; exact itemid text |
| Coding system | coding `{ "path": "system", "name": "system" }` | uri | `STRING`; exact lab system |
| Dimension label | coding `{ "path": "display", "name": "display" }` | string | `STRING`; 25,087/25,087 non-null |

The raw encoded `Observation.valueQuantity.value` is decimal, but the
ViewDefinition alias is string-like. Cast it before numeric `MAX` pivots.
The effective target is dateTime-only in the demo; projecting the empty choice
aliases is useful diagnostic evidence, but only the dateTime alias should feed
the output.

### Patient identifier spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "patient_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
  ]
}
```

`patient_id` is a UUID-like `STRING` join key. `subject_id_str` is FHIR
`Identifier.value`, a `string`/`VARCHAR`; cast it to final `subject_id INTEGER`.
The demo Patient view had 100/100 non-null patient identifiers and 100 distinct
resource keys (and 100/100 non-null `patient_key` values). All 25,087 target
Observation rows joined to a Patient.

### Specimen grouping spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "specimen_id"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", "name": "specimen_id_str"},
    {"path": "type.coding.code", "name": "specimen_type_code"},
    {"path": "type.coding.system", "name": "specimen_type_system"},
    {"path": "type.coding.display", "name": "specimen_type_display"},
    {"path": "collection.collected.ofType(dateTime)", "name": "specimen_collected_datetime"}
  ]
}
```

The resource key/reference key is a `STRING` UUID. `specimen_id_str` is a
FHIR `string`/materialized `STRING` and is the exact relational
`labevents.specimen_id`; cast it to final `specimen_id INTEGER`. The specimen
type paths are FHIR `code`/`uri`/`string`, and collection is FHIR `dateTime`
materialized as a string. In the full Specimen table, 11,122/12,458 resources
have the `specimen-lab` identifier; `specimen_key`, `specimen_patient_key`,
type code, and type system are each non-null 12,458/12,458, type display is
non-null 1,336/12,458, and collection dateTime is non-null 12,413/12,458.
Among the 2,964 target specimen groups, all 2,964 joined to the identifier,
had a type code/system, and had collection dateTime; lab
`type.coding.display` was null for all 2,964. The type and collection fields
are not output by this concept.

### Hospital Encounter identifier spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "encounter_id"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str"},
    {"path": "period.start", "name": "encounter_period_start"},
    {"path": "period.end", "name": "encounter_period_end"}
  ]
}
```

`encounter_id` and `patient_id` are `STRING` UUID join keys. `hadm_id_str` is a
FHIR `string`/materialized `STRING`; cast it to nullable final
`hadm_id INTEGER`. Filter the Encounter view by the hospital identifier
system, never by `Encounter.class`, and `LEFT JOIN` it from Observation. The
The full Encounter view had 637/637 non-null `encounter_key` and
`encounter_patient_key` values, 275/637 non-null hospital identifiers, and
637/637 non-null period starts and ends. Of
25,087 target coded observations, 19,573 had an Encounter reference resolving
to a hospital identifier and 5,514 had no reference. The corresponding source
numeric observations had the same 19,573 non-null `hadm_id` rows; the grouped
output comparison also agreed including nulls.

## Exact itemid-to-FHIR-code mapping and counts

The source itemids are carried verbatim as string `Observation.code.coding.code`
under the one lab system. No LOINC translation is used. Counts are
**Delta coded rows / Delta Quantity.value rows / DuckDB source rows /
DuckDB rows satisfying `valuenum IS NOT NULL AND valuenum > 0`**. The source
raw query is the same ten-item allowlist before the positive numeric filter.

| Itemid | Source SQL output | FHIR system | Exact FHIR code | Delta coded | Delta Quantity | Source raw | Source eligible |
|---:|---|---|---:|---:|---:|---:|---:|
| 51221 | `hematocrit` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | `"51221"` | 2,913 | 2,908 | 2,913 | 2,908 |
| 51222 | `hemoglobin` | same | `"51222"` | 2,787 | 2,785 | 2,787 | 2,785 |
| 51248 | `mch` | same | `"51248"` | 2,760 | 2,748 | 2,760 | 2,748 |
| 51249 | `mchc` | same | `"51249"` | 2,760 | 2,748 | 2,760 | 2,748 |
| 51250 | `mcv` | same | `"51250"` | 2,760 | 2,748 | 2,760 | 2,748 |
| 51265 | `platelet` | same | `"51265"` | 2,827 | 2,820 | 2,827 | 2,820 |
| 51279 | `rbc` | same | `"51279"` | 2,760 | 2,748 | 2,760 | 2,748 |
| 51277 | `rdw` | same | `"51277"` | 2,760 | 2,747 | 2,760 | 2,747 |
| 52159 | `rdwsd` | same | `"52159"` | 0 | 0 | 0 | 0 |
| 51301 | `wbc` | same | `"51301"` | 2,760 | 2,759 | 2,760 | 2,759 |
| **total** | — | one system | — | **25,087** | **25,011** | **25,087** | **25,011** |

`52159` is a dead literal in this demo: it exists in `d_labitems` as
`Platelet Aggregation`, but has no raw labevents row and no served Observation
row. The source comment calls it RDW SD; the literal and output name remain
unchanged because the canonical SQL is authoritative. This is a concept-level
dead filter, not a reason to remove the required `rdwsd` output column.

The observed non-null field counts over the 25,087 target coded rows were:

```text
observation_key 25087/25087   patient_key 25087/25087
encounter_key   19573/25087   specimen_key 25087/25087
code           25087/25087    system      25087/25087
display        25087/25087    effective_datetime 25087/25087
period_start       0/25087    period_end          0/25087
effective_instant  0/25087    quantity_value 25011/25087
quantity_unit  25011/25087    quantity_code 25011/25087
quantity_comparator 0/25087   value_string  76/25087
```

The per-code Delta counts were also checked: the five non-Quantity rows for
51221, two for 51222, twelve each for 51248/51249/51250, seven for 51265,
thirteen for 51277, twelve for 51279, and one for 51301 sum to 76. There were
no comparator-bearing target rows and no non-positive Quantity rows in this
code set.

## Filtering, joins, grouping, and effective time

The FHIR-side extraction must retain both numeric and string value choices and
the comparator diagnostic. On this demo the source-equivalent eligible
predicate is:

```sql
quantity_value IS NOT NULL
AND quantity_comparator IS NULL
AND TRY_CAST(quantity_value AS DOUBLE) > 0
```

It returns 25,011 rows, exactly the DuckDB source `valuenum IS NOT NULL AND
valuenum > 0` population. `value_string` is not a numeric fallback. The
labevents ETL can synthesize a Quantity from comparator text when relational
`valuenum` is null; retain `quantity_comparator` so such rows are not silently
treated as source numeric values. There were no such comparator rows in this
demo CBC subset. If a full-data comparator-bearing row is encountered, it needs
source-side diagnosis because FHIR does not preserve the relational
`valuenum-is-non-null` provenance bit.

Join sequence:

1. Filter the Observation coding group by the lab system and the ten exact
   string codes.
2. Keep only the source-equivalent numeric Quantity branch.
3. `LEFT JOIN` Patient on `Observation.subject.getReferenceKey(Patient)` to
   `Patient.getResourceKey()` and cast `subject_id_str` to integer.
4. `LEFT JOIN` lab Specimen on `Observation.specimen.getReferenceKey(Specimen)`
   to `Specimen.getResourceKey()`, then cast `specimen_id_str` to integer.
5. `LEFT JOIN` hospital Encounter on
   `Observation.encounter.getReferenceKey(Encounter)` to the hospital
   Encounter key and cast `hadm_id_str` to nullable integer.
6. Cast the dateTime string directly to `TIMESTAMP_NTZ`; group by integer
   `specimen_id` and independently take `MAX` for subject, admission,
   charttime, and each conditional item pivot.

The target had 2,964 specimen groups before the numeric filter and 2,959 after
it. The source and FHIR candidate both had 2,959 eligible groups. Do not use
patient plus time as the grouping key.

`Observation.effectiveDateTime` comes from the ETL's
`CAST(lab.charttime AS TIMESTAMPTZ)` (`mimic-fhir/sql/fhir_observation_labevents.sql:15,121`).
Its offset is not a real instant for de-identified MIMIC wall-clock values.
`CAST(effective_datetime AS TIMESTAMP_NTZ)` preserves the served wall-clock
text. An offset-aware conversion or a mixed `COALESCE` with the empty native
instant alias shifts values. One eligible grouped CBC specimen exposed the
known irreversible DST-gap rewrite: specimen `55500529`, source
`2116-03-08 02:52:00`, served FHIR `03:52:00`.

## Oracle checks

The source positive-numeric row query returned 25,011 rows; the FHIR numeric
Quantity query returned 25,011. `(specimen_id,itemid)` was unique on both sides
in the demo. The row-level merge had 25,011/25,011 matching keys and:

```text
subject_id  25011/25011 exact
hadm_id     25011/25011 exact, including NULLs
valuenum    25011/25011 exact
charttime   25002/25011 exact; 9 row observations share the one DST-gap specimen
```

For the specimen-level output, the source and candidate key merge was
2,959/2,959 (`both`), with no left-only or right-only keys:

```text
subject_id  2959/2959 exact
hadm_id     2959/2959 exact, including NULLs
hematocrit  2959/2959 exact
hemoglobin  2959/2959 exact
mch         2959/2959 exact
mchc        2959/2959 exact
mcv         2959/2959 exact
platelet    2959/2959 exact
rbc         2959/2959 exact
rdw         2959/2959 exact
rdwsd       2959/2959 exact (all NULL in the demo)
wbc         2959/2959 exact
charttime   2958/2959 exact; sole difference is the DST-gap specimen above
```

The supporting patient/specimen identifier joins were 25,087/25,087. The
hospital Encounter join was 19,573/25,087, exactly matching the non-null source
admission population for the target observations.

## Gaps and representability

* **`hadm_id` — absent but heuristically approximable when the Encounter
  reference is missing.** The exact FHIR path is available for referenced
  observations; when the reference is absent, no FHIR element carries the
  relational admission ID. A patient-plus-`effectiveDateTime` window against
  hospital Encounter periods was measured on the 2,959 grouped CBC rows:
  2,305 unique matches, 0 ambiguous matches, 654 no matches; 2,294/2,336
  source-non-null admissions matched, and 11 unique guesses were false
  positives where the oracle `hadm_id` was NULL. Leaving unmatched values NULL
  gives 2,948/2,959 (99.63%) exact rows, but the heuristic is not an exact
  inversion and must not manufacture an ID. Use a left join and typed nullable
  `INTEGER`.
* **`charttime` — not representable exactly for DST-gap rows.** The FHIR ETL
  has already normalized the nonexistent source wall-clock time, and no other
  FHIRPath recovers the original. The measured demo agreement is 2,958/2,959
  grouped rows. Preserve the FHIR wall-clock value with `TIMESTAMP_NTZ` rather
  than applying a second timezone conversion.
* **Source numeric provenance — not fully representable in the general case.**
  FHIR can carry a Quantity synthesized from comparator text when source
  `valuenum` was NULL, and can carry source/comments text in `valueString`, but
  it does not carry a flag saying which relational branch produced it. This
  demo has an exact split (25,011 Quantity rows versus 76 string rows and zero
  comparators), so the source filter is reproducible here. Do not use text as a
  numeric approximation.
* **`specimen_id` — absent as a direct scalar on Observation but exactly
  derivable.** The reference plus lab Specimen identifier reproduced all
  25,087 target rows and all 2,959 grouping keys; this is not a gap.
* `labevent_id`, `value`, `valueuom`, `comments`, `storetime`, flags, reference
  ranges, and dimension fields are not selected by the canonical SQL. The
  Observation UUID is support-only and is not an invertible output mapping for
  `labevent_id`; no extra output columns should be added.

## Curated notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping were:

* Delta tables, not stale NDJSON, are authoritative.
* Itemid-derived Observation codes are verbatim and require the exact
  `mimic-d-labitems` system plus string code; no LOINC translation and no
  `meta.profile` discriminator.
* `d_labitems` has no v2.2 LOINC mapping.
* MIMIC identifiers live in string-valued `identifier.value`, while resource
  and reference keys are UUID strings; final IDs must be cast to integers.
* Lab Observation specimens preserve `specimen_id` through the
  `specimen-lab` identifier.
* Lab Observation Encounter references are incomplete, so the Encounter join
  must be left-sided and patient/time estimation must not manufacture IDs.
* Quantity value aliases materialize as strings and require a numeric cast.
* FHIR datetimes carry offsets but must be cast to `TIMESTAMP_NTZ`; the
  DST-gap rewrite is intrinsically unrecoverable.
* Lab `valueString` may be a source text/comments fallback and is not a
  numeric `valuenum` substitute.

I read and treated as provisional leads all current fragments:
`MIMIC_NOTES.d/README.md`, `blood_differential.md`, `chemistry.md`,
`coagulation.md`, `cardiac_marker.md`, and `code_status.md`. The comparator
synthesis warning in `blood_differential.md` and `coagulation.md` was checked
against `mimic-fhir/sql/fhir_observation_labevents.sql:27-47,123-136`; CBC had
0 comparator-bearing rows in the demo, so the ETL rule was verified but the
provisional full-data example was not reproduced for this item set. The
chemistry/coagulation datetime and Quantity-cast warnings were independently
confirmed by the CBC projections and the exact grouped comparison. The
cardiac-marker system-before-integer-cast warning was confirmed by the
constrained lab-system `forEach`; `code_status.md` is chartevents-specific and
did not change this labevents mapping. No other fragment was present.

I appended one dataset-wide finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/complete_blood_count.md`: the labevents
ETL can synthesize a FHIR Quantity from comparator text when relational
`valuenum` is NULL, so numeric ports must retain the comparator diagnostic and
not treat every Quantity as source numeric data. This is provisional until a
human merges it into `MIMIC_NOTES.md`.

No implementation artifact or attempt file was authored. This reusable mapping
is the carryover artifact at
`mimic-iv/concepts_fhir/carryover/complete_blood_count/fhir-prober.md`.
