# FHIR prober mapping: `sapsii`

**Attempt:** `0001`  
**Probed:** 2026-08-26  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/sapsii/source-analyst.md`  
**Canonical SQL:** `mimic-iv/concepts/score/sapsii.sql`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Probe engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Read-only oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB 1.5.5)

No HTTP Pathling server, raw NDJSON, ViewDefinition artifact, or `concept.sql`
was used or authored by this stage.

## Source contract and target shape

The source SQL has one row per ICU stay. Its natural key is `stay_id`; the full
oracle manifest declares 73,181 rows, a keyed comparison on `stay_id`, and
three required FHIR identity companions: `encounter_key`,
`icu_encounter_key`, and `patient_key`. The companions are not source SQL
columns, but are required in the candidate for downstream FHIR joins.

The manifest output types are:

```text
subject_id          INTEGER
hadm_id             INTEGER
stay_id             INTEGER
starttime           TIMESTAMP
endtime             TIMESTAMP
sapsii              INTEGER
sapsii_prob         DOUBLE
age_score           INTEGER
hr_score            INTEGER
sysbp_score         INTEGER
temp_score          INTEGER
pao2fio2_score      INTEGER
uo_score            INTEGER
bun_score           INTEGER
wbc_score           INTEGER
potassium_score     INTEGER
sodium_score        INTEGER
bicarbonate_score  INTEGER
bilirubin_score     INTEGER
gcs_score           INTEGER
comorbidity_score   INTEGER
admissiontype_score INTEGER
```

The first-day interval is `(icustays.intime, icustays.intime + 24 hours]`.
The source uses the ICU `intime` for both `starttime` and all time-window
membership. `outtime` is selected only in an intermediate CTE and is not in
the final output.

## Source table to FHIR resource mapping

| Source table/role | FHIR resource or published relation | Mapping/discriminator |
|---|---|---|
| `mimiciv_icu.icustays` (`subject_id`, `hadm_id`, `stay_id`, `intime`) | ICU `Encounter` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; `partOf` points to the hospital Encounter |
| `mimiciv_hosp.admissions` (`subject_id`, `hadm_id`, `admission_type`) | hospital `Encounter` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`; `priority.coding` preserves the elective/non-elective distinction |
| `mimiciv_hosp.services` (`hadm_id`, `curr_service`, `transfertime`) | hospital `Encounter.serviceType` | `serviceType.coding` contains the first service selected upstream by `transfertime` |
| `mimiciv_hosp.diagnoses_icd` (`hadm_id`, `icd_code`, `icd_version`) | `Condition` | join `Condition.encounter` to the hospital Encounter; use `Condition.code.coding.system + code` and the exact source prefixes |
| `mimiciv_icu.chartevents` (`stay_id`, `charttime`, `itemid`, `value`) | chartevents `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus code `226732` |
| `mimiciv_hosp.patients` | `Patient` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/patient` |
| `mimiciv_derived.age` | published derived relation `age` | consume the completed dependency; join its published `encounter_key`, not a stripped `hadm_id` |
| `mimiciv_derived.bg` | published derived relation `bg` | consume the completed dependency; join its published `patient_key` and `charttime` |
| `mimiciv_derived.chemistry` | published derived relation `chemistry` | consume the completed dependency; join its published `patient_key` and `charttime` |
| `mimiciv_derived.complete_blood_count` | published derived relation `complete_blood_count` | consume the completed dependency; join its published `patient_key` and `charttime` |
| `mimiciv_derived.enzyme` | published derived relation `enzyme` | consume the completed dependency; join its published `patient_key` and `charttime` |
| `mimiciv_derived.gcs` | published derived relation `gcs` | consume the completed dependency; join its published `icu_encounter_key` and `charttime` |
| `mimiciv_derived.urine_output` | published derived relation `urine_output` | consume the completed dependency; join its published `icu_encounter_key` and `charttime` |
| `mimiciv_derived.ventilation` | published derived relation `ventilation` | consume the completed dependency; join its published `icu_encounter_key` and interval |
| `mimiciv_derived.vitalsign` | published derived relation `vitalsign` | consume the completed dependency; join its published `patient_key` and `charttime` |

