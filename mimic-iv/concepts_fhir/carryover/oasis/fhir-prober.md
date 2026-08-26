# FHIR-prober mapping: `oasis`, attempt `0002`

This is the reusable source-column to MIMIC-on-FHIR mapping for the OASIS
implementer.  It is a mapping/evidence artifact, not a ViewDefinition,
`concept.sql`, or terminal equivalence decision.  It supersedes the attempt
0001 mapping where that mapping used `Encounter.class = 'AMB'` as a proxy for
elective admission.

## Provenance and probe policy

- Source analysis reused verbatim:
  `mimic-iv/concepts_fhir/carryover/oasis/source-analyst.md`.
- Canonical source SQL: `mimic-iv/concepts/score/oasis.sql` (287 lines).
- Oracle manifest: `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.
  The source grain is `stay_id`; the full manifest has 73,181 rows and requires
  `patient_key`, `encounter_key`, and `icu_encounter_key` as companion resource
  keys.
- Structural reference: `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
  The mapping below uses its `select[].column[].{path,name}` and
  `forEach`/`forEachOrNull` conventions.
- Authoritative FHIR data: `/Users/nau025/warehouses/mimic-iv-demo/delta`,
  queried with embedded Pathling 9.6.0 on Spark 4.0.2.  The Pathling session
  was pinned to UTC by `EmbeddedExecutor`.
- Read-only relational oracle: `/Users/nau025/warehouses/mimic4-demo.db`,
  DuckDB 1.5.5.
- No HTTP Pathling server and no raw `Mimic*.ndjson.gz` were used.
- Resource and reference keys were used only for equality joins, distinct
  resource counts, and provenance.  No id was parsed, regenerated, hashed,
  hardcoded, or used to infer a source value.

The probe counts below are row totals versus non-null totals where relevant;
coding counts also report distinct resources and the coding/resource ratio.

## Mapping decision that supersedes attempt 0001

The exact served elective discriminator is:

```json
{ "path": "code", "name": "priority_code" }
```

inside:

```text
forEach: priority.coding
```

with `priority_system =
http://terminology.hl7.org/CodeSystem/v3-ActPriority` and
`priority_code = 'EL'`.  The local Delta probe found 13/275 hospital
Encounters with this coding, and the DuckDB `admissions.admission_type =
'ELECTIVE'` count is 13/275; the joined cross-tab agreed on all 275/275
admissions.  `Encounter.class.code = 'AMB'` is not an elective discriminator:
it groups ELECTIVE with URGENT and ambulatory observation admissions.  Do not
use class for this branch.

This is the upstream mapping named in the previous diagnosis:
`mimic-fhir/sql/fhir_etl/map_encounter_priority.sql:12-20`, written by
`mimic-fhir/sql/fhir_encounter.sql:93-96,135-141`.  The service history remains
partial: `fhir_encounter.sql:45-57,71,142-147` retains only the first service
ordered by `transfertime`, drops `transfertime`, and writes one
`serviceType.coding`.

## Source table to FHIR resource/interface

