# FHIR probe: `chemistry`

## Scope and source contract

The source analysis at `carryover/chemistry/source-analyst.md` and the
canonical SQL `mimic-iv/concepts/measurement/chemistry.sql` describe one raw
source table, `mimiciv_hosp.labevents`, with no joins.  The result is a wide
specimen-level pivot: one row per `specimen_id`, not one row per
`labevent_id` or per analyte.  The active itemids are exactly

```
50862, 50930, 50976, 50868, 50882, 51006,
50893, 50902, 50912, 50931, 50983, 50971
```

The commented point-of-care literals `52456`, `52502`, `52525`, `52566`,
`52579`, and `52603` are not filters and must not be added.  The relational
predicates are `valuenum IS NOT NULL`, `(valuenum > 0 OR itemid = 50868)`,
and the per-analyte upper bounds in the source analysis.  There is no time
window, unit filter, or admission filter in the source SQL.

## Resource mapping

| Source stream/role | MIMIC-on-FHIR resource | FHIR spine |
|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` (`mimic-observation-labevents`) | `code.coding` carries the lab itemid; `subject`, `encounter`, `specimen`, `value[x]`, and `effective[x]` carry the row fields |
| `labevents.specimen_id` grouping spine | `Specimen` (`specimen-lab`) | `Observation.specimen.getReferenceKey(Specimen)` joins to `Specimen.identifier` with system `http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab` |
| identifier helper | `Patient` | `Observation.subject.getReferenceKey(Patient)` joins to `Patient.getResourceKey()`; the source `subject_id` is the patient identifier value |
| nullable admission helper | `Encounter` (hospital stream only) | `Observation.encounter.getReferenceKey(Encounter)` joins to the hospital Encounter identifier value; the join is LEFT, never INNER |

The FHIR Observation `getResourceKey()` is a UUID and is not the source
`labevent_id`; `labevent_id` is not selected by the chemistry SQL.  The output
natural key is `specimen_id`, recovered from the lab Specimen identifier.

## Canonical `{path, name}` projections and FHIR types

The following are the reusable column groups.  The type in parentheses is the
type of the materialized Pathling/ViewDefinition alias, not the final oracle
type.  Pathling materializes the relevant identifier, datetime, and Quantity
aliases as `VARCHAR`; the implementer must cast the numeric/date aliases in
the final SQL.

### Observation

Flat columns:

```text
{ "path": "getResourceKey()",                         "name": "observation_key" }       -- VARCHAR UUID
{ "path": "subject.getReferenceKey(Patient)",       "name": "patient_key" }           -- VARCHAR UUID reference
{ "path": "encounter.getReferenceKey(Encounter)",   "name": "encounter_key" }         -- VARCHAR UUID reference, nullable
{ "path": "specimen.getReferenceKey(Specimen)",     "name": "specimen_key" }          -- VARCHAR UUID reference
{ "path": "(value).ofType(Quantity).value",         "name": "quantity_value" }         -- VARCHAR, cast DOUBLE
{ "path": "(value).ofType(Quantity).unit",          "name": "quantity_unit" }          -- VARCHAR
{ "path": "(value).ofType(Quantity).comparator",    "name": "quantity_comparator" }    -- VARCHAR, nullable
{ "path": "(value).ofType(string)",                 "name": "value_string" }           -- VARCHAR, nullable
{ "path": "(value).ofType(CodeableConcept).text",   "name": "value_cc_text" }          -- VARCHAR, nullable; not used
{ "path": "(effective).ofType(dateTime)",           "name": "effective_datetime" }    -- VARCHAR ISO datetime, cast TIMESTAMP_NTZ
{ "path": "(effective).ofType(Period).start",      "name": "effective_period_start" } -- VARCHAR, observed empty
{ "path": "(effective).ofType(Period).end",        "name": "effective_period_end" }   -- VARCHAR, observed empty
```

The coding group must be constrained inside the iteration, before any integer
cast:

```text
forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')"