`Encounter.class` is not used to select a stream. The current Delta has 275
hospital, 140 ICU, and 222 ED Encounters; class values overlap between those
streams.

## Canonical FHIRPath projections

All `_str` identifier aliases and all resource/reference keys are FHIR strings
and materialize as Spark `STRING`/`VARCHAR`. Numeric identifier outputs must be
cast to `INTEGER` by the eventual derived SQL. Resource keys are opaque,
type-prefixed equality keys and must be emitted unchanged.

### Patient

```text
{ "path": "getResourceKey()", "name": "patient_key" }
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
```

`patient_key` is FHIR resource-key `string`; `subject_id_str` is
`Identifier.value` of FHIR type `string`. The probe found 100/100 Patient
resource keys and 100/100 patient identifiers.

### Hospital Encounter

```text
{ "path": "getResourceKey()", "name": "encounter_key" }
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
{ "path": "period.start", "name": "admittime_datetime" }
{ "path": "priority.coding.code", "name": "admission_priority_code" }
{ "path": "priority.coding.system", "name": "admission_priority_system" }
{ "path": "serviceType.coding.code", "name": "service_code" }
{ "path": "serviceType.coding.system", "name": "service_system" }
```

The hospital stream has 275/275 `hadm_id_str`, 275/275 patient references,
275/275 priority codes, and 275/275 service codes. The priority system is
`http://terminology.hl7.org/CodeSystem/v3-ActPriority`; `EL` is the served
elective discriminator. The service system is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services`.

The source SQL only needs `admission_type = 'ELECTIVE'` versus
`admission_type != 'ELECTIVE'`. In the served Delta, `priority.coding.code =
'EL'` reproduces that binary distinction. The demo has 13 elective/`EL` and
262 non-elective/non-`EL` hospital admissions.

### ICU Encounter

```text
{ "path": "getResourceKey()", "name": "icu_encounter_key" }
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }
{ "path": "period.start", "name": "intime_datetime" }
```

The ICU identifier projection has 140/140 `stay_id_str`; the ICU stream has
140/140 `partOf` hospital references, patient references, and period starts.
The ICU identifier and `period.start` match the DuckDB `icustays` spine
140/140. Use `hospital_encounter_key` to recover `hadm_id` through the hospital
Encounter identifier; do not join ICU and hospital rows by parsing resource
IDs or by guessing from timestamps.

### Chartevents Observation for CPAP

The coding discriminator is constrained inside the coding iteration:

```text
forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code='226732')"
{ "path": "code", "name": "item_code" }
{ "path": "system", "name": "item_system" }
{ "path": "display", "name": "item_display" }
```

Flat columns:

```text
{ "path": "getResourceKey()", "name": "observation_key" }
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }
{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }
{ "path": "(value).ofType(string)", "name": "value_string" }
{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }
```

For code `226732`, the probe found 3,145 rows/resources, with all 3,145
observation keys, patient keys, encounter keys, effective dateTimes, string
values, code, system, and display populated. Quantity value was 0/3,145.
The source CPAP predicate `LOWER(value) RLIKE 'cpap mask|bipap'` selects 32
rows: FHIR has 4 `CPAP mask` and 28 `Bipap mask` rows, and DuckDB has 32 rows.
The source/FHIR `(stay_id, charttime)` alignment is 32/32 exact after
discarding the FHIR string formatting whitespace.

### Condition for hospital diagnoses

```text
{ "path": "getResourceKey()", "name": "condition_key" }
{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }
```

Coding is projected as:

```text
forEach: "code.coding"
{ "path": "code", "name": "code" }
{ "path": "system", "name": "system" }
{ "path": "display", "name": "display" }
```

The current Delta `Condition` table contains both hospital and ED diagnosis
resources. Filter to hospital diagnoses by joining `encounter_key` to the
hospital Encounter view; do not use `meta.profile`. The probe found 5,051
Condition codings over 5,051 distinct resources (ratio 1.000), of which the
hospital-Encounter-linked subset is 4,506. The hospital subset has 2,193 ICD-9
and 2,313 ICD-10 codings, each one coding per resource. This exactly matches
the 4,506 DuckDB `diagnoses_icd` rows after trimming `icd_code`; the tuple
`(subject_id, hadm_id, icd_code, icd_version)` agrees 4,506/4,506.

The served systems actually observed are:

```text
icd_version 9  -> http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9
icd_version 10 -> http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10
```

The current Delta probe is authoritative for this mapping. It does not carry
the proper ICD URI values suggested by a historical curated-note entry.

## Dependency boundary and FHIR origins

The completed dependency attempts emit resource keys beside the relational
identifiers. The runner's published-shape preprocessing strips an identifier
when its paired key is present. Therefore the relations available to `sapsii`
do **not** expose the source analyst's integer `subject_id`, `hadm_id`, or
`stay_id` columns in the following cases. Join on the published keys:

| Dependency input used by sapsii | Published relation available to the consumer | FHIR origin of the value | Demo oracle total/non-null |
|---|---|---|---:|
| `age.hadm_id`, `age.age` | `age.encounter_key`, `age.age`, `age.patient_key` | hospital Encounter key from `{path: "getResourceKey()", name: "encounter_key"}`; age is derived from Encounter `period.start` and Patient `birthDate` | `age`: 275/275 |
| `bg.subject_id`, `bg.charttime`, `bg.specimen`, `bg.pao2fio2ratio` | `bg.patient_key`, `bg.encounter_key`, `bg.charttime`, `bg.specimen`, `bg.pao2fio2ratio` | Patient reference; lab Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}`; code `52033` string value; ratio derived from lab codes `50821`/`50816` and chart FiO2 `223835` | 889/889, 889/889, 872/872, 563/563 |
| `chemistry.subject_id`, `chemistry.charttime`, `bun`, `potassium`, `sodium`, `bicarbonate` | `chemistry.patient_key`, `chemistry.encounter_key`, `chemistry.specimen_key`, plus the listed fields | lab Observation Patient/reference/effective paths; Quantity value for codes `51006`, `50971`, `50983`, `50882` | total 3,289; charttime 3,289; bun 2,973; potassium 3,019; sodium 3,007; bicarbonate 2,863 |
| `complete_blood_count.subject_id`, `charttime`, `wbc` | `complete_blood_count.patient_key`, `encounter_key`, `specimen_key`, plus the listed fields | lab Observation Patient/reference/effective paths; Quantity value for code `51301` | total 2,959; charttime 2,959; wbc 2,759 |
| `enzyme.subject_id`, `charttime`, `bilirubin_total` | `enzyme.patient_key`, `encounter_key`, `specimen_key`, plus the listed fields | lab Observation Patient/reference/effective paths; Quantity value for code `50885` | total 1,411; charttime 1,411; bilirubin_total 1,146 |
| `gcs.stay_id`, `gcs.charttime`, `gcs.gcs` | `gcs.icu_encounter_key`, `gcs.patient_key`, `gcs.charttime`, `gcs.gcs` | ICU Observation reference `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}`; ICU identifier; effective dateTime; GCS Quantity/component derivation | 3,279/3,279 for all three |
| `urine_output.stay_id`, `charttime`, `urineoutput` | `urine_output.icu_encounter_key`, `patient_key`, `charttime`, `urineoutput` | ICU Observation encounter reference and ICU identifier; effective dateTime; Quantity values from the outputevents item set | total 7,317; all three fields 7,317/7,317 |
| `ventilation.stay_id`, `starttime`, `endtime`, `ventilation_status` | `ventilation.icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `ventilation_status` | published `oxygen_delivery`/`ventilator_setting` relations, ultimately chartevents effective dateTime, text/component paths, and ICU Encounter key | total 209; start/end/status 209/209; `InvasiveVent` 61 |
| `vitalsign.subject_id`, `charttime`, `heart_rate`, `sbp`, `temperature` | `vitalsign.patient_key`, `icu_encounter_key`, `charttime`, plus the listed fields | ICU Observation reference/effective paths; Quantity codes `220045` (heart rate), `220179`/`220050`/`225309` (SBP), and `223761`/`223762` (temperature) | total 21,086; charttime 21,086; heart_rate 13,910; sbp 14,002; temperature 3,764 |

The dependency FHIR paths and choice-type behavior are independently recorded
in the completed carryovers under `mimic-iv/concepts_fhir/carryover/<dependency>/fhir-prober.md`.
Quantity ViewDefinition aliases are strings and must be cast before numeric
aggregation. All dependency effective times used here are the dateTime choice;
the empty Period/instant variants must not be coalesced with a native timestamp.

The source SQL's dependency joins therefore become:

```text
age              ON hospital encounter_key
bg/chemistry/CBC/enzyme/vitalsign ON ICU patient_key + charttime window
gcs/urine_output/ventilation     ON ICU encounter_key (+ charttime/interval)
```

The implementer must use `FROM age`, `FROM bg`, `FROM chemistry`,
`FROM complete_blood_count`, `FROM enzyme`, `FROM gcs`, `FROM urine_output`,
`FROM ventilation`, and `FROM vitalsign`; it must not rederive these relations
from raw FHIR resources or join a published dependency on a stripped integer
identifier.

## Source-column to FHIRPath mapping

| Source column/expression | Canonical `{path, name}` mapping | FHIR type | Required final/use type |
|---|---|---|---|
| `icustays.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` on ICU Encounter, then Patient identifier projection | `Reference(Patient)` key plus `Identifier.value string` | emit `patient_key`; cast Patient identifier to `subject_id INTEGER` |
| `icustays.hadm_id` | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }`, then hospital Encounter identifier | `Reference(Encounter)` key plus `Identifier.value string` | cast hospital `hadm_id_str` to `hadm_id INTEGER` |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value string` | cast to `stay_id INTEGER`; retain `icu_encounter_key` |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | `dateTime`, materialized string | `CAST(... AS TIMESTAMP_NTZ)` → `starttime TIMESTAMP` |
| `starttime + INTERVAL 24 HOURS` | no single FHIR path | derived temporal expression | `endtime TIMESTAMP`; exact derivation from `starttime` |
| `admissions.subject_id` | hospital Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient identifier | reference key + FHIR string | output `subject_id INTEGER` and `patient_key` |
| `admissions.hadm_id` | hospital Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Identifier.value string` | `hadm_id INTEGER`; use hospital-system filter |
| `admissions.admission_type` | `{ "path": "priority.coding.code", "name": "admission_priority_code" }` plus `{ "path": "priority.coding.system", "name": "admission_priority_system" }` | `Coding.code` + `Coding.system` | `EL` means source `ELECTIVE`; any other served priority means source non-elective for this binary CASE |
| `services.curr_service` | `{ "path": "serviceType.coding.code", "name": "service_code" }` plus `{ "path": "serviceType.coding.system", "name": "service_system" }` | `Coding.code` + `Coding.system` | `LOWER(service_code) LIKE '%surg%'`; the first service is already selected upstream |
| `services.transfertime` | no direct FHIR path | source ordering input | absent after ETL selection, but the selected `serviceType` value agrees with the first source service 275/275; no sapsii output needs the timestamp |
| `diagnoses_icd.hadm_id` | Condition `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` → hospital Encounter identifier | reference key plus `Identifier.value string` | hospital join, then `hadm_id` grouping; Condition without a hospital Encounter is not part of this source stream |
| `diagnoses_icd.icd_code` | Condition coding `{ "path": "code", "name": "code" }` inside `forEach: "code.coding"` | `Coding.code string` | apply the exact trimmed prefix/range predicates |
| `diagnoses_icd.icd_version` | Condition coding `{ "path": "system", "name": "system" }` | `Coding.system uri` | ICD-9 system selects the version-9 predicates; ICD-10 system selects version-10 predicates |
| `chartevents.stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter identifier | reference key plus `Identifier.value string` | join to ICU key; cast identifier only if an integer is needed |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` string alias | `TIMESTAMP_NTZ`; CPAP window and interval expansion input |
| `chartevents.itemid` | coding `{ "path": "code", "name": "item_code" }` | `Coding.code string` | exact system + string code `226732` |
| `chartevents.value` | `{ "path": "(value).ofType(string)", "name": "value_string" }` | `string` | lower-case regex `(cpap mask|bipap)`; no CodeableConcept path and no UUID recovery |
| `bg.specimen` | dependency output from lab code `52033`, Observation `{ "path": "(value).ofType(string)", "name": "value_string" }` | derived `VARCHAR` | exact value `'ART.'`; no FHIR `Condition`/code filter |
| `bg.pao2fio2ratio` | dependency-derived numeric output from lab Quantity paths | derived numeric | use dependency value as `DOUBLE`; no raw rederivation in sapsii |
| `chemistry.bun` | dependency lab code `51006`, `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value decimal`, materialized string alias | dependency `DOUBLE`; source filter/cleaning already belongs to chemistry |
| `chemistry.potassium` | dependency lab code `50971`, same Quantity path | decimal/string alias | dependency `DOUBLE` |
| `chemistry.sodium` | dependency lab code `50983`, same Quantity path | decimal/string alias | dependency `DOUBLE` |
| `chemistry.bicarbonate` | dependency lab code `50882`, same Quantity path | decimal/string alias | dependency `DOUBLE` |
| `complete_blood_count.wbc` | dependency lab code `51301`, same Quantity path | decimal/string alias | dependency `DOUBLE` |
| `enzyme.bilirubin_total` | dependency lab code `50885`, same Quantity path | decimal/string alias | dependency `DOUBLE` |
| `gcs.gcs` | dependency output from ICU GCS Observation codes `223900`, `223901`, `220739`; numeric values use Quantity and the verbal sentinel uses component text | derived `FLOAT` | use dependency `FLOAT`; join on `icu_encounter_key` |
| `urine_output.urineoutput` | dependency output from outputevents code set and Quantity value path | derived `DOUBLE` | use dependency `DOUBLE`; join on `icu_encounter_key` |
| `ventilation.starttime/endtime` | dependency interval derived from Observation effective dateTime | derived `TIMESTAMP_NTZ` | overlap with BG charttime; join on `icu_encounter_key` |
| `ventilation.ventilation_status` | dependency CASE over oxygen/mode text, including component valueString where needed | derived `VARCHAR` | exact literal `InvasiveVent` |
| `vitalsign.heart_rate` | dependency chartevents code `220045`, Quantity value | derived `DOUBLE` | use dependency numeric value |
| `vitalsign.sbp` | dependency chartevents codes `220179`, `220050`, `225309`, Quantity value | derived `DOUBLE` | use dependency numeric value |
| `vitalsign.temperature` | dependency chartevents codes `223761`/`223762`, Quantity value with Fahrenheit conversion | derived `DECIMAL(38,2)`/numeric | use dependency value; no raw FHIR rederivation |
| final `sapsii` and component scores | no single FHIR path | derived integer score expressions | manifest `INTEGER`; preserve NULL component values before the final `COALESCE(..., 0)` sum |
| final `sapsii_prob` | no single FHIR path | derived logistic expression | manifest `DOUBLE` |

