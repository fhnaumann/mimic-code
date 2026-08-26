# FHIR probe and mapping: `apsiii`

**Probed:** 2026-08-25  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/apsiii/source-analyst.md`  
**Canonical source:** `mimic-iv/concepts/score/apsiii.sql`  
**Authoritative FHIR warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone UTC  
**Read-only source oracle:** `/Users/nau025/warehouses/mimic4-demo.db`  

This is a mapping artifact, not a ViewDefinition or terminal
representability decision. No HTTP Pathling server was used. No FHIR resource
id was parsed, regenerated, hashed, hardcoded, or used to infer a source value.

## Scope, grain, and dependency boundary

The source SQL is one row per ICU stay, preserving every `icustays` row with a
final `LEFT JOIN score ON stay_id`. The manifest has 73,181 full rows, key
`stay_id`, and these output types:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
apsiii INTEGER, apsiii_prob DOUBLE,
hr_score INTEGER, mbp_score INTEGER, temp_score INTEGER,
resp_rate_score INTEGER, pao2_aado2_score INTEGER,
hematocrit_score INTEGER, wbc_score INTEGER, creatinine_score INTEGER,
uo_score INTEGER, bun_score INTEGER, sodium_score INTEGER,
albumin_score INTEGER, bilirubin_score INTEGER, glucose_score INTEGER,
acidbase_score INTEGER, gcs_score INTEGER
```

The completed dependencies are consumed by their unqualified published view
names and must not be rederived from raw FHIR resources:

```text
bg, first_day_gcs, first_day_lab, first_day_urine_output,
first_day_vitalsign, ventilation
```

Published dependencies carry opaque resource keys. Their paired integer
identifiers are stripped at the dependency boundary, so joins use
`icu_encounter_key`, `patient_key`, and `encounter_key`, never a dropped
`stay_id`/`subject_id`/`hadm_id` and never a parsed UUID.

## MIMIC source table → MIMIC-on-FHIR resource/interface

