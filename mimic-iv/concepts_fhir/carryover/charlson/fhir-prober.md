# FHIR Prober Mapping: `charlson`

**Concept:** `charlson` (`comorbidity/charlson.sql`)
**Attempt:** `attempt_0001`
**Probe date:** 2026-08-14
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, read with embedded Pathling 9.6.0 / Spark 4.0.2
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB demo oracle)

This is a mapping and evidence artifact only. No ViewDefinition or `concept.sql`
was authored here. Resource/reference keys below are opaque strings used only for
equality joins; they must not be parsed, regenerated, hardcoded, or used as a
semantic side channel.

## Resources and stream selection

| MIMIC-IV source | FHIR resource | Probe result and required selection |
|---|---|---|
| `mimiciv_hosp.admissions` | `Encounter` | The Delta has 637 Encounter resources: 275 hosp, 140 ICU, 222 ED. Select the hospital stream with `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'`; this gives 275 rows and 275 distinct `hadm_id` values. `class` is not a discriminator. |
| `mimiciv_hosp.patients` | `Patient` | 100 resources; the patient identifier system is `http://mimic.mit.edu/fhir/mimic/identifier/patient`, with 100/100 identifier values populated and unique. |
| `mimiciv_hosp.diagnoses_icd` | `Condition` | `Condition` is a merged Delta resource table containing 5,051 diagnosis Conditions: 4,506 hospital-linked and 545 ED-linked. Select hospital diagnoses by joining the opaque `Condition.encounter.getReferenceKey(Encounter)` to `Encounter.getResourceKey()` and retaining the Encounter row whose hospital identifier value is non-null. Do not use `meta.profile` or `category`: all 5,051 have the same `mimic-condition` profile and `encounter-diagnosis` category. |

The Condition hospital filter is essential: ICD code/system alone does not
separate the hospital and ED streams. The hospital-linked join produced 4,506
Conditions across 275 hospital Encounters, exactly the demo
`mimiciv_hosp.diagnoses_icd` row count. The ED remainder was 545 Conditions
across 221 ED Encounters.

The natural grain is one row per hospital admission: `hadm_id` is the single
manifest key and the full oracle has 431,231 rows. The demo has 275 admissions.
Condition diagnosis rows are grouped to this grain; the one-coding-per-resource
cardinality does not introduce a coding fan-out.

## Source column -> FHIRPath mapping

All materialized Pathling aliases below were `STRING`/`VARCHAR`, including
identifier values, resource/reference keys, dates, and Condition coding fields.
The implementer must keep `_str`/`_key` aliases until the final query and cast
the manifest outputs (`subject_id`, `hadm_id`, all flags, and the index) to
`INTEGER`.