## Code and literal confirmation

The rule is always the served `system` plus the exact source literal. No
terminology expansion or translation is performed.

### Chartevents CPAP

The unconstrained chartevents coding stream has system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` (the
current Delta probe reports 668,862 coding rows over 668,862 distinct
Observation resources). The exact target code is `226732`: 3,145 FHIR coded
rows over 3,145 resources, ratio **1.000**. The source/FHIR CPAP value filter
has 32 rows, split FHIR `CPAP mask` 4 and `Bipap mask` 28; DuckDB has 32. The
code alone is safe here because this is the chartevents-specific system; the
shared `mimic-d-items` outputevents/datetimeevents issue does not apply.

### Dependency literal `bg.specimen = 'ART.'`

This is not a FHIR coding filter after the `bg` dependency boundary. The
underlying lab carrier is Observation code `52033` under
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, with 1,033/1,033
code rows/resources, ratio **1.000**, and 1,033/1,033 `valueString` values in
the target Delta probe. The derived `bg` oracle has 889 rows, 872 non-null
`specimen`, 706 rows with `specimen = 'ART.'`, and 563 non-null
`pao2fio2ratio` values. The exact literal is therefore applied to the
published dependency string, not to `Observation.code`.

### Dependency literal `ventilation_status = 'InvasiveVent'`

This is also a derived string discriminator, not a FHIR coding filter. The
demo `ventilation` relation has 209 rows and 209 non-null statuses: 61
`InvasiveVent`, 4 `NonInvasiveVent`, 5 `HFNC`, and 139 `SupplementalOxygen`.
The status is produced by the completed `ventilation` dependency from the
chartevents code systems and text/component paths; sapsii must consume the
literal `InvasiveVent` exactly.

### Hospital service/admission classification

The first-service FHIR projection uses
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services`; its code agrees
with the first DuckDB `services` row by `transfertime` on 275/275 admissions.
`LOWER(service_code) LIKE '%surg%'` is true for 76/275 first-service rows on
both sides. The priority system is
`http://terminology.hl7.org/CodeSystem/v3-ActPriority`; `EL` agrees with
`admission_type = 'ELECTIVE'` on 275/275 rows (13 true, 262 false). No
terminology lookup is involved.