| MIMIC source/interface | FHIR resource or interface | Role in APS III |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter`, ICU stream selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Driving one-row-per-stay spine; supplies ICU identity and time window |
| `mimiciv_hosp.admissions` | `Encounter`, hospital stream selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | Parent of the ICU Encounter; represents the source `hadm_id` inner join |
| `mimiciv_hosp.patients` | `Patient` | Represents the source `subject_id` inner join |
| `mimiciv_hosp.diagnoses_icd` | `Condition` plus its hospital `Encounter` reference | CKD flag; code and ICD-version predicates are applied to Conditions linked to hospital Encounters |
| `mimiciv_derived.bg` | Published `bg` dependency, ultimately lab/chart `Observation` + `Specimen` | Blood-gas values, specimen, admission key, and chart time |
| `mimiciv_derived.first_day_gcs` | Published `first_day_gcs` dependency, ultimately chartevents `Observation` | GCS components and `gcs_unable` |
| `mimiciv_derived.first_day_lab` | Published `first_day_lab` dependency, ultimately lab `Observation` + `Specimen` | First-day laboratory extrema |
| `mimiciv_derived.first_day_urine_output` | Published `first_day_urine_output` dependency, ultimately outputevents `Observation` | First-day urine total |
| `mimiciv_derived.first_day_vitalsign` | Published `first_day_vitalsign` dependency, ultimately chartevents `Observation` | First-day vital-sign extrema |
| `mimiciv_derived.ventilation` | Published `ventilation` dependency, ultimately chartevents `Observation` | Ventilation intervals and first-day invasive-ventilation flag |

The source `INNER JOIN admissions` and `INNER JOIN patients` retain all 140
demo ICU rows: source counts were 140/140 for both joins. The ICU `partOf`
reference is the exact FHIR equivalent of `icustays.hadm_id` in this served
warehouse.

## Canonical FHIRPath projections

The following are the exact `{path, name}` mappings. Identifier aliases are
FHIR strings and must be cast in the final SQL; resource/reference keys remain
uncast, type-prefixed opaque strings.

### Patient

```json
{
  "resource": "Patient",
  "select": [{"column": [
    {"path": "getResourceKey()", "name": "patient_key"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
  ]}]
}
```

### ICU Encounter

```json
{
  "resource": "Encounter",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "icu_encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "partOf.getReferenceKey(Encounter)", "name": "encounter_key"},
      {"path": "period.start", "name": "intime_datetime"},
      {"path": "period.end", "name": "outtime_datetime"}
    ]},
    {"forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')", "column": [
      {"path": "system", "name": "stay_system"},
      {"path": "value", "name": "stay_id_str"}
    ]}
  ]
}
```

The ICU identifier system, not `Encounter.class`, selects the stream. The
`partOf` key is joined to the hospital Encounter view below. In the focused
probe, ICU rows were 140/140 for each of `icu_encounter_key`, `patient_key`,
`encounter_key`, `stay_id_str`, `intime_datetime`, and
`outtime_datetime`; the parent and patient joins were 140/140.

### Hospital Encounter parent

```json
{
  "resource": "Encounter",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}
    ]},
    {"forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')", "column": [
      {"path": "system", "name": "hadm_system"},
      {"path": "value", "name": "hadm_id_str"}
    ]}
  ]
}
```

### Condition CKD input

The Condition resource has one coding per resource in the probe. Project its
coding as follows and join `encounter_key` to the hospital Encounter view:

```json
{
  "resource": "Condition",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "condition_key"},
      {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}
    ]},
    {"forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9' or system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10')", "column": [
      {"path": "code", "name": "code"},
      {"path": "system", "name": "system"},
      {"path": "display", "name": "display"}
    ]}
  ]
}
```

The `Condition` resource itself contains ED-linked diagnoses as well as
hospital-linked diagnoses. Therefore the APS III mapping must retain only
Conditions whose `encounter_key` resolves to an Encounter carrying the
hospital identifier system. This is how the 4,506-row source
`diagnoses_icd` table is recovered from 5,051 served Conditions.

### Upstream Observation provenance for dependency fields

APS III does not author these Observation views. These paths document the
already-completed dependency mappings; the consumer reads the published
dependency columns.

| Dependency field/provenance | Canonical FHIRPath | FHIR type | Published/use type |
|---|---|---|---|
| `bg.charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | dependency `TIMESTAMP_NTZ` |
| `bg.po2`, `aado2`, `ph`, `pco2`, `fio2` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | dependency numeric `DOUBLE` |
| `bg.fio2_chartevents` | same Quantity path on the completed chart FiO2 pivot | `Quantity.value decimal` | dependency `FLOAT` |
| `bg.specimen` | `{path: "(value).ofType(string)", name: "value_string"}` on the completed lab specimen-text item | `string` | dependency `VARCHAR` |
| `bg` hospital identity | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` | nullable `Reference(Encounter)` | dependency opaque `STRING` |
| first-day dependency stay identity | `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}` → ICU `{path: "getResourceKey()", name: "icu_encounter_key"}` | `Reference(Encounter)` / resource key | dependency opaque `STRING` |
| first-day dependency patient identity | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `Reference(Patient)` | dependency opaque `STRING` |
| `ventilation.starttime`, `endtime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | dependency `TIMESTAMP_NTZ` |
| `ventilation.ventilation_status` | completed oxygen/mode dependency pivots from `valueString` and repaired `component.valueString` | derived string, not a FHIR coding | dependency `VARCHAR` |
| `first_day_urine_output.urineoutput` | completed outputevents Quantity path `{path: "(value).ofType(Quantity).value", name: "value_quantity"}` | `Quantity.value decimal` | dependency `DOUBLE` |

Use direct `TRY_CAST(... AS TIMESTAMP_NTZ)` for served datetime strings. Do
not parse offsets as instants and do not coalesce the dateTime string with the
empty Period/instant variants.

## Source-column → FHIRPath mapping and types

### Direct ICU and hospital identity columns