| MIMIC source | FHIR resource or interface | Stream discriminator / role |
|---|---|---|
| `mimiciv_hosp.patients` | `Patient` | Patient identifier system |
| `mimiciv_hosp.admissions` | hospital `Encounter` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` |
| `mimiciv_icu.icustays` | ICU `Encounter` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` |
| `mimiciv_hosp.services` | hospital `Encounter.serviceType` | only the retained first service; not the source history |
| `mimiciv_icu.chartevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus exact item code |
| `mimiciv_icu.outputevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items` plus exact item code |
| `mimiciv_derived.age` | completed dependency stem `age` | consume the published `age` interface by `encounter_key`; do not rederive in OASIS |
| `mimiciv_derived.first_day_gcs` | completed dependency stem `first_day_gcs` | consume `gcs_min` by `icu_encounter_key` |
| `mimiciv_derived.first_day_urine_output` | completed dependency stem `first_day_urine_output` | consume `urineoutput` by `icu_encounter_key` |
| `mimiciv_derived.first_day_vitalsign` | completed dependency stem `first_day_vitalsign` | consume min/max fields by `icu_encounter_key` |
| `mimiciv_derived.ventilation` | completed dependency stem `ventilation` | consume intervals/status by `icu_encounter_key` |

The five derived stems are not additional raw FHIR resources for this concept.
The candidate must use their published shapes; it must not query raw
`mimiciv_derived` tables or inline their transformations.

## Patient and Encounter identifier/key spine

### Patient

| Source column/role | Canonical mapping `{path,name}` | FHIR type and materialized type | Probe |
|---|---|---|---|
| `patients.subject_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Identifier.value` `string` / `STRING` | 100/100 non-null, 100 distinct; exact source patient-id set 100/100; final SQL casts to manifest `INTEGER` |
| Patient join/output key | `{ "path": "getResourceKey()", "name": "patient_key" }` | opaque resource-key `string` / `STRING` | 100/100 non-null and distinct; type-prefixed form on 100/100; equality only |
| `patients.anchor_age`, `patients.anchor_year` | no individual exact FHIR path | absent source fields; `Patient.birthDate` is FHIR `date` / materialized `STRING` | OASIS consumes the completed `age` dependency, not these anchor fields. The current rebuilt `birthDate` + hospital `Encounter.period.start` age interface is exact; do not infer anchors from an id. |
| Age provenance | `{ "path": "birthDate", "name": "birth_date" }` | FHIR `date` / `STRING` | `birthDate` 100/100; current `age` full run evidence says the consumed age is exact, while individual anchor members remain unavailable |

### Hospital and ICU Encounter

The following flat columns can be emitted together from an Encounter view.  A
hospital and an ICU view should filter by the identifier-system predicates,
not by `class`.

| Source column/role | Canonical mapping `{path,name}` | FHIR type and materialized type | Probe |
|---|---|---|---|
| Encounter identity | `{ "path": "getResourceKey()", "name": "encounter_key" }` | opaque resource-key `string` / `STRING` | 637/637 non-null and distinct; retain the `Encounter/` prefix |
| Encounter subject join | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | Reference key `string` / `STRING` | 637/637 non-null; hospital subject-to-Patient identifier join 275/275 and ICU join 140/140 |
| `admissions.hadm_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Identifier.value` `string` / `STRING` | hospital stream 275/275; source id set exact 275/275; final SQL casts to `INTEGER` |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` `string` / `STRING` | ICU stream 140/140; source id set exact 140/140; final SQL casts to `INTEGER` and uses it as natural key |
| `icustays.hadm_id` | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }`, then join to hospital `{ "path": "getResourceKey()", "name": "encounter_key" }` and take `hadm_id_str` | Reference/resource keys plus identifier `string` | ICU `partOf` 140/140; parent hospital-key join 140/140; recovered `hadm_id` exact 140/140 |
| `icustays.subject_id` / `admissions.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, then join to Patient `patient_key` and take `subject_id_str` | Reference key plus identifier `string` | ICU subject identifier exact 140/140 and hospital subject identifier exact 275/275 |
| `admissions.admittime` | `{ "path": "period.start", "name": "period_start" }` | FHIR `dateTime`; offset-bearing `STRING` | exact wall-clock agreement 275/275; cast directly to `TIMESTAMP_NTZ` |
| `admissions.dischtime` | `{ "path": "period.end", "name": "period_end" }` | FHIR `dateTime`; offset-bearing `STRING` | exact wall-clock agreement 275/275; cast directly to `TIMESTAMP_NTZ` |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`; offset-bearing `STRING` | exact wall-clock agreement 140/140; cast directly to `TIMESTAMP_NTZ` |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime_datetime" }` | FHIR `dateTime`; offset-bearing `STRING` | exact wall-clock agreement 140/140; cast directly to `TIMESTAMP_NTZ` |
| ICU parent identity | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }` | opaque reference key `string` / `STRING` | join by equality only; never parse or regenerate the key |

The authoritative Delta contains 637 Encounters: 275 hospital, 140 ICU, and
222 ED.  Identifier-system probing returned one identifier per resource for
each system: patient 100/100 (ratio 1.000), hospital 275/275 (1.000), ICU
140/140 (1.000), and ED 222/222 (1.000).  The all-Encounter class cross-tab
was `ACUTE=140`, `AMB=56`, `EMER=341`, `OBSENC=82`, `SS=18`; therefore class
cannot be used to select the hospital or ICU stream.

Required output resource keys are `patient_key` beside `subject_id`,
`encounter_key` beside `hadm_id`, and `icu_encounter_key` beside `stay_id`.
They are uncast opaque strings with their type prefix intact.  The integer
identifiers are not keys.

## Admission type, priority, services, and discharge fields

### Exact admission discriminator

| Source column | Canonical mapping `{path,name}` | FHIR type/materialized type | Probe and rule |
|---|---|---|---|
| `admissions.admission_type = 'ELECTIVE'` | in a separate coding group: `{ "path": "code", "name": "priority_code" }` with `forEach: "priority.coding"`; `{ "path": "system", "name": "priority_system" }`; `{ "path": "display", "name": "priority_display" }` | `Coding.code` `code` / `STRING`; `Coding.system` `uri` / `STRING`; `display` `string` / `STRING` | system is `http://terminology.hl7.org/CodeSystem/v3-ActPriority`; `EL/elective=13`, `EM/emergency=119`, `R/routine=105`, `UR/urgent=38`; one priority coding per hospital resource, 275 rows / 275 resources, ratio 1.000. Filter on exact system + `EL`. |
| `Encounter.class` (old proxy only) | `{ "path": "class.code", "name": "class_code" }` | `Coding.code` `code` / `STRING` | not an admission-type mapping; hospital `AMB` includes all 13 ELECTIVE, all 38 URGENT, and 5 ambulatory-observation admissions. The attempt 0001 `AMB` decision is superseded. |