### Condition ICD prefix predicates

Counts below are `source diagnoses_icd rows / hospital-Encounter-linked FHIR
Condition rows`; all are from the demo oracle and current Delta probe. A zero
is a measured zero, not permission to remove the source predicate.

| Source predicate | Source/FHIR rows |
|---|---:|
| ICD-9 `042`–`044` (AIDS) | 0 / 0 |
| ICD-10 `B20`–`B22` (AIDS) | 3 / 3 |
| ICD-10 `B24` (AIDS) | 0 / 0 |
| ICD-9 `20000`–`20238` | 2 / 2 |
| ICD-9 `20240`–`20248` | 0 / 0 |
| ICD-9 `20250`–`20302` | 7 / 7 |
| ICD-9 `20310`–`20312` | 0 / 0 |
| ICD-9 `20302`–`20382` | 0 / 0 |
| ICD-9 `20400`–`20522` | 6 / 6 |
| ICD-9 `20580`–`20702` | 0 / 0 |
| ICD-9 `20720`–`20892` | 0 / 0 |
| ICD-9 prefixes `2386` or `2733` | 0 / 0 |
| ICD-10 `C81`–`C96` (hematologic malignancy) | 27 / 27 |
| ICD-9 `1960`–`1991` (metastatic cancer) | 14 / 14 |
| ICD-9 `20970`–`20975` | 0 / 0 |
| ICD-9 `20979` or `78951` | 0 / 0 |
| ICD-10 `C77`–`C79` | 2 / 2 |
| ICD-10 `C800` | 0 / 0 |