| Source input/output | FHIR resource | Canonical extraction `{path, name}` | FHIR type | Use / target type |
|---|---|---|---|---|
| `admissions` row identity for joins | `Encounter` | `{path: "getResourceKey()", name: "encounter_key"}` | `STRING` opaque resource key | Equality join to Condition encounter reference; not a `hadm_id`. |
| `admissions.subject_id` admission-to-patient FK | `Encounter` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `STRING` opaque reference key | Equality join to Patient key only. |
| `admissions.subject_id` / final `subject_id` | `Patient` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `STRING` | Cast to target `INTEGER` `subject_id`; do not use a resource key. |
| `admissions.hadm_id` / final `hadm_id` | `Encounter` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | `STRING` | Hospital-stream filter and cast to target `INTEGER` `hadm_id`. |
| `admissions.admittime` (transitive `age` input) | `Encounter` | `{path: "period.start", name: "period_start"}` | `STRING` ISO-8601 with offset | Use `CAST(period_start AS TIMESTAMP_NTZ)` or year extraction; target dependency type is `TIMESTAMP`. |
| `diagnoses_icd` row identity | `Condition` | `{path: "getResourceKey()", name: "condition_key"}` | `STRING` opaque resource key | Equality/deduplication only; no source value may be recovered from this key. |
| `diagnoses_icd.hadm_id` | `Condition` | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` | `STRING` opaque reference key | Equality join to Encounter `encounter_key`, then retain only hosp Encounter rows. |
| `diagnoses_icd.subject_id` relationship validation | `Condition` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `STRING` opaque reference key | Equality join to Patient; observed non-null for 4,506/4,506 hospital Conditions. |
| `diagnoses_icd.icd_version` | `Condition`, inside `code.coding` | `{path: "system", name: "code_system"}` under `forEach: "code.coding"` | `STRING` | Exact observed system is the version discriminator: suffix `mimic-diagnosis-icd9` means source version 9; suffix `mimic-diagnosis-icd10` means source version 10. |
| `diagnoses_icd.icd_code` | `Condition`, inside `code.coding` | `{path: "code", name: "icd_code"}` under `forEach: "code.coding"` | `STRING` | Verbatim code used by the source prefix/range tests. Constrain coding to the observed ICD systems inside `forEach` when authoring the view. |
| diagnosis display (not used by source SQL) | `Condition`, inside `code.coding` | `{path: "display", name: "icd_display"}` under `forEach: "code.coding"` | `STRING` | Populated 4,506/4,506 hospital codings; ancillary. |
| `patients.subject_id` | `Patient` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `STRING` | Equality key after casting only in the final SQL. |
| `patients.anchor_age` | `Patient` | No direct path; `{path: "birthDate", name: "birth_date"}` is the only relevant field | `STRING` date | `anchor_age` is not individually representable. `birthDate` is a lossy synthesis, not an exact anchor-age field. |
| `patients.anchor_year` | `Patient` | No direct path; `{path: "birthDate", name: "birth_date"}` is the only relevant field | `STRING` date | `anchor_year` is not individually representable. `anchor_year_group` is also absent and is not used by `age.sql`. |
| `age.hadm_id` dependency output | `Encounter` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | `STRING` | Same hospital admission key as above. |
| `age.age` dependency output | `Patient` + `Encounter` | `{path: "birthDate", name: "birth_date"}` plus `{path: "period.start", name: "period_start"}` | both `STRING` | FHIR-side expression `YEAR(period_start) - YEAR(birth_date)` (or year substrings), with the limitation below. |
| final `age_score` | Patient + hospital Encounter | Derived from the age expression using the source thresholds `<=50`, `<=60`, `<=70`, `<=80`, else 4 | target `INTEGER` | No direct FHIR element; do not treat the derived value as exact on full data without the age limitation. |
| final 17 comorbidity flags | hospital-linked `Condition` | `code_system` + `icd_code` from the coding extraction above, grouped by `hadm_id_str` | target `INTEGER` | `MAX(CASE ...)` per hospital admission, using the literal source prefix/range tests below. |
| final `charlson_comorbidity_index` | hospital-linked Conditions + age score | No direct FHIR element; weighted expression over the 17 flags and `age_score` | target `INTEGER` | Derived output; preserve source arithmetic exactly. |

For an implementation that extracts both ICD versions in one coding group, the
coding group should be constrained inside the iterator, for example
`forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9' or system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10')"`, with the three canonical columns `{path: "code", name: "icd_code"}`, `{path: "system", name: "code_system"}`, and `{path: "display", name: "icd_display"}`. The measured ratio is one coding per resource, but the system constraint is still the correct discriminator rule.

## Populated-field and cardinality counts

These are counts over the materialized probe rows, not schema-only claims:

| Probe view / field | Rows | Non-null | Distinct resource/key count |
|---|---:|---:|---:|
| Patient `getResourceKey()` | 100 | 100 | 100 |
| Patient patient-identifier `.value` | 100 | 100 | 100 values |
| Patient `birthDate` | 100 | 100 | 100 |
| Patient `gender` | 100 | 100 | 100 |
| all Encounter identifier rows | 637 | 637 resource keys / values | 637 |
| hospital Encounter identifier `.value` | 637 | 275 | 275 distinct values |
| all Encounter `subject.getReferenceKey(Patient)` | 637 | 637 | 637 |
| all Encounter `period.start` | 637 | 637 | 637 |
| Condition total | 5,051 | 5,051 resource keys | 5,051 |
| hospital-linked Condition rows | 4,506 | 4,506 | 4,506 |
| hospital Condition subject reference | 4,506 | 4,506 | 100 distinct Patient keys |
| hospital Condition encounter reference | 4,506 | 4,506 | 275 distinct Encounter keys |
| hospital Condition `code.coding.system` | 4,506 | 4,506 | 1 coding/resource |
| hospital Condition `code.coding.code` | 4,506 | 4,506 | 1 coding/resource |
| hospital Condition `code.coding.display` | 4,506 | 4,506 | 1 coding/resource |
| hospital Condition `recordedDate` | 4,506 | 0 | — |
| all Condition `onset[x]` variants probed | 5,051 | 0 for dateTime, Period.start/end, string | — |
| all Condition clinical/verification status text | 5,051 | 0 / 0 | — |