The source `admission_type` cross-tab against served priority was exact for all
275/275 hospital admissions, including the 13 `ELECTIVE -> EL` rows.  This is
the discriminator that must feed `electivesurgery`; no terminology lookup is
needed.

### Service mapping and irrecoverable history

Use a separate repeating group (with the resource key in the flat group):

```json
{
  "forEach": "serviceType.coding",
  "column": [
    { "path": "code", "name": "service_code" },
    { "path": "system", "name": "service_system" },
    { "path": "display", "name": "service_display" }
  ]
}
```

| Source column | Canonical mapping `{path,name}` | FHIR type/materialized type | Probe |
|---|---|---|---|
| `services.hadm_id` | hospital Encounter identifier mapping above; join the retained service row to `encounter_key` | source `INTEGER`; FHIR identifier `string` / `STRING` | service rows cover all 275 hospital hadm ids; equality join to hospital Encounter is exact |
| `services.curr_service` | `{ "path": "code", "name": "service_code" }` within `serviceType.coding` | `Coding.code` `code` / `STRING` | system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services`; 275 rows / 275 resources, ratio 1.000; `display` is NULL on all 275/275 |
| service coding system | `{ "path": "system", "name": "service_system" }` within `serviceType.coding` | `Coding.system` `uri` / `STRING` | one exact system on 275/275 hospital codings |
| service display | `{ "path": "display", "name": "service_display" }` within `serviceType.coding` | `string` / `STRING` | 0/275 non-null; never use display for filtering |
| `services.transfertime` | no FHIR path | source `TIMESTAMP`; absent | no service time is serialized. `Encounter.period.start` is admission time, not service-transfer time. |

The retained hospital service code equals the earliest source service ordered
by `transfertime` for 275/275 admissions.  The source has 319 service rows over
275 distinct admissions, whereas FHIR has one coding per hospital Encounter.
The FHIR hospital code counts are:

```text
CMED=39, CSURG=13, GYN=2, MED=112, NMED=7, NSURG=15, OMED=24,
ORTHO=4, PSYCH=3, SURG=36, TRAUM=8, TSURG=3, VSURG=9.
```

The source literals are retained exactly: `LOWER(curr_service) LIKE '%surg%'`
matched 89 source service rows and `curr_service = 'ORTHO'` matched 5.  In the
140-stay demo, applying the full source cutoff
`transfertime < intime + 1 day` gives 57/140 surgical stays.  Applying the
same surgical predicate to the one served service gives 45/140; 45 agree,
12 source-positive stays are missed, and there are 0 FHIR-only positives.
Those 12 are later/history surgical services whose first retained service is
non-surgical.  In this demo all 12 are non-elective, so the priority-plus-one-
service branch happens to agree on `electivesurgery` for 140/140 stays (5
source positives and 5 served positives).  This does not make the history
representable: the previous full-data diagnosis decomposed the old attempt
into 3,295 class-heuristic false positives and 54 remaining elective-surgery
false negatives after using the exact priority discriminator.  The latter are
the full-data instances where a later pre-cutoff surgical service changes the
OASIS result.

### Other admission fields

| Source column | Canonical mapping `{path,name}` | FHIR type/materialized type | Probe/gap |
|---|---|---|---|
| `admissions.discharge_location` | in a coding group over `hospitalization.dischargeDisposition.coding`: `{ "path": "code", "name": "discharge_code" }`, `{ "path": "system", "name": "discharge_system" }` | `Coding.code` `code` / `STRING`; `Coding.system` `uri` / `STRING` | source/FHIR value agreement 275/275 including 42 NULLs; non-null served system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-discharge-disposition` on 233/275. Source literal `DEAD/EXPIRED` occurs 0 times in this oracle. |
| `admissions.deathtime` | no exact FHIR path | source `TIMESTAMP`; absent | Patient `deceasedDateTime` is patient-level/date-like and is not an admission-time substitute. It is only used by an unselected intermediate mortality flag. |
| `admissions.hospital_expire_flag` | no exact FHIR path | source `SMALLINT`; absent | only an unselected intermediate field; it does not enter the final OASIS projection or score |