| Source column | Canonical mapping (`{path, name}`) | FHIR type / materialized type | Required target type/use |
|---|---|---|---|
| `icustays.subject_id` | Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` → Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | Reference key + Identifier.value `string` / `STRING` | `CAST(subject_id_str AS INTEGER)` → `subject_id`; emit `patient_key` |
| `icustays.hadm_id` | ICU Encounter `{path: "partOf.getReferenceKey(Encounter)", name: "encounter_key"}` → hospital Encounter identifier `{path: "value", name: "hadm_id_str"}` under the hospital system | Reference/resource key + Identifier.value `string` / `STRING` | `CAST(hadm_id_str AS INTEGER)` → `hadm_id`; emit `encounter_key` |
| `icustays.stay_id` | ICU Encounter identifier `{path: "value", name: "stay_id_str"}` inside ICU-system `identifier` | Identifier.value `string` / `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id`; emit `icu_encounter_key` |
| `icustays.intime` | ICU Encounter `{path: "period.start", name: "intime_datetime"}` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(... AS TIMESTAMP_NTZ)`; full `[intime,outtime)` blood-gas window and first-day dependency windows |
| `icustays.outtime` | ICU Encounter `{path: "period.end", name: "outtime_datetime"}` | FHIR `dateTime` / offset-bearing `STRING` | `TRY_CAST(... AS TIMESTAMP_NTZ)`; exclusive blood-gas upper bound |
| ICU resource identity | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque type-prefixed resource key / `STRING` | Equality join and required key output only |
| hospital resource identity | hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}` | opaque type-prefixed resource key / `STRING` | Equality join and required `encounter_key` output |
| patient resource identity | Patient `{path: "getResourceKey()", name: "patient_key"}` | opaque type-prefixed resource key / `STRING` | Equality join and required `patient_key` output |

The canonical candidate should use the ICU Encounter as the left spine, join
its `encounter_key` to the hospital Encounter key, and join each published
dependency's `icu_encounter_key` to `icu_encounter_key`.

### Dependency fields consumed by APS III

These are fields of completed derived interfaces, not new FHIR resource
columns. The FHIR provenance is shown above; the implementer must select the
published names directly.

| Published dependency | Consumed fields | Published type | Demo rows/non-null for each consumed field |
|---|---|---|---|
| `bg` | `encounter_key`, `charttime`, `po2`, `aado2`, `ph`, `pco2`, `fio2`, `fio2_chartevents`, `specimen` | key `STRING`; charttime `TIMESTAMP_NTZ`; numeric `DOUBLE` except `fio2_chartevents FLOAT`; specimen `VARCHAR` | total 889; encounter key 837; charttime 889; po2 889; aado2 889; ph 28; pco2 889; fio2 136; fio2_chartevents 546; specimen 872 |
| `ventilation` | `icu_encounter_key`, `starttime`, `endtime`, `ventilation_status` | key `STRING`; times `TIMESTAMP_NTZ`; status `VARCHAR` | total 209; each field 209 |
| `first_day_gcs` | `icu_encounter_key`, `gcs_min`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs_unable` | key `STRING`; GCS components `FLOAT`; unable `INTEGER` | total 140; ICU key 140; gcs_min 140; motor 80; verbal 80; eyes 80; unable 0 |
| `first_day_lab` | `icu_encounter_key`, `hematocrit_min/max`, `wbc_min/max`, `creatinine_min/max`, `bun_min/max`, `sodium_min/max`, `albumin_min/max`, `bilirubin_total_min/max`, `glucose_min/max` | key `STRING`; aggregates `DOUBLE` | total 140; ICU key 140; hematocrit 140/140; WBC 139/139; creatinine 139/139; BUN 140/140; sodium 140/140; albumin 140/140; bilirubin 57/57; glucose 77/77 |
| `first_day_vitalsign` | `icu_encounter_key`, `heart_rate_min/max`, `mbp_min/max`, `temperature_min/max`, `resp_rate_min/max`, `glucose_min/max` | key `STRING`; numeric aggregates `DOUBLE`, temperature extrema `DECIMAL(38,2)` in the published interface | total 140; ICU key 140; heart rate 140/140; MBP 140/140; temperature 139/139; respiratory rate 135/135; glucose 140/140 |
| `first_day_urine_output` | `icu_encounter_key`, `urineoutput` | key `STRING`; `DOUBLE` | total 140; ICU key 140; urineoutput 137 |