The unfiltered coding cardinality is 5,051 rows / 5,051 distinct Conditions,
ratio **1.000**. The source hospital stream is 4,506 / 4,506, also **1.000**.
The hospital and ED stream split was established by opaque reference-key
equality plus the exact Encounter identifier system, not by parsing any key.

## Actual ICD systems and discriminator warrant

The authoritative Delta carries these systems, not the standard `sid` URIs:

| Exact `Condition.code.coding.system` | Hospital coding rows / Conditions | Meaning used for source branch |
|---|---:|---|
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9` | 2,193 / 2,193 | source `icd_version = 9` |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10` | 2,313 / 2,313 | source `icd_version = 10` |

The warrant is the served coding data and the ETL branch: the current Delta
contains only these two systems for diagnosis Conditions. The current demo
also has one coding per Condition and the ICD code is non-null on every coding.
`meta.profile` cannot be used: all 5,051 Conditions project the same
`http://mimic.mit.edu/fhir/mimic/StructureDefinition/mimic-condition` profile.
`category` likewise cannot be used: all 5,051 carry the same
`http://terminology.hl7.org/CodeSystem/condition-category|encounter-diagnosis`.

The source code rule is therefore:

1. join Condition's opaque encounter reference to Encounter's opaque resource
   key;
2. retain the Encounter whose identifier system is the hospital system;
3. inside the single Condition coding, use **system + exact code/prefix**;
4. group by the hospital Encounter's `hadm_id_str`.

The two systems are necessary because the same literal can be meaningful in
different ICD versions. The hospital Encounter system is separately necessary
because ED Conditions use the same ICD coding systems and overlap the same code
space.

## Literal source code set confirmed against served hospital Conditions

Counts below are coding rows in the hospital-linked Condition stream. An exact
literal `X` means `SUBSTR(icd_code, 1, N) = X` with the source's length `N`; a
range `X-Y` means the source's lexical `BETWEEN X AND Y` on that prefix. Zero is
a measured demo count, not an unmarked deletion or a terminology substitution.

