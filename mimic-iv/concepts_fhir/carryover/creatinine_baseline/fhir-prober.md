# FHIR prober mapping: `creatinine_baseline` (attempt_0001)

**Scope:** mapping/probing only. No attempt ViewDefinition or `concept.sql` was
authored. The authoritative warehouse was
`/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded Pathling
9.6.0 on Spark 4.0.2.

## Read surface and source contract

I read `AGENTS.md`, the reusable source analysis
`carryover/creatinine_baseline/source-analyst.md` exactly, `LOOP_CONTRACT.md`,
curated `MIMIC_NOTES.md`, the canonical
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`,
the attempt source-analysis evidence, the full oracle manifest, the current
attempt state, and dependency analyses for `age` and `chemistry`.

I also read the provisional fragments `MIMIC_NOTES.d/chemistry.md`,
`MIMIC_NOTES.d/kdigo_creatinine.md`, `MIMIC_NOTES.d/charlson.md`,
`MIMIC_NOTES.d/complete_blood_count.md`, `MIMIC_NOTES.d/height.md`,
`MIMIC_NOTES.d/icustay_detail.md`, and `MIMIC_NOTES.d/README.md`. They were
treated as leads, not evidence; the claims used below were rechecked against
the Delta and/or upstream SQL. There is no age-named fragment. The age-specific
guidance was instead checked in curated `MIMIC_NOTES.md`, the age carryover
probe, `LOOP_CONTRACT.md`, and the completed age attempt evidence.

Source SQL and the source analysis establish seven output columns, one row per
adult `hadm_id`, keyed by `hadm_id`:

```text
hadm_id, gender, age, scr_min, ckd, mdrd_est, scr_baseline
```

The direct inputs are `mimiciv_derived.age`,
`mimiciv_hosp.patients.gender`, `mimiciv_derived.chemistry`, and
`mimiciv_hosp.diagnoses_icd`. `age` depends on hospital `admissions` and
patients; `chemistry` depends on labevents item `50912` for creatinine. The
full manifest target is `hadm_id INTEGER`, `gender VARCHAR`, `age BIGINT`,
`scr_min DOUBLE`, `ckd INTEGER`, `mdrd_est DOUBLE`, and `scr_baseline DOUBLE`,
with 431,231 rows and key `hadm_id`.

## Resource/table mapping

| Source relation or role | MIMIC-on-FHIR resource(s) | Mapping consequence |
|---|---|---|
| `mimiciv_derived.age` (`subject_id`, `hadm_id`, `age`, `admittime` lineage) | hospital `Encounter` + `Patient` | Select only the Encounter carrying the hospital identifier system; join Encounter to Patient by opaque FHIR reference key. Compute the served age approximation from `Encounter.period.start` and `Patient.birthDate`. |
| `mimiciv_hosp.patients` (`subject_id`, `gender`) | `Patient` | Patient identifier supplies the source subject value; `Patient.gender` is `female`/`male` and must be mapped to source `F`/`M` for the output and MDRD branch. |
| `mimiciv_derived.chemistry` (`hadm_id`, `creatinine`) | labevents-derived `Observation` + lab `Specimen` + hospital `Encounter` + `Patient` | Select Observation coding system `mimic-d-labitems` and code `50912`; Quantity value supplies numeric creatinine, Specimen identifier supplies specimen grouping, and Encounter supplies nullable hospital admission identity. For this consumer, group the eligible creatinine values by hospital `hadm_id` and take `MIN`. |
| `mimiciv_hosp.diagnoses_icd` (`hadm_id`, `icd_code`, `icd_version`) | `Condition` + referenced `Encounter` + `Patient` | Condition coding system carries ICD version in the served Delta. Conditions include ED and hospital streams, so retain only Conditions whose opaque Encounter reference resolves to an Encounter with the hospital identifier system. Filter exact system plus the source three-character code prefix. |

The `Observation`, `Patient`, `Encounter`, `Specimen`, and `Condition` resource
tables are distinct. Resource/reference keys are used only for equality joins;
they are opaque and must not be parsed, regenerated, hashed, enumerated, or
used as a side channel for source values.

## Canonical source-column to FHIRPath mapping