The combined hospital diagnosis flags therefore reach 3 AIDS rows, 42
hematologic-malignancy rows, and 16 metastatic-cancer rows before the
one-admission `MAX` grouping. The source flags are grouped by `hadm_id`; the
FHIR implementation must group the hospital Conditions by their resolved
hospital `encounter_key`, not by Condition resource UUID.

## Oracle checks

The following cheap checks were run against `/Users/nau025/warehouses/mimic4-demo.db`:

* ICU Encounter identifier, `period.start`, patient reference, and
  hospital-parent reference were checked on the 140 ICU stays; stay id and
  `intime` agreed 140/140.
* Hospital Encounter `hadm_id`, priority elective bit, first service code,
  and surgical predicate agreed 275/275. The first-service comparison uses
  `ROW_NUMBER() OVER (PARTITION BY hadm_id ORDER BY transfertime)` on the
  source side.
* CPAP code `226732` and its value/time/stay target agreed 32/32 after the
  source/FHIR text whitespace normalization.
* Hospital diagnosis Conditions agreed with `diagnoses_icd` on the full
  `(subject_id, hadm_id, trimmed code, version-system)` multiset 4,506/4,506.
* Dependency source totals and non-null counts used for the consumer boundary
  were queried directly from `mimiciv_derived` and are listed in the dependency
  table above. The dependency carryovers also record their own Observation /
  Specimen / Encounter path checks and completed-attempt comparisons.