| Flag | ICD-9 literal counts | ICD-10 literal counts |
|---|---|---|
| `myocardial_infarct` | `410=3`, `412=8` | `I21=9`, `I22=0`, `I252=9` |
| `congestive_heart_failure` | `428=43`, `39891=0`, `40201=0`, `40211=0`, `40291=0`, `40401=0`, `40403=0`, `40411=0`, `40413=0`, `40491=1`, `40493=0`, `4254-4259=6` | `I43=0`, `I50=36`, `I099=0`, `I110=12`, `I130=9`, `I132=1`, `I255=2`, `I420=1`, `I425=0`, `I426=0`, `I427=1`, `I428=2`, `I429=0`, `P290=0` |
| `peripheral_vascular_disease` | `440=3`, `441=2`, `0930=0`, `4373=2`, `4471=1`, `5571=0`, `5579=3`, `V434=0`, `4431-4439=6` | `I70=4`, `I71=3`, `I731=0`, `I738=0`, `I739=3`, `I771=0`, `I790=0`, `I792=0`, `K551=0`, `K558=0`, `K559=0`, `Z958=5`, `Z959=0` |
| `cerebrovascular_disease` | `430-438=18`, `36234=0` | `G45=0`, `G46=0`, `I60-I69=20`, `H340=0` |
| `dementia` | `290=0`, `2941=1`, `3312=0` | `F00=0`, `F01=0`, `F02=0`, `F03=2`, `G30=0`, `F051=0`, `G311=0` |
| `chronic_pulmonary_disease` | `490-505=26`, `4168=5`, `4169=0`, `5064=0`, `5081=0`, `5088=0` | `J40-J47=33`, `J60-J67=1`, `I278=0`, `I279=0`, `J684=0`, `J701=0`, `J703=0` |
| `rheumatic_disease` | `725=0`, `4465=0`, `7100=0`, `7101=0`, `7102=5`, `7103=0`, `7104=0`, `7140=0`, `7141=0`, `7142=0`, `7148=0` | `M05=0`, `M06=0`, `M32=0`, `M33=0`, `M34=0`, `M315=0`, `M351=2`, `M353=0`, `M360=0` |
| `peptic_ulcer_disease` | `531=3`, `532=3`, `533=0`, `534=0` | `K25=2`, `K26=3`, `K27=0`, `K28=3` |
| `mild_liver_disease` | `570=3`, `571=11`, `0706=0`, `0709=0`, `5733=1`, `5734=0`, `5738=0`, `5739=0`, `V427=0`, `07022=0`, `07023=0`, `07032=1`, `07033=0`, `07044=1`, `07054=3` | `B18=2`, `K73=0`, `K74=3`, `K700=0`, `K701=4`, `K702=0`, `K703=11`, `K709=0`, `K713=0`, `K714=0`, `K715=0`, `K717=0`, `K760=0`, `K762=0`, `K763=0`, `K764=0`, `K768=1`, `K769=0`, `Z944=0` |
| `diabetes_without_cc` | `2500=38`, `2501=3`, `2502=1`, `2503=0`, `2508=4`, `2509=0` | `E100=0`, `E101=1`, `E106=0`, `E108=0`, `E109=0`, `E110=0`, `E111=0`, `E116=27`, `E118=1`, `E119=26`, `E120=0`, `E121=0`, `E126=0`, `E128=0`, `E129=0`, `E130=0`, `E131=0`, `E136=0`, `E138=0`, `E139=0`, `E140=0`, `E141=0`, `E146=0`, `E148=0`, `E149=0` |
| `diabetes_with_cc` | `2504=2`, `2505=1`, `2506=5`, `2507=0` | `E102=0`, `E103=0`, `E104=0`, `E105=0`, `E107=0`, `E112=20`, `E113=3`, `E114=14`, `E115=5`, `E117=0`, `E122=0`, `E123=0`, `E124=0`, `E125=0`, `E127=0`, `E132=0`, `E133=0`, `E134=0`, `E135=0`, `E137=0`, `E142=0`, `E143=0`, `E144=0`, `E145=0`, `E147=0` |
| `paraplegia` | `342=1`, `343=0`, `3341=0`, `3440=0`, `3441=0`, `3442=0`, `3443=0`, `3444=0`, `3445=0`, `3446=0`, `3449=0` | `G81=2`, `G82=0`, `G041=0`, `G114=0`, `G801=0`, `G802=0`, `G830=0`, `G831=0`, `G832=0`, `G833=0`, `G834=0`, `G839=0` |
| `renal_disease` | `582=1`, `585=33`, `586=0`, `V56=0`, `5880=0`, `V420=0`, `V451=2`, `5830-5837=0`, `40301=0`, `40311=0`, `40391=3`, `40402=0`, `40403=0`, `40412=0`, `40413=0`, `40492=0`, `40493=0` | `N18=39`, `N19=0`, `I120=8`, `I131=0`, `N032=0`, `N033=0`, `N034=0`, `N035=0`, `N036=0`, `N037=0`, `N052=0`, `N053=0`, `N054=0`, `N055=0`, `N056=0`, `N057=0`, `N250=0`, `Z490=0`, `Z491=0`, `Z492=0`, `Z940=0`, `Z992=11` |
| `malignant_cancer` | `140-172=16`, `1740-1958=2`, `200-208=15`, `2386=0` | `C43=0`, `C88=0`, `C00-C26=2`, `C30-C34=3`, `C37-C41=0`, `C45-C58=0`, `C60-C76=6`, `C81-C85=0`, `C90-C97=27` |
| `severe_liver_disease` | `4560=0`, `4561=1`, `4562=1`, `5722-5728=6` | `I850=0`, `I859=0`, `I864=0`, `I982=0`, `K704=2`, `K711=0`, `K721=0`, `K729=3`, `K765=0`, `K766=7`, `K767=4` |
| `metastatic_solid_tumor` | `196=2`, `197=5`, `198=6`, `199=1` | `C77=0`, `C78=2`, `C79=0`, `C80=0` |
| `aids` | `042=0`, `043=0`, `044=0` | `B20=3`, `B21=0`, `B22=0`, `B24=0` |

There were no `WHERE` filters in the source query. These counts validate the
literal tests used inside the 17 `MAX(CASE ...)` branches; they do not license
code expansion, terminology translation, or replacing a zero with a related
code.

## Oracle checks

Read-only DuckDB checks against `/Users/nau025/warehouses/mimic4-demo.db`:

- Patient identifier set: FHIR 100/100 exact against `patients.subject_id`.
- Hospital Encounter identifier set: FHIR 275/275 exact against
  `admissions.hadm_id`.