The aliases below deliberately distinguish opaque UUID/reference strings from
MIMIC identifier strings. Every Pathling/ViewDefinition alias shown as
`VARCHAR` remains a string until the derived SQL casts it to the manifest type.

### Hospital Encounter and Patient / age dependency

| Source input | FHIR resource | Canonical `{path, name}` | FHIR/materialized type | Required use |
|---|---|---|---|---|
| `age.subject_id` / admission patient identity | `Encounter` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `VARCHAR` opaque reference key | Equality join to `Patient.getResourceKey()`; never parse it. |
| `patients.subject_id` | `Patient` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `VARCHAR` identifier value | Cast only for a source-shaped `subject_id` if a helper output needs it; this concept does not emit `subject_id`. |
| Patient resource key | `Patient` | `{ "path": "getResourceKey()", "name": "patient_id" }` | `VARCHAR` opaque resource key | Equality join target for Encounter/Observation/Condition references. |
| `age.hadm_id` | hospital `Encounter` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `VARCHAR` identifier value | Filter `hadm_id_str IS NOT NULL`; final `CAST(hadm_id_str AS INTEGER)` is `hadm_id`. Do not use `getResourceKey()` for this output. |
| Encounter resource key | `Encounter` | `{ "path": "getResourceKey()", "name": "encounter_id" }` | `VARCHAR` opaque resource key | Equality join to Observation/Condition references and Patient-side encounter rows. |
| Encounter patient key | `Encounter` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `VARCHAR` opaque reference key | Equality join to Patient. |
| `age.admittime` | hospital `Encounter` | `{ "path": "period.start", "name": "period_start" }` | `VARCHAR` ISO-8601 string with offset | Cast with `CAST(period_start AS TIMESTAMP_NTZ)` before `YEAR`; do not offset-convert it. |
| `patients.gender` | `Patient` | `{ "path": "gender", "name": "gender_fhir" }` | `VARCHAR` | `female` maps to source `F`; `male` maps to source `M`. The final `gender` remains manifest `VARCHAR`. |
| `age.age` | Encounter + Patient | `{ "path": "period.start", "name": "period_start" }` and `{ "path": "birthDate", "name": "birth_date" }` | both `VARCHAR` | `YEAR(CAST(period_start AS TIMESTAMP_NTZ)) - YEAR(CAST(birth_date AS DATE))`; cast the result to `BIGINT` as `age`. This is a served-data approximation, not an exact recovery of the anchor pair. |

The hospital Encounter discriminator is the identifier system, not
`Encounter.class`: the Delta has 637 Encounter rows, of which 275 are hospital
admissions, 140 ICU stays, and 222 ED contacts. The hospital identifier value
is the source `hadm_id` string. Use the identifier value for the output and the
opaque Encounter key for resource joins.

### Chemistry creatinine Observation and its grouping spine

