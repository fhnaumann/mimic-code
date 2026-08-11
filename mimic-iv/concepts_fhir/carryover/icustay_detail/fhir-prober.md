# Corrected FHIR prober mapping: `icustay_detail`

**Date:** 2026-08-11 (re-probe after attempt 0001 invalidated the prior
fhir-prober carryover)  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/icustay_detail/source-analyst.md`  
**Natural key:** `stay_id`; the full oracle manifest identifies a keyed join with
73,181 rows.

The earlier analysis was a hypothesis only. This version corrects three
decisions: (1) US Core race and ethnicity `ombCategory` is a `Coding` value,
not a `CodeableConcept`; (2) Patient demographics are selected from the latest
hospital admission and include an ethnicity extension; and (3)
`hospital_expire_flag` is not derivable exactly and must be a typed NULL, not a
death-date-window estimate.

## Resource and stream mapping

| MIMIC-IV source table | FHIR resource/stream | Discriminator and authoritative demo cardinality |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter` ICU stream | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`; 140 resources; `partOf` populated 140/140 |
| `mimiciv_hosp.admissions` | `Encounter` hospital stream | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'`; 275 resources |
| `mimiciv_hosp.patients` | `Patient` | Patient identifier system `http://mimic.mit.edu/fhir/mimic/identifier/patient`; 100 resources |

The unfiltered Delta `Encounter` table has 637 resources: 275 hospital, 140
ICU, and 222 ED. `Encounter.class` is not a discriminator (ICU is `ACUTE`,
but hospital and ED classes overlap); use the identifier system. Join an ICU
Encounter to its hospital admission by
`{path: "partOf.getReferenceKey(Encounter)", name: "parent_encounter_key"}`
to the hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}`.
Then join both the ICU subject reference and the Patient resource key. Never
use `meta.profile` or `class` for this stream split.

There are no source coded filters. The literal code set is empty; no
`code.coding` projection or coding-per-resource ratio applies. The
identifier-system probe returned ED 222/222, hospital 275/275, and ICU
140/140 identifier rows, with one identifier row per Encounter (637/637).

## Canonical ViewDefinition projections

The `_key` aliases are UUID/reference strings used only for joins. The `_str`
aliases are FHIR identifier strings and must be cast by the outer concept SQL
to the manifest's integer output types. All served date/dateTime aliases are
string-like in Pathling; parse dateTime with `CAST(... AS TIMESTAMP_NTZ)`.

### Patient

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" },
    { "path": "gender", "name": "gender" },
    { "path": "birthDate", "name": "birth_date" },
    { "path": "(deceased).ofType(dateTime)", "name": "dod_datetime" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='text').value.ofType(string).first()", "name": "race_text" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).code.first()", "name": "race_omb_code" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).display.first()", "name": "race_omb_display" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).system.first()", "name": "race_omb_system" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url='text').value.ofType(string).first()", "name": "ethnicity_text" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url='ombCategory').value.ofType(Coding).code.first()", "name": "ethnicity_omb_code" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url='ombCategory').value.ofType(Coding).display.first()", "name": "ethnicity_omb_display" },
    { "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url='ombCategory').value.ofType(Coding).system.first()", "name": "ethnicity_omb_system" }
  ]
}
```

The four race text/code/system/display combinations observed in the demo are:

| race text/display | code | system | rows |
|---|---|---|---:|
| `Black or African American` | `2054-5` | `urn:oid:2.16.840.1.113883.6.238` | 10 |
| `White` | `2106-3` | `urn:oid:2.16.840.1.113883.6.238` | 72 |
| `asked but unknown` | `ASKU` | `http://terminology.hl7.org/CodeSystem/v3-NullFlavor` | 1 |
| `unknown` | `UNK` | `http://terminology.hl7.org/CodeSystem/v3-NullFlavor` | 17 |

The ETL's full supported race output set is broader than this 100-patient
demo: `Asian`/`2028-9`, `American Indian or Alaska Native`/`1002-5`, `Native
Hawaiian or Other Pacific Islander`/`2076-8`, and `other`/`OTH` can also occur,
in addition to the four demo values above. The race ETL mapping is many-to-one
from detailed `admissions.race` values to these OMB values.

The complete demo ethnicity result is:

| ethnicity text/display | code | system | rows |
|---|---|---|---:|
| `Hispanic or Latino` | `2135-2` | `urn:oid:2.16.840.1.113883.6.238` | 5 |
| `Not Hispanic or Latino` | `2186-5` | `urn:oid:2.16.840.1.113883.6.238` | 77 |
| NULL (no ethnicity extension) | NULL | NULL | 18 |