The corresponding DuckDB source counts were: `bg` 889 total with
`hadm_id` 837, ART specimen 706, `ph` 28; ventilation 209 total with 61
`InvasiveVent`; first-day GCS all five source fields 140/140 with 23
`gcs_unable=1`; first-day lab and vital counts agree with the table above; and
urine output is 137/140. The completed dependency carryovers contain the
full-data mappings and should remain the authority for upstream item pivots,
windows, and aggregates.

## Coded and categorical filters

APS III itself has **no direct itemid filter**. Its source literals are derived
categorical values and diagnosis-code prefixes. Do not re-lift the itemids of
`bg`, GCS, first-day lab/vitals, urine output, or ventilation into APS III;
those code sets belong to the completed dependencies.

### Condition code system and CKD prefix counts

The authoritative demo Delta currently carries the following systems (this
fresh result differs from the older curated note that described proper
`icd-9-cm`/`icd-10-cm` systems):

```text
ICD-9:  http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9
ICD-10: http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10
```

The source discriminator is the exact system plus the source prefix predicate,
after restricting Conditions to hospital Encounter references. Coding rows
per Condition resource were 5,051/5,051 = **1.000** overall and 21/21 =
**1.000** for the APS prefix target after the hospital Encounter join.

| Source literal | FHIR system | FHIR rows/resources after hospital-Encounter restriction | Source rows |
|---|---|---:|---:|
| `5854` | ICD-9 system above | 0 | 0 |
| `5855` | ICD-9 system above | 1 | 1 |
| `5856` | ICD-9 system above | 2 | 2 |
| `N184` | ICD-10 system above | 6 | 6 |
| `N185` | ICD-10 system above | 0 | 0 |
| `N186` | ICD-10 system above | 12 | 12 |

The unfiltered Condition counts for these prefixes are 5855=2, 5856=2,
N184=6, and N186=14 because two N186 and one 5855 Condition resources are
ED-linked. Code alone is therefore insufficient to reproduce the
`mimiciv_hosp.diagnoses_icd` stream; retain the hospital Encounter identifier
system as the table-stream discriminator. The full hospital-linked Condition
multiset agreed with DuckDB exactly: **4,506/4,506** rows, including
`hadm_id`, code, and ICD version.

Use the canonical coding projection:

```json
{
  "forEach": "code.coding",
  "column": [
    {"path": "code", "name": "code"},
    {"path": "system", "name": "system"},
    {"path": "display", "name": "display"}
  ]
}
```

The SQL then preserves the source predicates literally:

```sql
system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9'
AND SUBSTR(code, 1, 4) IN ('5854', '5855', '5856')

system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
AND SUBSTR(code, 1, 4) IN ('N184', 'N185', 'N186')
```

Do not use `meta.profile` or terminology expansion. `icd_version` is
derivable from the two observed coding-system URIs; no numeric
`icd_version` element is separately carried by FHIR.

### Derived categorical literals

These are not `code.coding` filters, so no FHIR coding system applies:

| Source literal | Published field | Demo count | Role |
|---|---|---:|---|
| `'ART.'` | `bg.specimen` | 706/889 | arterial blood-gas branches |
| `'InvasiveVent'` | `ventilation.ventilation_status` | 61/209 | ventilation interval joins and first-day vent flag |

The other ventilation status counts were HFNC 5, NonInvasiveVent 4, and
SupplementalOxygen 139. The specimen counts were ART. 706, CENTRAL VENOUS. 11,
MIX. 22, VEN. 133, and NULL 17. These are dependency values, not FHIR
CodeableConcept code sets.

## Oracle and served-data checks

* ICU FHIR spine: 140/140 rows, `stay_id`/`hadm_id`/`subject_id` exact against
  `mimiciv_icu.icustays`; all ICU parent and patient references resolved.
* Hospital-linked Conditions: 4,506/4,506 exact multiset against
  `mimiciv_hosp.diagnoses_icd`; the APS CKD prefix subset was 21/21 exact.
* Completed `bg` demo output: 889/889 full tuples exact against
  `mimiciv_derived.bg`; the 52 rows without a published hospital key were
  exactly the 52 source rows with NULL `hadm_id`, so APS's source inner join
  excludes them and this is not an output gap.