| Source input | FHIR resource | Canonical `{path, name}` | FHIR/materialized type | Required use |
|---|---|---|---|---|
| labevent resource key (not source `labevent_id` output) | `Observation` | `{ "path": "getResourceKey()", "name": "observation_id" }` | `VARCHAR` opaque resource key | Provenance/grouping only; it is not an invertible labevent id. |
| `labevents.subject_id` | `Observation` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `VARCHAR` opaque reference key | Equality join to Patient. |
| `labevents.hadm_id` | `Observation` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }` | nullable `VARCHAR` opaque reference key | LEFT join to Encounter; do not infer a missing admission from patient/time. |
| `labevents.specimen_id` | `Observation` | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_id" }` | `VARCHAR` opaque reference key | Equality join to lab Specimen. |
| `labevents.specimen_id` | lab `Specimen` | `{ "path": "getResourceKey()", "name": "specimen_id" }` | `VARCHAR` opaque resource key | Join target for Observation.specimen. |
| `labevents.specimen_id` | lab `Specimen` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", "name": "specimen_id_str" }` | `VARCHAR` identifier value | Cast to `INTEGER` only if the intermediate chemistry grouping needs source `specimen_id`. The baseline consumer ultimately groups the chemistry result by `hadm_id`. |
| chemistry `itemid = 50912` | `Observation.code.coding` | `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems' and code='50912')"`; `{ "path": "code", "name": "item_code" }` | `VARCHAR` code | Exact item discriminator; `CAST(item_code AS INTEGER)` is `50912`. |
| chemistry item code system | `Observation.code.coding` | `{ "path": "system", "name": "item_system" }` | `VARCHAR` URI | Must equal `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`. |
| item display | `Observation.code.coding` | `{ "path": "display", "name": "item_display" }` | `VARCHAR` | Informational only (`Creatinine` in the probe); do not filter by display. |
| `labevents.valuenum` | `Observation.valueQuantity` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | materialized `VARCHAR` alias; raw encoded Quantity value is decimal | Cast to `DOUBLE`; apply the source non-null/positive rules and the creatinine CASE bound `<= 150` when deriving chemistry `creatinine`. |
| `labevents.valueuom` | `Observation.valueQuantity` | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `VARCHAR` | Unit evidence only; chemistry baseline has no unit output. Demo target is `mg/dL`. |
| comparator metadata | `Observation.valueQuantity` | `{ "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" }` | nullable `VARCHAR` | Retain while checking the source `valuenum IS NOT NULL` limitation; the served data does not carry an explicit source-origin flag. |
| non-Quantity fallback | `Observation` | `{ "path": "(value).ofType(string)", "name": "value_string" }` | nullable `VARCHAR` | Do not use as numeric creatinine. It can hold source text/comments when no Quantity exists. |
| `labevents.charttime` | `Observation.effective[x]` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | materialized `VARCHAR` ISO string with offset | Cast to `TIMESTAMP_NTZ` only if the dependency needs chart time. This consumer does not use chemistry chart time for grouping or a window. |
| unused effective choice probe | `Observation.effective[x]` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` and `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `VARCHAR` | Verified empty for target `50912`; do not coalesce with the dateTime string. |
| unused effective choice probe | `Observation.effective[x]` | `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | `TIMESTAMP` | Verified empty for target `50912`; do not coalesce with the dateTime string. |

The quantity alias is string-like despite FHIR `Quantity.value` being decimal;
this is the established Pathling materialization behavior. The derived SQL
must cast it to `DOUBLE` before `MIN` or comparisons. The datetime alias is an
ISO string with an offset, but de-identified MIMIC timestamps are wall-clock
values; `TIMESTAMP_NTZ` preserves the displayed wall clock and avoids local
timezone conversion.

### CKD Condition and diagnosis coding

| Source input | FHIR resource | Canonical `{path, name}` | FHIR/materialized type | Required use |
|---|---|---|---|---|
| diagnosis resource key | `Condition` | `{ "path": "getResourceKey()", "name": "condition_id" }` | `VARCHAR` opaque resource key | Optional provenance/deduplication only. Never infer source `seq_num` or any code from it. |
| diagnosis patient relation | `Condition` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `VARCHAR` opaque reference key | Equality join to Patient if needed; not a source output here. |
| diagnosis admission relation | `Condition` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }` | `VARCHAR` opaque reference key | Equality join to Encounter, then retain only `identifier.system=.../encounter-hosp`; this is essential because Condition also contains ED diagnoses. |
| `diagnoses_icd.icd_code` | `Condition.code.coding` | `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9' or system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10')"`; `{ "path": "code", "name": "diagnosis_code" }` | `VARCHAR` | Apply the source exact three-character prefixes: `SUBSTR(diagnosis_code,1,3)='585'` only with ICD-9 system, and `SUBSTR(...,1,3)='N18'` only with ICD-10 system. |
| `diagnoses_icd.icd_version` | `Condition.code.coding` | `{ "path": "system", "name": "diagnosis_system" }` | `VARCHAR` URI | ICD-9 system means source version 9; ICD-10 system means source version 10. |
| diagnosis display | `Condition.code.coding` | `{ "path": "display", "name": "diagnosis_display" }` | `VARCHAR` | Informational only; never use display as the filter. |

The authoritative Delta uses these diagnosis systems:

```text
ICD-9:  http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9
ICD-10: http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10
```

An embedded Pathling `src.read('CodeSystem')` probe raised
`IllegalArgumentException: No data found for resource type: CodeSystem`, so
the system and code confirmation comes from the served Condition coding rows,
not a terminology resource.