The ethnicity ETL writes only those two non-null values; `PATIENT DECLINED TO
ANSWER`, `UNABLE TO OBTAIN`, `UNKNOWN`, and `OTHER` map to no ethnicity
extension. The OMB projections must use `.ofType(Coding)`: raw `_extension`
contains `valueCoding`. The prior `.ofType(CodeableConcept)` hypothesis
materialized 0/100 race codes and 0/100 ethnicity codes.

### Hospital Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" },
    { "path": "period.start", "name": "period_start" },
    { "path": "period.end", "name": "period_end" }
  ]
}
```

Filter the materialized view with `hadm_id_str IS NOT NULL`. All five columns
are served as strings; the two period columns are FHIR `dateTime` values.

### ICU Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "period_start" },
    { "path": "period.end", "name": "period_end" }
  ]
}
```

Filter with `stay_id_str IS NOT NULL`. All six columns are served as strings;
all 140 ICU rows populated every projected column. In particular, the
`partOf` UUID/reference join resolved 140/140 parents.

## Source column to FHIRPath mapping

FHIR types below are the types of the served elements/materialized aliases,
not the final oracle types. The implementer must cast identifiers and derived
numeric fields to the required output types explicitly.

| Source column/expression | Canonical FHIR mapping `{path, name}` | FHIR type as served | Required output / result |
|---|---|---|---|
| `icustays.subject_id` | ICU `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` joined to Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | reference key/string and identifier `string` | `CAST(subject_id_str AS INTEGER)` → `subject_id` (`INTEGER`) |
| `icustays.hadm_id` | ICU `{path: "partOf.getReferenceKey(Encounter)", name: "parent_encounter_key"}` joined to hospital `{path: "getResourceKey()", name: "encounter_key"}` and `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | reference key/string and identifier `string` | `CAST(hadm_id_str AS INTEGER)` → `hadm_id` (`INTEGER`) |
| `icustays.stay_id` | ICU `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | identifier `string` | `CAST(stay_id_str AS INTEGER)` → `stay_id` (`INTEGER`, natural key) |
| `icustays.intime` | ICU `{path: "period.start", name: "period_start"}` | FHIR `dateTime`, materialized offset-bearing `string` | `CAST(period_start AS TIMESTAMP_NTZ)` → `icu_intime` (`TIMESTAMP`) |
| `icustays.outtime` | ICU `{path: "period.end", name: "period_end"}` | FHIR `dateTime`, materialized offset-bearing `string` | `CAST(period_end AS TIMESTAMP_NTZ)` → `icu_outtime` (`TIMESTAMP`) |
| `admissions.hadm_id` | Hospital `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}`; used to resolve ICU `partOf` | identifier `string` | join-only source key; same cast → `hadm_id` |
| `admissions.subject_id` | Hospital `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` joined to Patient `{path: "getResourceKey()", name: "patient_key"}` | reference/resource key `string` | join/rank partition key; not emitted directly |
| `admissions.admittime` | Hospital `{path: "period.start", name: "period_start"}` | FHIR `dateTime`, materialized offset-bearing `string` | `CAST(... AS TIMESTAMP_NTZ)` → `admittime` (`TIMESTAMP`) |
| `admissions.dischtime` | Hospital `{path: "period.end", name: "period_end"}` | FHIR `dateTime`, materialized offset-bearing `string` | `CAST(... AS TIMESTAMP_NTZ)` → `dischtime` (`TIMESTAMP`) |
| `admissions.race` | Patient text `{path: "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='text').value.ofType(string).first()", name: "race_text"}` plus OMB `{path: "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).code.first()", name: "race_omb_code"}`, `{path: "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).display.first()", name: "race_omb_display"}`, `{path: "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='ombCategory').value.ofType(Coding).system.first()", name: "race_omb_system"}`; companion ethnicity text `{path: "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity').extension.where(url='text').value.ofType(string).first()", name: "ethnicity_text"}` and corresponding `Coding` code/display/system paths | nested extension `string` and `Coding` strings | `race` is absent from Encounter and only approximable: Patient ETL uses latest hospital admission, then many-to-one OMB maps detailed race. Do not claim exact source-race recovery. |
| `admissions.hospital_expire_flag` | no FHIR path | not present | `CAST(NULL AS SMALLINT)` → `hospital_expire_flag` (`SMALLINT`); declare unrepresentable |
| `admissions.deathtime` (not selected by source SQL) | no admission-level path; nearest Patient `{path: "(deceased).ofType(dateTime)", name: "dod_datetime"}` is patient-level `dod` | Patient `dateTime` exists, admission death time absent | not representable as admission `deathtime`; never substitute it for the flag |
| `patients.subject_id` | Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | identifier `string` | join-only duplicate of `subject_id` |
| `patients.gender` | Patient `{path: "gender", name: "gender"}` | FHIR `code`, materialized `string` | `male → M`, `female → F` → `gender` (`VARCHAR`) |
| `patients.dod` | Patient `{path: "(deceased).ofType(dateTime)", name: "dod_datetime"}` | FHIR `dateTime`, materialized `string` | `CAST(dod_datetime AS DATE)` → `dod` (`DATE`) |
| `patients.anchor_age` | no FHIR path; use Patient `{path: "birthDate", name: "birth_date"}` only as a collapsed input | FHIR `date`, materialized `string`; anchor value absent | approximate `admission_age`; anchor value not recoverable |
| `patients.anchor_year` | no FHIR path; hospital `{path: "period.start", name: "period_start"}` supplies event year | anchor value absent | approximate `admission_age`; anchor value not recoverable |
| `icustays.los` | no mapping required | raw column is not referenced by source SQL | recompute ICU LOS from period endpoints; do not use stored `ie.los` |