The absence of `deathtime` and `hospital_expire_flag` is therefore ancillary
for this concept.  Do not manufacture them from Patient death data.

## Observation mapping and exact code sets

All item filters use `code.coding.system` plus the exact source item code.  Do
not discriminate with `meta.profile`.  For each Observation stream, the
resource key, references, effective variants, value variants, and `issued`
are flat columns, and the code fields are a constrained coding group:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(string)", "name": "value_string" },
    { "path": "issued", "name": "issued" }
  ]
}
```

For chartevents use:

```text
forEach: code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and <exact source-code disjunction>)
```

and for outputevents use the corresponding `mimic-d-items` system.  In either
group the canonical code mappings are:

```json
{ "path": "code", "name": "item_code" }
{ "path": "system", "name": "item_system" }
{ "path": "display", "name": "item_display" }
```

Their FHIR types are `Coding.code` `code`, `Coding.system` `uri`, and
`Coding.display` `string`; all three materialize as `STRING`.  The current
Delta probe found exactly one coding per targeted resource: chartevents
123,829 rows / 123,829 resources (ratio 1.000), and outputevents 7,349 /
7,349 (ratio 1.000).  For chartevents, `item_code`, `item_system`, and
`item_display` were each non-null on 123,829/123,829; for outputevents each
was non-null on 7,349/7,349.  The source row counts matched those FHIR counts
for every listed code.

### Chartevents exact code counts

System for every row below:
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
The union is 40 exact codes; `224690` is shared by the vitalsign and
ventilator-setting dependency code sets and is counted once in the union.
Each number is `source rows = FHIR coding rows = distinct FHIR resources`.

```text
GCS:
  223900=3266, 223901=3251, 220739=3274