This is a confirmed Delta result for this attempt and supersedes the
provisional standard-ICD lead in the curated/fragment read surface. Do not use
`meta.profile` to discriminate. The Condition profile is shared; the coding
system and exact code prefix, plus the hospital Encounter identifier filter,
are the discriminator.

## Served-data probe counts

### Resource cardinality and non-null ledger

The following are counts from ephemeral probe ViewDefinitions over the demo
Delta. `count(*)` is the total materialized row count and `count(field)` is the
non-null count.

| Probe/resource | Total | Key | Patient/ref | Admission/ref | Numeric/value | Effective |
|---|---:|---:|---:|---:|---:|---:|
| creatinine Observation, system + code `50912` | 3,003 | observation 3,003/3,003 | patient 3,003/3,003 | hospital Encounter 2,366/3,003 | Quantity value 3,003/3,003; unit 3,003/3,003; comparator 0/3,003; string 0/3,003 | dateTime 3,003/3,003; Period.start 0/3,003; Period.end 0/3,003; instant 0/3,003 |
| Patient | 100 | resource 100/100 | patient identifier 100/100 | — | gender 100/100 | birthDate 100/100 |
| Encounter (all streams) | 637 | resource 637/637 | subject 637/637 | hospital identifier 275/637 | — | period.start 637/637 |
| lab Specimen (all resources) | 12,458 | resource 12,458/12,458 | subject 12,458/12,458 | — | lab identifier 11,122/12,458 | — |
| Condition coding | 5,051 | condition 5,051/5,051 | subject 5,051/5,051 | encounter 5,051/5,051 | code/system/display 5,051/5,051 each | — |

The creatinine Observation coding fan-out is exactly
`3,003 codings / 3,003 distinct Observation resources = 1.000`. Condition
coding fan-out is also `5,051 / 5,051 = 1.000`. A constrained coding
`forEach` is still recommended so a future second coding cannot silently
multiply rows.

### Confirmed code set and system discriminator

The direct `creatinine_baseline` SQL has no direct item filter. Its
`chemistry` dependency names the exact item `50912`, so that inherited code is
confirmed here:

| Source filter | Served system + code | FHIR rows | Oracle raw rows | Oracle rows passing source numeric predicate |
|---|---|---:|---:|---:|
| chemistry creatinine item | `mimic-d-labitems` + `50912` | 3,003 | 3,003 | 3,003 (`valuenum IS NOT NULL`, positive; all are `<=150` in demo) |
| CKD ICD-9 prefix | `mimic-diagnosis-icd9` + code prefix `585` | 35 before stream filter; 33 after hospital Encounter filter | 33 | 33 |
| CKD ICD-10 prefix | `mimic-diagnosis-icd10` + code prefix `N18` | 45 before stream filter; 39 after hospital Encounter filter | 39 | 39 |

The two extra `585` and six extra `N18` Conditions are ED Conditions. The
source table `diagnoses_icd` is hospital-stream data, so the FHIR port must
join the Condition's opaque `encounter_id` to Encounter and filter the
hospital identifier system. The exact source-prefix/system rule is therefore
the discriminator; `meta.profile` is not.

The source CKD code detail also agrees after the hospital stream filter:

```text
ICD-9: 5853=16, 5855=1, 5856=2, 5859=14  (33 total)
ICD-10: N183=13, N184=6, N186=12, N189=8 (39 total)
```

## Oracle checks and exact demo agreement

All checks below used the read-only DuckDB demo oracle
`/Users/nau025/warehouses/mimic4-demo.db`; none parsed or reconstructed a FHIR
resource id.

### Creatinine input and joins

- The oracle has 3,003 `labevents` rows for item `50912` with non-null positive
  `valuenum`; all 3,003 are `<=150`, and 2,366 have non-null `hadm_id`.
- The FHIR target has exactly 3,003 matching `(subject_id, specimen_id,
  itemid, numeric value, unit)` multiplicities: 3,003/3,003 groups and rows
  agree. Opaque Observation → Patient and Observation → Specimen joins resolve
  3,003/3,003. Observation → hospital Encounter resolves 2,366/3,003,
  exactly matching the source non-null `hadm_id` count. Thus the missing
  Encounter references are not a creatinine gap in this demo; use a LEFT join
  and preserve NULL.