Derived output expressions use these mapped fields:

| Output column | FHIR inputs and derivation | Required oracle type |
|---|---|---|
| `los_hospital` | `DATEDIFF(TO_DATE(period_end), TO_DATE(period_start))` on hospital Encounter | `BIGINT` |
| `admission_age` | `YEAR(CAST(hospital.period_start AS TIMESTAMP_NTZ)) - YEAR(CAST(patient.birth_date AS DATE))`; best FHIR approximation to source anchor expression | `BIGINT` |
| `hospstay_seq` | `DENSE_RANK()` partitioned by Patient key, ordered by parsed hospital `period.start`, over admissions represented by ICU join | `BIGINT` |
| `first_hosp_stay` | `hospstay_seq = 1` | `BOOLEAN` |
| `los_icu` | `ROUND(((DATEDIFF(TO_DATE(icu.period_end), TO_DATE(icu.period_start)) * 24) + HOUR(icu_end) - HOUR(icu_start)) / 24.0, 2)` | `DECIMAL(38,2)` |
| `icustay_seq` | `DENSE_RANK()` partitioned by resolved `hadm_id`, ordered by parsed ICU `period.start` | `BIGINT` |
| `first_icu_stay` | `icustay_seq = 1` | `BOOLEAN` |

The final SQL must cast `subject_id_str`, `hadm_id_str`, and `stay_id_str` to
`INTEGER`; UUID keys must never be emitted as MIMIC IDs. Cast rank results to
`BIGINT`, hospital LOS and age to `BIGINT`, and retain ICU LOS as
`DECIMAL(38,2)`.

## Population and null-count checks

Every mapped field was materialized and counted as total rows versus non-null
rows in the authoritative demo:

| Materialized view | Rows | Non-null counts |
|---|---:|---|
| Patient | 100 | `patient_key` 100, `subject_id_str` 100, `gender` 100, `birth_date` 100, `dod_datetime` 31, `race_text` 100, `race_omb_code/display/system` 100 each, `ethnicity_text` 82, `ethnicity_omb_code/display/system` 82 each |
| hospital Encounter (after `hadm_id_str IS NOT NULL`) | 275 | `encounter_key`, `patient_key`, `hadm_id_str`, `period_start`, `period_end` all 275 |
| ICU Encounter (after `stay_id_str IS NOT NULL`) | 140 | `encounter_key`, `patient_key`, `parent_encounter_key`, `stay_id_str`, `period_start`, `period_end` all 140 |
| Encounter identifiers (`forEach: "identifier"`) | 637 | `system` 637, `value` 637; 637 identifier rows for 637 resources, ratio 1.0 |

Raw schema checks found `Patient.deceasedDateTime` 31/100 and
`deceasedBoolean` 0/100. `Encounter` has `period` and
`hospitalization.dischargeDisposition` (455/637), but no
`hospital_expire_flag` or `deathtime` field. The source DuckDB demo has 275
admissions with `hospital_expire_flag=1` on 15 and `deathtime` non-null on 15;
the 140 ICU-detail rows expand these to 20/140 each. These source values are
not admission-level FHIR data.

## Latest-admission and race/ethnicity checks

The served `Patient` ETL uses the maximum hospital `admissions.admittime` per
patient (then `MIN(race)` only if there is a tied maximum). The DuckDB demo
latest-admission query found 100/100 patients and no maximum-time ties. Mapping
the latest source race through the ETL's race table agreed with the served
Patient race text and OMB code on 100/100 patients; mapping the same latest
source value through the ethnicity table agreed with the served ethnicity text
(including the 18 null extensions) on 100/100. Thus the Patient demographic is
not the race of the ICU admission unless that admission is the patient's latest
hospital admission.