{ "path": "code",    "name": "item_code" }    -- VARCHAR, exact itemid text
{ "path": "system",  "name": "item_system" }  -- VARCHAR
{ "path": "display", "name": "item_display" } -- VARCHAR, dimension label
```

The source `itemid` is therefore `CAST(item_code AS INTEGER)` only after the
system and exact string-code filter.  Do not use `meta.profile`; the curated
notes say the Observation profile representation is warehouse-version
dependent.

### Specimen, Patient, and Encounter helper projections

```text
{ "path": "getResourceKey()", "name": "specimen_key" } -- Specimen, VARCHAR UUID
{ "path": "subject.getReferenceKey(Patient)", "name": "specimen_patient_key" } -- VARCHAR UUID
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value",
  "name": "specimen_id_str" } -- VARCHAR, cast INTEGER
{ "path": "type.coding.code",    "name": "specimen_type_code" } -- VARCHAR
{ "path": "type.coding.system",  "name": "specimen_type_system" } -- VARCHAR
{ "path": "type.coding.display", "name": "specimen_type_display" } -- VARCHAR, null in served lab data
{ "path": "collection.collected.ofType(dateTime)", "name": "specimen_collected_datetime" } -- VARCHAR

{ "path": "getResourceKey()", "name": "patient_key" } -- Patient, VARCHAR UUID
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value",
  "name": "subject_id_str" } -- VARCHAR, cast INTEGER