* Completed dependency demo population and types were checked from the latest
  candidate Parquet outputs under `mimic-iv/concepts_fhir/concepts/`; the
  dependency carryovers document the corresponding FHIR replay checks.
* Condition coding projection: 5,051/5,051 resource keys, patient keys,
  encounter keys, codes, systems, and displays were non-null; one coding per
  resource.

## Gaps and representability

### GCS discriminator: absent and not representable; potentially essential

The served `first_day_gcs` interface has `gcs_unable` non-null on 0/140 rows,
while the source dependency has it on 140/140 rows and `gcs_unable=1` on 23/140
selected rows. Served GCS motor/verbal/eyes values are each present on only
80/140 rows. The upstream probe measured the source-label loss counterfactual
as changing `gcs_min` on 43/140 rows, `gcs_verbal` on 41/140, `gcs_motor` on
6/140, and `gcs_eyes` on 12/140; the ambiguity involved 345 verbal
observations across 60 stays. A Quantity-1 heuristic was only 1,348/1,426
(94.53%) accurate and is forbidden as a mapping.

There is no FHIR path for the discarded `No Response` versus
`No Response-ETT` discriminator, and resource IDs are opaque. This is not a
typed-NULL-only row-local gap: the missing fields feed the clinically
meaningful `gcs_score`, then `apsiii` and `apsiii_prob`. Recommend that the
equivalence judge consider whole-concept blocking unless the dependency/ETL
preserves the discriminator. The prober does not make that terminal decision.

### Blood-gas hospital-key coverage: absent on rows already excluded by source

`bg.encounter_key` is non-null on 837/889 rows, exactly matching source
`bg.hadm_id` non-null on 837/889 rows. The remaining 52 source rows have NULL
`hadm_id` and cannot satisfy APS III's inner join to `icustays` by admission.
The missing FHIR reference is therefore not output-affecting for this concept;
do not manufacture an admission with a patient/time heuristic.

### Datetimes

The current UTC-rebuilt demo gave exact ICU `intime`/`outtime` spine values and
the completed dependency mappings use `TIMESTAMP_NTZ`. Historical DST-gap
normalization remains documented in `MIMIC_NOTES.md`, but it was not observed
in this focused demo. No timestamp correction or id side-channel is allowed;
any full-data divergence must be bounded by the comparator.

### Other fields

The source fields that are omitted from the final SELECT or not consumed by
APS III have no output mapping requirement. All final score columns are
computed SQL columns, not single FHIR elements; their inputs are the mapped
dependency fields above. Missing dependency measurements remain typed NULLs
until the canonical score CASE/COALESCE logic handles them.

## Final output provenance map

| Final source output | FHIR mapping/provenance | Required type |
|---|---|---|
| `subject_id` | Patient identifier `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `INTEGER` |
| `hadm_id` | Hospital Encounter identifier `{path: "value", name: "hadm_id_str"}` reached through ICU `{path: "partOf.getReferenceKey(Encounter)", name: "encounter_key"}` | `INTEGER` |
| `stay_id` | ICU Encounter identifier `{path: "value", name: "stay_id_str"}` | `INTEGER`, manifest key |
| `patient_key` | Patient `{path: "getResourceKey()", name: "patient_key"}` | opaque `STRING` |
| `encounter_key` | Hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}` | opaque `STRING` |
| `icu_encounter_key` | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque `STRING` |
| `apsiii` | Sum of the sixteen mapped component scores with source `COALESCE(...,0)` | `INTEGER` |
| `apsiii_prob` | Logistic expression over `apsiii` | `DOUBLE` |
| `hr_score` | `first_day_vitalsign.heart_rate_min/max` | `INTEGER` |
| `mbp_score` | `first_day_vitalsign.mbp_min/max` | `INTEGER` |
| `temp_score` | `first_day_vitalsign.temperature_min/max` | `INTEGER` |
| `resp_rate_score` | `first_day_vitalsign.resp_rate_min/max` plus ventilation flag | `INTEGER` |
| `pao2_aado2_score` | `bg.po2` / `bg.aado2` selected by the mapped blood-gas branches | `INTEGER` |
| `hematocrit_score` | `first_day_lab.hematocrit_min/max` | `INTEGER` |
| `wbc_score` | `first_day_lab.wbc_min/max` | `INTEGER` |
| `creatinine_score` | `first_day_lab.creatinine_min/max` plus derived ARF/CKD | `INTEGER` |
| `uo_score` | `first_day_urine_output.urineoutput` | `INTEGER` |
| `bun_score` | `first_day_lab.bun_min/max` | `INTEGER` |
| `sodium_score` | `first_day_lab.sodium_min/max` | `INTEGER` |
| `albumin_score` | `first_day_lab.albumin_min/max` | `INTEGER` |
| `bilirubin_score` | `first_day_lab.bilirubin_total_min/max` | `INTEGER` |
| `glucose_score` | merged `first_day_lab`/`first_day_vitalsign` glucose extrema | `INTEGER` |
| `acidbase_score` | `bg.ph` + `bg.pco2` interaction, worst score per stay | `INTEGER` |
| `gcs_score` | `first_day_gcs.gcs_unable`, `gcs_eyes`, `gcs_verbal`, `gcs_motor` | `INTEGER` |