vitalsign:
  220045=13913, 225309=486, 225310=486, 225312=488,
  220050=5525, 220051=5524, 220052=5560,
  220179=8347, 220180=8349, 220181=8342,
  220210=13913, 224690=1331, 220277=13540,
  225664=1637, 220621=931, 226537=209,
  223762=391, 223761=3379, 224642=3794

oxygen_delivery:
  223834=1090, 227582=13, 227287=145, 226732=3145

ventilator_setting:
  224688=801, 224689=1314, 224690=1331,
  224687=1359, 224685=1331, 224684=769, 224686=661,
  224696=510, 220339=1447, 224700=490, 223835=1746,
  223849=1048, 229314=402, 223848=1292, 224691=330

chartevents union total: 123829
```

The DuckDB source probe found 123,829/123,829 selected chartevent rows with a
non-NULL `value` and `stay_id`, and 0 rows at the known hard-coded excluded
tuple.  The constrained FHIR projection had `effective.ofType(dateTime)` on
123,829/123,829; `Period.start`, `Period.end`, and `instant` were each
0/123,829.  `quantity_value` was populated on 116,467/123,829, its unit on
100,944/123,829, top-level `value_string` on 7,362/123,829, and `issued` on
123,829/123,829.  The Quantity alias is string-like in a materialized
ViewDefinition even though FHIR `Quantity.value` is decimal; cast it before
numeric SQL.  The raw decimal is encoded at Pathling `DECIMAL(32,6)`.

The oxygen-device item `226732` is not one row per patient/charttime: the
DuckDB source has 3,145 rows in 3,014 `(subject_id, charttime)` groups, 106
groups with multiplicity greater than one, and maximum multiplicity 3.  Keep
the resource rows until the dependency's source-equivalent ranking is applied;
do not pre-deduplicate on patient and time.

### Rebuilt numeric chartevent text

For dependency mappings that need source labels (GCS and ventilation), add a
nullable component group:

```json
{
  "forEachOrNull": "component",
  "column": [
    { "path": "code.coding.code", "name": "component_code" },
    { "path": "code.coding.system", "name": "component_system" },
    { "path": "value.ofType(string)", "name": "component_text" }
  ]
}
```

The attempt 0002 Delta probe found component text/code/system on:

```text
220739: 3274/3274; 223900: 3266/3266; 223901: 3251/3251;
223848: 906/1292; 223849: 1011/1048; 229314: 402/402.
```

The three GCS item streams therefore retain their numeric-row labels in the
component, including `223900` `No Response-ETT` (1,348) and `No Response` (78).
For ventilator settings, the nonnumeric source rows remain in top-level
`value.ofType(string)`: `223848` has 386 such rows and `223849` has 37; their
numeric, label-bearing rows are the component counts above.  The source
numeric/text partition and the served component counts agree for these target
items.  Never use an Observation id to recover a discarded label.

### Outputevents exact code counts

System for every row below:
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`.

```text
226559=6685, 226560=496, 226561=90, 226584=0,
226563=0, 226564=0, 226565=0, 226567=15,
226557=0, 226558=0, 227488=32, 227489=31.

outputevents total: 7349
```

The nonzero counts are source rows = FHIR coding rows = distinct resources;
the six zero codes were absent in both source and FHIR.  The FHIR projection
had `effective.ofType(dateTime)` on 7,349/7,349, `Period.start`, `Period.end`,
and `instant` each on 0/7,349, Quantity value and unit on 7,349/7,349, and
top-level string value on 0/7,349.  `issued` was non-null on 7,349/7,349.