For the 140 ICU rows, only 84/140 hadm_ids were the patient's latest admission.
The current admission's detailed race equalled the latest-admission detailed
race on 139/140 rows; after collapsing both source values to the ETL's broad
race categories, 139/140 agreed. The detailed source `race` string is still not
recoverable from the broad FHIR extension: the previous attempt's raw text
comparison was 0/140, and its four-label reverse guess was only 122/140. The
correct reusable mapping therefore projects both race and ethnicity OMB
codings and declares source detailed/admission-specific race an approximation,
not an exact identity. The prior full-data diagnosis further partitioned race
residuals into 1,766 recoverable by decoding both extensions, 9,939 detailed
many-to-one losses, and 1,541 latest-admission substitutions.

## Oracle agreement and representability gaps

The DuckDB demo oracle `mimiciv_derived.icustay_detail` has 140 rows. A fresh
FHIR-side candidate joined ICU `partOf` to hospital Encounter and Patient UUID
keys and had 140 rows and 140 unique `stay_id` values. Exact keyed agreement
was 140/140 for every representable output:

```
subject_id 140/140       hadm_id 140/140          stay_id 140/140
gender 140/140           dod 140/140              admittime 140/140
dischtime 140/140        los_hospital 140/140     admission_age 140/140
icu_intime 140/140       icu_outtime 140/140      los_icu 140/140
hospstay_seq 140/140     first_hosp_stay 140/140  icustay_seq 140/140
first_icu_stay 140/140
```

The gaps are classified explicitly:

1. **`race`: absent but approximable.** Encounter has no race element. Patient
   race is latest-admission demographic data and detailed source values are
   many-to-one OMB mapped. Canonical broad-category agreement was 139/140 on
   the demo ICU rows, but the detailed source string has no exact inverse.
2. **`admission_age`: absent but approximable.** `anchor_age` and `anchor_year`
   are not served. The birthDate/year calculation is 140/140 on this demo;
   full-data evidence in `MIMIC_NOTES.md` found 460 conflicts among 431,231
   admission rows because FHIR birthDate is synthesized from
   `MIN(transfers.intime) - anchor_age`, not the anchor-year pair.
3. **`hospital_expire_flag`: not representable.** No FHIR element serializes
   the admission flag. Patient DOD plus period/discharge disposition does not
   invert it; the prior estimate generated 187 full-data conflicts and the
   stricter date equality still left 182. Emit `CAST(NULL AS SMALLINT)` and
   retain the gap declaration.
4. **Admission `deathtime`: not representable.** It is not serialized on
   Encounter. Patient `deceasedDateTime` is patient-level `patients.dod`, not
   admission `admissions.deathtime`; no exact derivation exists.
5. **DST-gap timestamps: not representable.** The upstream ETL casts source
   wall-clock times through `TIMESTAMPTZ`; `TIMESTAMP_NTZ` preserves the served
   wall clock but cannot restore a source time normalized in the DST gap. The
   curated full-data note reports 44/431,231 hospital admissions affected.

## Notes and provisional fragments consulted

The following established `MIMIC_NOTES.md` entries changed this mapping:

- Extensions are not a column: use `extension(url)`; this supplied the race
  and ethnicity FHIRPath rather than a raw `extension` column.
- MIMIC ids live in `identifier.value` as strings; UUID resource/reference keys
  remain join-only and the final SQL must cast identifiers to `INTEGER`.
- Encounter has three identifier systems and class discriminates none; this
  required hospital/ICU identifier-system filters and the ICU `partOf` join.
- `Patient.birthDate` is synthesized from transfers rather than the anchor
  pair; admission age is therefore only an approximation on full data.
- FHIR datetimes carry an offset; use `TIMESTAMP_NTZ`, and treat upstream
  DST-gap normalization as unrecoverable.

I read `MIMIC_NOTES.d/README.md` and every existing fragment: `arb.md`,
`blood_differential.md`, `cardiac_marker.md`, `chemistry.md`, `code_status.md`,
`complete_blood_count.md`, `coagulation.md`, `crrt.md`, `dobutamine.md`,
`dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`, `icp.md`, and this
concept's `icustay_detail.md`. The other fragments were provisional leads and
contained no applicable Patient/Encounter claim; they were not used as facts.
The applicable extension, OMB `Coding`, identifier, latest-admission,
datetime, and typed-null decisions were independently checked against the
authoritative Delta and DuckDB oracle above. The `icustay_detail` fragment's
earlier race/expiry hypotheses were superseded by its correction sections and
rechecked here.

No attempt artifact was edited and no implementation artifact was created.