## Gaps and representability

### Identity and hospital/ICU joins

`subject_id`, `hadm_id`, and `stay_id` are absent as scalar values from the
FHIR references but are exactly derivable through Patient/Encounter
`identifier.value`. The ICU `partOf` reference preserves the hospital
Encounter join. This is **absent but derivable**, not a data gap, and is
essential only as the output identity; use the identifier paths and preserve
the three opaque key companions.

### `services.transfertime`

The timestamp used to select the first service is not a FHIR element. The
selected `serviceType.coding.code` is already present and agreed with the
source first-service result 275/275. This is **absent but derivable/preserved
as the selected value**, does not change row inclusion or grouping in sapsii,
and should not be reconstructed from a resource ID.

### Patient anchor pair and the age dependency

`anchor_age` and `anchor_year` themselves are not consumed by the sapsii SQL;
the dependency consumes `age`. The current FHIR `age` mapping is exact on the
demo admissions (275/275), including all 140 demo ICU stays. The full-data age
carryover has measured 460 conflicting age rows among 431,231 admissions after
the upstream birthDate transformation; the sapsii-specific intersection with
73,181 ICU stays was not available in this local demo oracle. Thus the
individual anchor fields are **not representable**, while the best served
`age` derivation is available. If an affected ICU stay changes `age_score`,
the loss reaches `age_score`, `sapsii`, `sapsii_prob`, and possibly only those
derived score columns. It is potentially clinically meaningful, but its
sapsii-specific reach must be bounded by the full comparator before any
whole-concept conclusion. No typed NULL can replace `age` because it is a
score discriminator; the prober makes no terminal block/accept decision.