`outputevents` and `datetimeevents` share the `mimic-d-items` system.  The
exact system-plus-code discriminator still separates this OASIS stream because
`mimiciv_icu.d_items.itemid` is a global primary key with one `linksto` value:
the DuckDB probe found every one of the twelve output codes linked to
`outputevents` and no selected output code linked to `datetimeevents`.  This
rule would break if a future preparation reused an itemid across streams; do
not substitute `meta.profile`.

The canonical output value mapping is:

```json
{ "path": "(value).ofType(Quantity).value", "name": "value_quantity" }
{ "path": "(value).ofType(Quantity).unit", "name": "value_unit" }
{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }
```

The first two are FHIR decimal/string and unit string in the materialized
view; the dependency casts the numeric value and applies the source
`227488`-positive sign reversal.

## Dependency boundary to consume

These are published interfaces, not columns to reconstruct from raw FHIR in
OASIS.  All dependency joins use opaque keys:

| Published stem | Published columns used by OASIS | FHIR provenance / type |
|---|---|---|
| `age` | `encounter_key`, `patient_key`, `age` | hospital Encounter key from `getResourceKey()` / subject Patient key; `age` is published `BIGINT` derived from Patient `birthDate` and hospital `period.start` |
| `first_day_gcs` | `icu_encounter_key`, `patient_key`, `gcs_min` | chartevent Quantity value plus component text for GCS; `gcs_min` published nullable `FLOAT` |
| `first_day_urine_output` | `icu_encounter_key`, `patient_key`, `urineoutput` | output Observation Quantity value and dateTime; `urineoutput` published nullable `DOUBLE` |
| `first_day_vitalsign` | `icu_encounter_key`, `patient_key`, HR/MBP/respiratory/temperature min/max | chartevent Quantity value, exact vitalsign codes, dateTime; published numeric min/max fields |
| `ventilation` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `ventilation_status` | chartevent dateTime and top-level/component labels; published timestamps plus `VARCHAR` status |

The dependency outputs have already stripped their integer identifiers in the
published shape.  Join `age` on `encounter_key` and all ICU dependencies on
`icu_encounter_key`, never on a dropped `hadm_id` or `stay_id`.

The OASIS literal `v.ventilation_status = 'InvasiveVent'` is a filter on the
completed dependency, not a FHIR coding filter.  The DuckDB demo dependency
contains 61 `InvasiveVent` intervals over 58 stays (the other status counts are
`HFNC=5`, `NonInvasiveVent=4`, and `SupplementalOxygen=139`).  The dependency
must expose and filter its exact `ventilation_status` string; its underlying
FHIR provenance is the chartevent `value.ofType(string)` and rebuilt
`component.valueString` mappings above.

## Final manifest output types