- The FHIR age expression `YEAR(period.start) - YEAR(birthDate)` agreed with
  the canonical DuckDB age expression on 275/275 demo admissions.
- Condition tuple multiset `(hadm_id, system-derived icd_version, code)` agreed
  4,506/4,506 with `diagnoses_icd` after the hospital Encounter filter; FHIR
  version counts were ICD-9 2,193 and ICD-10 2,313, exactly matching DuckDB.
- Condition subject/reference consistency: 4,506/4,506 Condition patient keys
  equaled their linked hospital Encounter patient keys; all 4,506 Condition
  encounter and patient references resolved by opaque equality joins.

## Gaps and representability

### Anchor pair and age-derived branch

`Patient.birthDate` is present (100/100) but `patients.anchor_age` and
`patients.anchor_year` are not separate FHIR elements or extensions. The
authoritative ETL constructs birthDate from `MIN(transfers.intime) - anchor_age`,
not from the source anchor pair. Therefore the individual anchor fields and
the exact source age are **not representable**; the FHIR expression is the best
available derivation, not an inversion of the pair.

The local demo expression was exact for 275/275 admissions. The established
full-data age evidence is 460/431,231 age rows with a conflict caused by the
birthDate synthesis. For Charlson, `age_score` can differ only when the
reconstructed age crosses one of the source thresholds, so the affected
Charlson rows are bounded above by 460/431,231 (0.107%); the exact threshold-
crossing count was not available in the local demo oracle. `hadm_id`, row
inclusion, and diagnosis grouping remain representable. The loss can change
the clinically meaningful `age_score` and therefore the final index on that
bounded subset, so this is not an ancillary field; it is an inherited
age-dependency limitation for the equivalence judge. No resource-id operation
may be used to recover it.

### Diagnosis timing/status fields

`Condition.recordedDate`, all probed `onset[x]` variants, and clinical/
verification status were null for all 5,051 Conditions. Charlson has no
diagnosis-time predicate and does not use status, so these are **absent but
ancillary** for this concept; they do not affect row inclusion, natural key,
grouping, or any Charlson flag. No typed output column is needed for them.

### Condition stream merge

The merged Condition table is not itself a gap: the hospital/ED distinction is
recoverable by the surviving Condition-to-Encounter reference and the
Encounter identifier system. The hospital join is required; using the whole
Condition table would incorrectly add the 545 ED diagnosis rows.

## Notes and fragments

Mapping decisions were changed by these established `MIMIC_NOTES.md` entries:

- the identifier spine / opaque resource-reference id rule;
- hospital Encounter selection by identifier system rather than class;
- the empty Encounter diagnosis backbones, requiring Condition joins;
- the stale-raw-NDJSON warning, so only Delta was probed;
- the `Patient.birthDate` construction and age-derived limitation;
- the no-anchor-extension and extension-access rules;
- the offset-bearing FHIR datetime rule, leading to `TIMESTAMP_NTZ` for
  `Encounter.period.start`.

The `MIMIC_NOTES.md` statement that treats `Condition.code` as the exception
with proper ICD-9-CM/ICD-10-CM systems was **not adopted without probing**. The
authoritative current Delta probe instead observed the two proprietary systems
documented above; this finding was appended to
`MIMIC_NOTES.d/charlson.md`.

All existing fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` were read as
provisional leads: `README.md`, `arb.md`, `blood_differential.md`,
`cardiac_marker.md`, `chemistry.md`, `code_status.md`,
`complete_blood_count.md`, `coagulation.md`, `crrt.md`, `dobutamine.md`,
`dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`, `icp.md`,
`icustay_detail.md`, `icustay_times.md`, `invasive_line.md`, `kdigo_creatinine.md`,
`milrinone.md`, `neuroblock.md`, `norepinephrine.md`, `oxygen_delivery.md`,
`phenylephrine.md`, `rhythm.md`, `rrt.md`, `urine_output.md`,
`vasopressin.md`, `ventilator_setting.md`, `vitalsign.md`, and
`weight_durations.md`.
No provisional fragment was cited as evidence; only the Condition, Encounter,
Patient, and DuckDB probes above were used for this mapping.

## Carryover status

This file is the reusable `fhir-prober` carryover for `charlson`. It records
the required source-to-FHIR paths, exact observed coding systems, literal code
counts, cardinalities, types, oracle checks, and representability limits. The
next stage must author the ViewDefinition/SQL separately and must not parse or
regenerate any FHIR resource/reference id.