- Numeric values and units agree 3,003/3,003 (`mg/dL` in the target). Effective
  wall-clock values agree 3,002/3,003. The single mismatch is specimen
  `48555540`, source `2116-03-08 02:52:00` versus FHIR
  `2116-03-08 03:52:00`, the known upstream DST-gap normalization. This concept
  does not use chemistry chart time for grouping, ordering, or a time window,
  so that transformed field is ancillary here and does not change the demo
  chemistry minimum.
- The demo chemistry relation has 3,289 specimen rows and 3,003 non-null
  `creatinine` values over 250 admission groups. Reconstructing the target
  creatinine minimum from the FHIR Quantity values gives the same 250 groups;
  `scr_min` agrees 275/275 in the full baseline reconstruction (25 admissions
  are NULL on both sides).

### Patient, age, diagnosis, and final baseline reconstruction

- Patient identifier, birthDate, and gender are populated 100/100. FHIR
  gender values are `female` 43 and `male` 57; mapping them to source `F`/`M`
  agrees 100/100 with `mimiciv_hosp.patients.gender`.
- Hospital Encounter → Patient opaque joins and Patient identifier joins
  cover all 275 demo admissions. The FHIR expression
  `YEAR(CAST(period_start AS TIMESTAMP_NTZ)) - YEAR(CAST(birth_date AS DATE))`
  agrees with `mimiciv_derived.age.age` 275/275; source and FHIR adult filters
  both retain 275/275, with demo source ages 21–93.
- After the hospital Encounter filter, CKD flags agree with the oracle on all
  72 qualifying diagnosis rows / admissions (33 ICD-9 `585` and 39 ICD-10
  `N18`).
- A FHIR-only reconstruction using the opaque joins, mapped gender, FHIR age,
  creatinine minimum, CKD flag, and the canonical MDRD/CASE expressions
  produces 275 rows, matching the oracle 275 rows. Per output column:

```text
gender        275/275 exact
age           275/275 exact
scr_min       275/275 exact (25 NULL on both sides)
ckd           275/275 exact
mdrd_est      275/275 exact
scr_baseline  275/275 exact (4 NULL on both sides)
```

The final `hadm_id` equality join is also 275/275. The full manifest target
types still require `CAST(hadm_id_str AS INTEGER)`, a `BIGINT` age expression,
and `DOUBLE` numeric expressions; the FHIR aliases themselves remain strings
where noted above.

## Gaps, transformations, and essentiality bounds

### Patient birthDate / age dependency: approximable but not exact

`Patient` has no `anchor_age`, `anchor_year`, or `anchor_year_group` extension.
The upstream ETL writes `birthDate` from
`MIN(transfers.intime) - anchor_age`, not from the canonical anchor pair
`anchor_year - anchor_age` (`mimic-fhir/sql/fhir_patient.sql:15`). Therefore
the FHIR expression for `age` is the best available derivation but is not exact
for every full-data admission. The FHIR resource ids cannot be used to recover
the discarded anchor pair.

The bound already established by the full `age` attempt is 460 conflicting age
values out of 431,231 admissions (0.107%); the demo was 275/275 only because
the demo patients happen to align. For this concept, at most those 460 rows can
carry the inherited age discrepancy, and only rows taking the MDRD fallback
(`scr_min > 1.1` or NULL and no CKD) can have `mdrd_est`/`scr_baseline` changed
by it. The source adult filter is identifiable from the surviving FHIR age
expression; demo has no inclusion loss (275/275 adult), and the completed age
full run retained the same 431,231 rows. The CKD and measured-creatinine
discriminators survive, so a port must not replace the missing exact age with a
different heuristic or use a typed NULL for the age value itself. This is an
inherited, bounded representability divergence that can affect a clinically
meaningful MDRD output on the affected fallback rows; the eventual full
comparison/judge must assess it, and this prober neither accepts nor blocks the
concept.

### Labevents numeric-origin bit: potentially essential, not observed in demo