### Diagnosis and service coverage

No current demo gap was found. The hospital Condition subset and all named ICD
prefix predicates agree with the oracle, and the priority/service projections
agree 275/275. ED Conditions (545 of the 5,051 combined Condition resources)
are excluded by the surviving hospital Encounter identifier discriminator;
this is intentional row selection, not missing data.

### CPAP text and dependency values

No current demo gap was found for CPAP: the target text is present on 3,145/3,145
item-226732 Observations and the source predicate selects 32/32 exact rows.
The required dependency values are represented in the completed dependency
relations; the missing lab Encounter references are not consumed by sapsii's
lab joins, which use Patient/time. GCS text is represented by the rebuilt
`Observation.component.valueString` branch in the completed dependency.

### Datetimes

All mapped datetime choices are the dateTime strings and must be cast as
`TIMESTAMP_NTZ`, never converted as instants. The rebuilt UTC Delta probe found
the ICU `intime` mapping exact 140/140 and the CPAP target effective times
exact 32/32. The historical DST-gap issue in the curated notes is marked fixed
for the current warehouse; a full sapsii comparison must still use the current
warehouse and must not apply a historical one-hour correction.

## Notes and provisional fragments consulted

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

* Delta tables, not stale NDJSON or the live server, are authoritative.
* MIMIC identifiers are string-valued `identifier.value`; resource/reference
  keys are separate opaque, type-prefixed equality keys and are required
  companion columns.