## Notes consulted and finding appended

Established `MIMIC_NOTES.md` entries that changed this mapping were the Delta

Read provisional fragments as leads: `MIMIC_NOTES.d/README.md`,
`MIMIC_NOTES.d/gcs.md`, `MIMIC_NOTES.d/first_day_bg.md`,
`MIMIC_NOTES.d/first_day_vitalsign.md`,
`MIMIC_NOTES.d/first_day_urine_output.md`, `MIMIC_NOTES.d/icustay_times.md`,
`MIMIC_NOTES.d/vitalsign.md`, `MIMIC_NOTES.d/complete_blood_count.md`,
`MIMIC_NOTES.d/chemistry.md`, `MIMIC_NOTES.d/blood_differential.md`, and
`MIMIC_NOTES.d/coagulation.md`. The GCS loss and ICU identity/time leads were
verified against the focused APS probes; non-APS code-specific claims were
not adopted as APS filters. The Condition-system claim in the newly owned
fragment was independently verified against served Delta and DuckDB.

Appended to the owned fragment only:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/apsiii.md`, recording that the current
authoritative demo Delta exposes proprietary ICD diagnosis coding systems and
that hospital-linked Conditions recover `diagnoses_icd` exactly. `MIMIC_NOTES.md`
was not edited.

## Evidence block

Concept `apsiii`. Source tables map to ICU/hospital `Encounter`, `Patient`,
`Condition`, and six published dependency interfaces (`bg`,
`first_day_gcs`, `first_day_lab`, `first_day_urine_output`,
`first_day_vitalsign`, `ventilation`). Canonical mappings are the Patient
resource key and patient identifier paths; ICU Encounter resource key,
subject reference, `partOf` hospital reference, ICU identifier, and period
start/end paths; hospital Encounter resource key and hospital identifier path;
Condition resource/encounter/subject keys and `code.coding` `code/system/display`;
and the dependency Observation paths documented above. The confirmed CKD code
set is ICD-9 prefixes `5854` 0, `5855` 1, `5856` 2 and ICD-10 prefixes `N184` 6,
`N185` 0, `N186` 12 after hospital-Encounter restriction; coding rows per
Condition resource are 21/21 = 1.000 for the target and 5,051/5,051 = 1.000
overall. The non-coded literals are `bg.specimen='ART.'` 706/889 and
`ventilation_status='InvasiveVent'` 61/209. The essential GCS discriminator
gap is absent/not representable and reaches measured first-day GCS changes on
43/140 demo stays (23/140 source `gcs_unable=1`); no heuristic or ID side
channel is valid. The `bg` hospital-key nulls are bounded to 52 rows whose
source `hadm_id` is also NULL and are excluded by APS's source inner join.
ICU spine and hospital-linked Condition checks were exact 140/140 and
4,506/4,506; the selected CKD Condition multiset was 21/21 exact.

Carryover written at:
`mimic-iv/concepts_fhir/carryover/apsiii/fhir-prober.md`.