The source chemistry filter requires `labevents.valuenum IS NOT NULL`, but the
upstream labevents ETL can parse comparator text in `labevents.value` into a
FHIR Quantity when `valuenum` is NULL (`mimic-fhir/sql/fhir_observation_labevents.sql:27-47,123-136`).
FHIR does not retain an explicit source-valuenum-present flag. The target demo
item `50912` has Quantity value 3,003/3,003, comparator 0/3,003, and string
value 0/3,003, and the oracle has 3,003/3,003 non-null numeric values, so no
demo row is ambiguous. On full data, a comparator-bearing Quantity for `50912`
cannot be proven to pass the source `valuenum IS NOT NULL` predicate solely
from its value. This can alter inclusion and the admission `MIN`, so if such
rows occur the missing origin bit is potentially essential and the full run
must bound them; do not silently treat `valueString` as numeric or infer source
origin from an opaque id.

### Condition stream and diagnosis system: resolved by surviving discriminators

Condition contains both hospital and ED diagnosis streams, and its profile does
not separate them. The hospital stream is still exactly identifiable by the
opaque Condition → Encounter join plus Encounter's hospital identifier system.
The diagnosis version is identifiable by the served coding system, and the
exact source code prefixes remain in `Condition.code.coding.code`. This is
therefore derivable, not a representation gap, provided both discriminators
are applied. Omitting the Encounter stream filter would add 8 CKD rows in the
demo and change `ckd`/`scr_baseline` for affected admissions.

### Datetime transformation: ancillary for this concept

The labevents ETL's `TIMESTAMPTZ` cast irreversibly shifts a DST-gap wall time;
the target item has one such demo row. `creatinine_baseline` contains no
time-window, temporal ordering, or charttime grouping; its chemistry consumer
uses only `hadm_id` and `creatinine`. The loss therefore does not reach row
inclusion, grouping, or any output of this concept, although it must not be
"corrected" by parsing or reconstructing an Observation id.

## Curated-note entries that changed mapping decisions

- **MIMIC ids live in `identifier.value` as STRINGs**: use the hospital
  Encounter identifier for `hadm_id_str` and cast it to `INTEGER`; keep
  `getResourceKey()`/`getReferenceKey()` only for opaque equality joins.
- **Encounter has three identifier systems — class discriminates none**:
  filter the Encounter helper to `.../identifier/encounter-hosp`; do not use
  `Encounter.class`.
- **Observation.code.coding.code is the source itemid, verbatim** and
  **Observation subtype profile metadata is warehouse-version dependent**:
  use system + exact code `50912`, not `meta.profile` or display.
- **Quantity.value ViewDefinition aliases materialize as VARCHAR**: cast
  `quantity_value` to `DOUBLE` before the chemistry `MIN` and bounds.
- **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ**: preserve the
  de-identified wall clock and do not offset-convert `effective_datetime` or
  `period_start`.
- **Lab Observation encounter references are incomplete — join by patient and
  time**: for this concept the source-null coincidence was measured directly
  for creatinine (2,366/3,003 non-null on both sides), so use a LEFT join and
  preserve NULL rather than inventing admission ids.
- **Patient.birthDate is NOT `anchor_year - anchor_age`** and the
  **essential-source-loss policy**: compute the best served age expression,
  report the bounded inherited full-data divergence, and never recover anchor
  data from an opaque id. The age result is a potential MDRD-output divergence,
  not a reason for this prober to make a terminal decision.
- **Encounter diagnosis backbones are empty — join diagnoses from Condition**:
  CKD evidence comes from `Condition.code` plus its Encounter reference, not
  Encounter.reasonCode/diagnosis.

The curated Condition-system statement was not adopted as a served-data fact:
the authoritative Delta probe found the MIMIC diagnosis systems instead. That
verified correction is the one new section in this concept's fragment below.

## Notes-fragment action

I appended exactly one new section to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/creatinine_baseline.md`. It records the
Delta-confirmed proprietary ICD diagnosis systems and the fact that Condition
mixes hospital and ED streams, with counts from this concept's attempt_0001.
`MIMIC_NOTES.md` was not edited. The curated note saying Condition is the
standard-ICD exception was not used as a data assertion because the authoritative
Delta probe contradicted it; the new fragment is provisional and names the
recheck evidence.