* Encounter streams require exact identifier-system filtering; `class` does
  not discriminate hospital, ICU, and ED.
* Observation item codes are verbatim source itemids and must be filtered by
  `system + exact code`, never `meta.profile`.
* Chartevents categorical values use `value.ofType(string)` and rebuilt
  numeric-row text can use `component.valueString`.
* Choice-type datetimes require separate `ofType()` projections and
  `TIMESTAMP_NTZ`; the current UTC rebuild supersedes the historical DST loss.
* Quantity aliases are string-like and require numeric casts.
* Encounter diagnosis backbones are empty, so diagnoses must be joined from
  `Condition`.
* The curated note's historical statement that served `Condition.code` uses
  proper ICD URIs did **not** agree with the current Delta probe. The mapping
  follows the served proprietary systems and the upstream ETL SQL; this new
  dataset-level finding was appended to the owned fragment below.

The following provisional fragments were read as leads: `README.md`,
`apsiii.md`, `age.md`, `gcs.md`, `first_day_gcs.md`, `first_day_vitalsign.md`,
`first_day_bg.md`, `first_day_urine_output.md`, `chemistry.md`,
`complete_blood_count.md`, `urine_output.md`, `ventilation.md`,
`vitalsign.md`, `oxygen_delivery.md`, `ventilator_setting.md`,
`icustay_times.md`, `icustay_detail.md`, `lods.md`, `kdigo_stages.md`,
`blood_differential.md`, `coagulation.md`, `cardiac_marker.md`, and
`code_status.md`. Relevant identifier, datetime, choice-type, component-text,
dependency-key, and system-before-code claims were independently checked
against the current Delta or the completed dependency carryovers. Unrelated
medication and concept-specific claims were not adopted. There was no existing
`MIMIC_NOTES.d/sapsii.md` fragment before this run.

One new dataset-wide finding was appended to:

`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sapsii.md`

It records the current Delta's proprietary `Condition.code` systems and the
5,051/5,051 coding cardinality check. `MIMIC_NOTES.md` was not edited.

## Evidence block

Concept: `sapsii`. Source tables map to ICU `Encounter`, hospital `Encounter`,
`Patient`, chartevents `Observation`, and hospital-linked `Condition`; the
measurement inputs are consumed from published derived relations `age`, `bg`,
`chemistry`, `complete_blood_count`, `enzyme`, `gcs`, `urine_output`,
`ventilation`, and `vitalsign`. Source identifiers map through Patient and
Encounter `identifier.value`; source keys map to `getResourceKey()` or
`getReferenceKey()` as listed above. The CPAP source item maps to Observation
code/system `226732`/`mimic-chartevents-d-items` and `value.ofType(string)`;
the diagnosis filters map to Condition `code`/`system` using the confirmed
proprietary ICD-9/ICD-10 systems and the exact prefix table above. CPAP rows
agree 32/32 with DuckDB, hospital diagnosis tuples agree 4,506/4,506, and
hospital service/admission classification agrees 275/275. The only identified
representability concern is the inherited full-data age derivation conflict;
its sapsii-specific reach is not bounded by the demo and must be measured by
the full comparator. The reusable mapping is this file, and the new
dataset-wide Condition-system finding is in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sapsii.md`.