{ "path": "getResourceKey()", "name": "encounter_key" } -- Encounter, VARCHAR UUID
{ "path": "subject.getReferenceKey(Patient)", "name": "encounter_patient_key" } -- VARCHAR UUID
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value",
  "name": "hadm_id_str" } -- VARCHAR, cast INTEGER, nullable
{ "path": "period.start", "name": "encounter_period_start" } -- VARCHAR datetime
```

Only the hospital identifier system is valid for `hadm_id`.  Encounter
`class` is not a discriminator.  The four identifier systems and their
meaning are established in `MIMIC_NOTES.md`; the hospital stream is
`.../identifier/encounter-hosp`.

## Source column to FHIRPath mapping

| Source column | FHIR path(s) and canonical alias | FHIR alias type | Final chemistry type / use |
|---|---|---|---|
| `le.subject_id` | `Observation.subject.getReferenceKey(Patient)` → `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}`; join to `Patient.identifier.where(system='.../identifier/patient').value` → `{path: "identifier.where(system='.../identifier/patient').value", name: "subject_id_str"}` | `VARCHAR` UUID join key and `VARCHAR` identifier | `CAST(subject_id_str AS INTEGER)` → output `subject_id INTEGER`; source is non-null |
| `le.hadm_id` | `Observation.encounter.getReferenceKey(Encounter)` → `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}`; join to hospital Encounter `{path: "identifier.where(system='.../identifier/encounter-hosp').value", name: "hadm_id_str"}` | nullable `VARCHAR` UUID and nullable `VARCHAR` identifier | `CAST(hadm_id_str AS INTEGER)` → output `hadm_id INTEGER` nullable; LEFT join only |
| `le.charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `VARCHAR` ISO datetime with offset | `CAST(effective_datetime AS TIMESTAMP_NTZ)` → output `charttime TIMESTAMP`; preserves the FHIR wall-clock text, not an instant conversion |
| `le.specimen_id` | `Observation.specimen.getReferenceKey(Specimen)` → `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}`; join to `{path: "identifier.where(system='.../identifier/specimen-lab').value", name: "specimen_id_str"}` | nullable `VARCHAR` UUID and `VARCHAR` identifier | `CAST(specimen_id_str AS INTEGER)` → output `specimen_id INTEGER`; group/pivot key |
| `le.itemid` | constrained `forEach` over `code.coding.where(system='.../CodeSystem/mimic-d-labitems')`: `{path: "code", name: "item_code"}` plus `{path: "system", name: "item_system"}` and `{path: "display", name: "item_display"}` | `VARCHAR` code/system/display | `CAST(item_code AS INTEGER)` after exact filter; drives the twelve CASE outputs |
| `le.valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `VARCHAR` in a materialized ViewDefinition | `CAST(quantity_value AS DOUBLE)`; source `valuenum IS NOT NULL`, positivity, and analyte upper bound are applied before the specimen pivot |
| `le.valueuom` (not referenced by source SQL) | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | `VARCHAR` | Supplemental unit evidence only; the chemistry output has no unit column. Demo eligible units matched exact source values 26,763/26,763 |
| `le.value` (not referenced by source SQL) | `{path: "(value).ofType(string)", name: "value_string"}` and, when ETL parsing succeeds, Quantity value/comparator | `VARCHAR` | Never use `value_string` as `valuenum`; it can be a source text value or a comments fallback |
| `le.comments` (not referenced by source SQL) | no direct source-preserving output; ETL may place it in `Observation.value.ofType(string)` when both numeric and source text are absent | `VARCHAR` if projected | Not part of chemistry; observed `___` and `<3*.` fallbacks must not satisfy the numeric filter |
| `le.labevent_id` (not referenced or selected) | `Observation.getResourceKey()` → `{path: "getResourceKey()", name: "observation_key"}` | `VARCHAR` UUID | Not an output column and not invertible to the relational integer; do not use as the chemistry key |

## Exact itemid-to-output mapping

The FHIR code is a verbatim string form of the source itemid.  The twelve
active codes and their chemistry output columns are:

| Itemid | FHIR code filter | Output CASE column | Upper bound |
|---:|---|---|---:|
| 50862 | `code='50862'` | `albumin` | 10 |
| 50930 | `code='50930'` | `globulin` | 10 |
| 50976 | `code='50976'` | `total_protein` | 20 |
| 50868 | `code='50868'` | `aniongap` | 10000 |
| 50882 | `code='50882'` | `bicarbonate` | 10000 |
| 51006 | `code='51006'` | `bun` | 300 |
| 50893 | `code='50893'` | `calcium` | 10000 |
| 50902 | `code='50902'` | `chloride` | 10000 |
| 50912 | `code='50912'` | `creatinine` | 150 |
| 50931 | `code='50931'` | `glucose` | 10000 |
| 50983 | `code='50983'` | `sodium` | 200 |
| 50971 | `code='50971'` | `potassium` | 30 |

`50868` is the only code allowed to pass the non-positive-value exception.
The upper bound belongs in each CASE expression: a row above the bound still
keeps its specimen group but contributes NULL to that analyte.

## Served-data probes and confirmed code set

All counts below are from the authoritative Delta warehouse
`/Users/nau025/warehouses/mimic-iv-demo/delta`, using embedded Pathling 9.6.0
on Spark 4.0.2.  The Observation probe projected `forEach: "code.coding"`
and then grouped by `system` and exact `code`.

The distinct Observation code systems were:

```text
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items     668,862 rows/resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems              107,727 rows/resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items                  24,642 rows/resources
http://loinc.org                                                          9,042 rows/resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-test        1,893 rows/resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-antibiotic  1,036 rows/resources
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism      338 rows/resources
```

For the lab stream, coding fan-out is exactly `107,727 / 107,727 = 1.000`
codings per resource.  The chemistry codes have `26,767 / 26,767 = 1.000`
before the source numeric predicate and `26,763 / 26,763 = 1.000` after it.
The exact system-plus-code discriminator is warranted by the served data and
the ETL; profile metadata is not used.

| Itemid | FHIR rows/resources in system+code | Oracle raw rows | Oracle rows after source predicate |
|---:|---:|---:|---:|
| 50862 | 625 | 625 | 625 |
| 50930 | 163 | 163 | 163 |
| 50976 | 181 | 181 | 181 |
| 50868 | 2,860 | 2,860 | 2,860 |
| 50882 | 2,863 | 2,863 | 2,863 |
| 51006 | 2,974 | 2,974 | 2,973 |
| 50893 | 2,377 | 2,377 | 2,377 |
| 50902 | 2,981 | 2,981 | 2,981 |
| 50912 | 3,003 | 3,003 | 3,003 |
| 50931 | 2,711 | 2,711 | 2,711 |
| 50983 | 3,007 | 3,007 | 3,007 |
| 50971 | 3,022 | 3,022 | 3,019 |
| **total** | **26,767** | **26,767** | **26,763** |

The four excluded demo rows are the three `50971` rows with source
`valuenum=NULL`, `value=NULL`, `comments='___'`, and one `51006` row with
`valuenum=NULL`, `value=NULL`, `comments='<3*.'`.  They materialize as
`value.ofType(string)` and not Quantity.  Among the 26,763 source-qualified
rows, `code`, `system`, `display`, `patient_key`, and `specimen_key` are each
non-null 26,763/26,763; `quantity_value`, `quantity_unit`, and
`effective_datetime` are each non-null 26,763/26,763; `quantity_comparator`,
`value_string`, and `value.ofType(CodeableConcept)` are 0/26,763.  Before the
numeric filter the target counts are: code/system/display 26,767/26,767,
quantity value/unit 26,763/26,767, comparator 0/26,767, value string
4/26,767, effective dateTime 26,767/26,767, period start/end 0/26,767,
patient key 26,767/26,767, specimen key 26,767/26,767, and encounter key
21,525/26,767.

The corresponding source-qualified input ledger is
`subject_id 26,763/26,763`, `hadm_id 21,521/26,763`, `charttime
26,763/26,763`, `specimen_id 26,763/26,763`, `itemid 26,763/26,763`, and
`valuenum 26,763/26,763` (total/non-null).  At the grouped output level the
3,289 rows have `subject_id 3,289/3,289`, `hadm_id 2,501/3,289`,
`charttime 3,289/3,289`, and `specimen_id 3,289/3,289`.

The FHIR ETL does more than copy `valuenum`: it uses `lab.valuenum` when
present, but can parse `<`, `<=`, `>`, and `>=` text into Quantity.value plus
Quantity.comparator when `valuenum` is NULL, then falls back to value text or
comments in `valueString`.  The source `valuenum IS NOT NULL` bit is not
preserved as a FHIR flag.  Thus the demo chemistry rows are exactly
filterable with the Quantity branch, but in a full dataset a comparator-text
row that was parsed into Quantity cannot be proven to have originated from a
non-null relational `valuenum`.  This is a source-origin gap, not a reason to
use `valueString` as a number.  The mapping must project both Quantity and
string variants and must retain `quantity_comparator` for this check.

## Specimen grouping and effective time

The Delta contains 11,122 lab `Specimen` resources, each with a non-null lab
identifier and a distinct numeric identifier value.  The lab specimen probe
found `type.coding.code` and `type.coding.system` populated 11,122/11,122,
`type.coding.display` populated 0/11,122, and
`collection.collected.ofType(dateTime)` populated 11,122/11,122.  All 26,767
target chemistry observations had a non-null specimen reference and joined
to a lab Specimen with the same subject, giving 3,289 distinct specimen
groups.  The source filtered query also produced 3,289 groups.  Group by the
Specimen identifier after the reference join; do not group by patient and
time.

The source demo comparison used `(specimen_id,itemid)` for the 26,763
eligible observations (unique 26,763/26,763 in this cohort) and then compared
the specimen-level pivot.  Exact agreement was:

```text
subject_id: 26,763/26,763; hadm_id: 26,763/26,763;
valuenum: 26,763/26,763; unit: 26,763/26,763;
charttime: 26,753/26,763;
specimen-level output key: 3,289/3,289;
specimen-level subject_id and hadm_id: 3,289/3,289;
specimen-level analyte values (all twelve): 3,289/3,289.
```

The ten datetime disagreements are all the ten analytes in specimen
`48555540`: source `2116-03-08 02:52:00`, FHIR `2116-03-08 03:52:00`.
This is the already-curated DST-gap transformation from
`mimic-fhir/sql/fhir_observation_labevents.sql:15` and
`MIMIC_NOTES.md`, not a timezone conversion to reapply.  Use
`CAST(effective_datetime AS TIMESTAMP_NTZ)`; do not use an offset-aware cast
that converts the de-identified wall-clock value.

## Encounter and `hadm_id` limitation

The served Encounter identifier systems were 275 hospital, 140 ICU, and 222
ED resources.  The chemistry mapping must select only
`.../identifier/encounter-hosp`, whose identifier value is `hadm_id` as a
string.  On the 26,763 source-qualified chemistry observations, the FHIR
encounter reference was present and resolved to a hospital identifier on
21,521/26,763; it was absent on 5,242/26,763.  The source has exactly
21,521 non-null `hadm_id` values and 5,242 null values in those same demo
rows.  At the 3,289 specimen-output rows, the source has non-null `hadm_id`
on 2,501 and NULL on 788, and the FHIR grouped result has the same counts.

This is why the implementer must LEFT JOIN Encounter and preserve a nullable
`hadm_id`; an INNER JOIN changes missing FHIR references into missing output
rows.  A patient-plus-effective-time admission-window heuristic was measured
against the demo oracle: it found one unique hospital match for 21,258/26,763
rows and agreed with the oracle on 21,143/21,258 (99.459%); 115 of those
unique matches were false positives where oracle `hadm_id` was NULL, 5,505
rows had no match, and none were ambiguous.  It is therefore an
approximation, not an exact recovery, and must not be used to manufacture
`hadm_id` values.  When the Observation encounter reference is absent,
`hadm_id` is a representational gap; emit a typed NULL rather than the
heuristic.

## Final output shape and casts

The oracle manifest target for `chemistry` is keyed by `specimen_id`, with
3,811,523 full-data rows and this exact column order/type shape:

```text
subject_id   INTEGER
hadm_id      INTEGER (nullable)
charttime    TIMESTAMP (nullable in the relational type, though demo groups are all non-null)
specimen_id  INTEGER
albumin      DOUBLE
globulin     DOUBLE
total_protein DOUBLE
aniongap     DOUBLE
bicarbonate DOUBLE
bun          DOUBLE
calcium      DOUBLE
chloride     DOUBLE
creatinine   DOUBLE
glucose      DOUBLE
sodium       DOUBLE
potassium    DOUBLE
```

The FHIR aliases that feed this shape remain strings until the final SQL:
cast `subject_id_str`, `hadm_id_str`, and `specimen_id_str` to INTEGER; cast
`quantity_value` to DOUBLE; and cast `effective_datetime` to
`TIMESTAMP_NTZ`.  Preserve all twelve analyte columns, including all-NULL
columns in a particular cohort; they are part of the required output shape.

## Evidence provenance

Probes used the source analysis, `AGENTS.md`, `LOOP_CONTRACT.md`, curated
`MIMIC_NOTES.md`, all existing fragments (`MIMIC_NOTES.d/README.md`,
`cardiac_marker.md`, and `blood_differential.md`), the canonical observation
ViewDefinition format, the demo Delta warehouse with embedded Pathling/Spark,
the demo DuckDB oracle, and upstream ETL SQL
`mimic-fhir/sql/fhir_observation_labevents.sql`,
`fhir_specimen_lab.sql`, and `fhir_encounter.sql`.  The other fragments were
treated as provisional leads; their system-before-integer-cast and
text/comparator warnings were independently verified in the probes above.

The only new dataset/IG-wide finding appended by this probe is the lab
Specimen display omission in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/chemistry.md`.  No concept-specific
finding was put in another fragment, and `MIMIC_NOTES.md` was not edited.