The final OASIS output is one row per ICU stay.  Required types are:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
oasis INTEGER, oasis_prob DOUBLE,
age BIGINT, age_score INTEGER,
preiculos BIGINT, preiculos_score INTEGER,
gcs FLOAT, gcs_score INTEGER,
heartrate DOUBLE, heart_rate_score INTEGER,
meanbp DOUBLE, mbp_score INTEGER,
resprate DOUBLE, resp_rate_score INTEGER,
temp DOUBLE, temp_score INTEGER,
urineoutput DOUBLE, urineoutput_score INTEGER,
mechvent INTEGER, mechvent_score INTEGER,
electivesurgery INTEGER, electivesurgery_score INTEGER.
```

The required companion columns are `patient_key`, `encounter_key`, and
`icu_encounter_key`, each uncast `STRING` with the `Patient/` or `Encounter/`
prefix.  FHIR identifier aliases remain `_str` until the outer SQL casts them
to the manifest integer types.  FHIR datetime aliases remain strings until
they are directly cast to `TIMESTAMP_NTZ`; do not use an offset-aware
`TIMESTAMP` conversion.

## Gaps and essentiality

1. **Service history and `transfertime`: absent and not representable.**
   `serviceType` provides the first service code exactly (275/275), but not
   later services or their times.  The source OASIS predicate uses every
   service row with `transfertime < intime + 1 day`; no FHIR element identifies
   whether a later surgical code was before that cutoff.  The measured demo
   loss is 12/140 source-positive surgical-history stays.  The previous full
   comparison/diagnosis measured 54 full-data ELECTIVE false negatives after
   replacing the bad AMB heuristic with priority `EL`.  On those rows the loss
   changes `electivesurgery`, `electivesurgery_score`, `oasis`, and
   `oasis_prob`; it is therefore potentially essential and reaches rows that
   the port cannot identify exactly.  Recommend whole-concept blocking to the
   equivalence judge, without making a terminal decision here.

2. **`admission_type` is representable for the only OASIS literal that
   matters.**  `ELECTIVE` is served as exact priority system + code `EL`,
   with 13/13 source/FHIR hospital rows and a 275/275 joined cross-tab.  This
   replaces the old `class=AMB` approximation; it is not a gap.

3. **Admission mortality intermediates are absent but non-essential.**
   `deathtime` and `hospital_expire_flag` have no exact FHIR path.  They feed
   only unselected intermediate mortality flags and no final OASIS value or
   score.  `discharge_location` itself is represented by
   `hospitalization.dischargeDisposition.coding.code` and agreed 275/275;
   the source `DEAD/EXPIRED` literal has zero rows here.

4. **Individual age anchors are absent, but the consumed age value is
   derivable/currently exact.**  `anchor_age`, `anchor_year`, and
   `anchor_year_group` are not individual FHIR fields.  The current rebuilt
   `Patient.birthDate` plus hospital Encounter period makes the completed
   `age` dependency exact, so OASIS must consume that dependency result rather
   than infer the anchor pair or use an opaque key.  This is not a missing
   OASIS input in the current warehouse.

## Notes/fragments read and verification summary

Established `MIMIC_NOTES.md` entries that changed this mapping were:

- Delta tables, not stale NDJSON or the unauthorized HTTP server, are the
  source of truth.
- Patient/Encounter identifiers are strings; resource/reference keys are
  type-prefixed opaque equality identities and required companion outputs.
- Encounter stream selection is by identifier system, not `class`.
- Itemid-derived Observation codes are verbatim and must use exact
  system + code; outputevents and datetimeevents share `mimic-d-items`.
- Choice fields require separate `ofType()` columns; Quantity aliases need
  numeric casts; datetime strings require `TIMESTAMP_NTZ`.
- Rebuilt numeric chartevents can carry source labels in
  `component.valueString`; no id recovery is permitted.
- The current UTC/birthDate upstream repairs mean the historical DST and
  birthDate-conflict behavior must not be reintroduced.

The following provisional fragments were read: `MIMIC_NOTES.d/README.md`,
`age.md`, `first_day_gcs.md`, `first_day_urine_output.md`,
`first_day_vitalsign.md`, `ventilation.md`, `gcs.md`, `urine_output.md`,
`vitalsign.md`, `oxygen_delivery.md`, and `ventilator_setting.md`.  Their
priority/service-history leads and all raw FHIR fields used here were checked
against the current Delta/oracle probes, not blindly adopted.  The completed
dependency outputs were not re-derived in this stage because the implementer
must consume their published stems.  In particular, the old provisional claim
that only item `223900` had a component was not adopted: the attempt 0002 probe
found component text for all three GCS items and the three ventilation label
items as documented above.

The existing priority/service-history entries in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/oasis.md` were **not rewritten or
duplicated**.  One genuinely new dataset-wide finding was appended there:
the rebuilt numeric chartevent component coverage includes GCS items `220739`
and `223901` as well as `223900`, with the measured per-item counts above.

No ViewDefinition, `concept.sql`, demo/full run, state transition, or commit
was performed by this stage.

## Carryover artifact

`mimic-iv/concepts_fhir/carryover/oasis/fhir-prober.md`
