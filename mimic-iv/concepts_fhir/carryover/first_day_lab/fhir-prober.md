# FHIR probe and mapping: `first_day_lab`

**Attempt:** `attempt_0001`  
**Probed:** 2026-08-21  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB 1.5.5, read-only

No HTTP Pathling server and no raw NDJSON were used.  The Delta warehouse is
the authoritative served representation.  No ViewDefinition or concept SQL
was authored by this stage.

## Source contract and target shape

The source analysis is
`mimic-iv/concepts_fhir/carryover/first_day_lab/source-analyst.md` and the
canonical source is `mimic-iv/concepts/firstday/first_day_lab.sql`.  The
consumer has no raw `labevents` reference and no coded filter.  It has one raw
driving table and five completed derived dependencies:

| Source table / dependency boundary | Served/candidate resource or view | Role in this concept |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter` (`identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`) | One output row per ICU stay; supplies `stay_id`, `subject_id`, and the `intime` window boundary |
| `mimiciv_derived.complete_blood_count` | published dependency view `complete_blood_count` (ultimately labevents `Observation` + `Specimen`) | CBC values and `charttime` |
| `mimiciv_derived.chemistry` | published dependency view `chemistry` (ultimately labevents `Observation` + `Specimen`) | chemistry values and `charttime` |
| `mimiciv_derived.blood_differential` | published dependency view `blood_differential` (ultimately labevents `Observation` + `Specimen`) | differential values and `charttime` |
| `mimiciv_derived.coagulation` | published dependency view `coagulation` (ultimately labevents `Observation` + `Specimen`) | coagulation values and `charttime` |
| `mimiciv_derived.enzyme` | published dependency view `enzyme` (ultimately labevents `Observation` + `Specimen`) | enzyme/bilirubin values and `charttime` |

The source window is inclusive `[-6 hours, +1 day]` around ICU `intime`, and
the join is patient plus time only.  The FHIR implementation must preserve
the five dependency boundaries and use the published dependency views; it
must not rederive the dependencies from `Observation` resources or join them
by `specimen_key`, `encounter_key`, `stay_id`, `hadm_id`, or an opaque resource
id.

The full oracle manifest declares `key = ["stay_id"]`, 73,181 full rows, and
88 compared columns.  The port must additionally emit the FHIR join keys
`patient_key` and `icu_encounter_key` (both uncast `STRING` values) beside the
MIMIC identifiers.  The export layer strips the paired MIMIC identifiers from
the published derived shape, so the candidate result needs both forms even
though the comparator's 88-column manifest does not list the keys.

## Exact ViewDefinition projections for the direct source spine

These are the exact canonical `{path, name}` projections.  The filename labels
used by the eventual implementation should be `icu_encounter` and `patient`
and must equal each ViewDefinition's `name`.

### ICU Encounter view

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "icu_encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "period.start", "name": "intime" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
      "column": [
        { "path": "value", "name": "stay_id_str" },
        { "path": "system", "name": "stay_id_system" }
      ]
    }
  ]
}
```

`getResourceKey()` and `subject.getReferenceKey(Patient)` are opaque FHIR
identity strings.  `stay_id_str` is the FHIR `Identifier.value` string and is
the only source of the relational `stay_id`.  `intime` is FHIR `dateTime`,
materialized as an offset-bearing string; cast it directly to
`TIMESTAMP_NTZ` before the temporal join.  Do not use `Encounter.class` to
select ICU stays: the ICU stream is identifier-typed.

The restricted identifier `forEach` is intentional.  It prevents identifier
fan-out across the hospital/ICU/ED systems and has exactly one row per ICU
Encounter in the served data.  `forEachOrNull` is not needed because this
concept requests only the ICU identifier variant.

### Patient identifier helper

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "resource": "Patient",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "patient_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
      ]
    }
  ]
}
```

`subject_id_str` is the FHIR `Identifier.value` string.  The final SQL must
use `CAST(subject_id_str AS INTEGER)` for the manifest's `subject_id`; it must
not cast or parse `patient_key`.

There is no direct Observation, Specimen, or hospital Encounter ViewDefinition
needed by `first_day_lab`: all five lab streams are dependency boundaries.
Their upstream FHIR projections are recorded below so that the implementer
does not accidentally cross those boundaries.

## Dependency boundary and source-column mapping

All five upstream lab dependencies use the same FHIR source mapping:

| Upstream source value | Canonical upstream `{path, name}` | FHIR type | Published dependency type/use |
|---|---|---|---|
| labevents patient identity | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, resolved through Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` plus `string` identifier | `patient_key STRING`; `subject_id` is stripped from the published dependency and must be replaced by a key equality join |
| labevents `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` | dependency `charttime TIMESTAMP_NTZ`; consume directly in the window predicate |
| labevents numeric value | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal | dependency analyte `DOUBLE`, except blood-differential absolute counts which are `DECIMAL(38,4)` |
| lab item discriminator (upstream only) | inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')"`: `{ "path": "code", "name": "code" }` and `{ "path": "system", "name": "system" }` | `code` and `uri` | already applied by each completed dependency; do not add a second item filter here |
| lab specimen identity (upstream only) | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key" }`, resolved through `forEach: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab')"`, `{ "path": "value", "name": "specimen_id_str" }` | `Reference(Specimen)` plus `string` identifier | `specimen_key STRING` remains in the published dependency for provenance but is not used by this source SQL |
| lab admission identity (upstream only) | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`, resolved through hospital Encounter `forEach: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')"`, `{ "path": "value", "name": "hadm_id_str" }` | nullable `Reference(Encounter)` plus nullable `string` identifier | nullable `encounter_key STRING` remains in the published dependency but is not read by this concept |

The dependency views are registered in their **published** shapes, not in
their attempt shapes.  `strip_mimic_ids` removes `subject_id` when paired with
`patient_key`, `hadm_id` when paired with `encounter_key`, and `specimen_id`
when paired with `specimen_key`.  Therefore the first-day SQL must join each
dependency with:

```sql
LEFT JOIN complete_blood_count le
  ON le.patient_key = ie.patient_key
 AND le.charttime >= ie.intime - INTERVAL 6 HOURS
 AND le.charttime <= ie.intime + INTERVAL 1 DAY
```

with the dependency name and analyte list substituted.  An integer
`subject_id` join is not available at this boundary and must not be invented.
The lab `encounter_key` and `specimen_key` columns are not temporal or source
row discriminators for this concept; retaining them in the dependency shape
does not authorize using them in the join.

### Published dependency schemas, required fields, and population counts

The following counts are from the embedded Pathling preprocessing of the five
completed dependency attempts.  Each entry is `total/non-null`.  They are
counts over the published candidate temp views, not counts over a rederived
FHIR query.

| Dependency view | Published schema used by `first_day_lab` | Population counts |
|---|---|---|
| `complete_blood_count` (2,959 rows) | `charttime TIMESTAMP_NTZ`; `hematocrit`, `hemoglobin`, `platelet`, `wbc DOUBLE`; `patient_key STRING`; nullable `encounter_key STRING`; `specimen_key STRING` | `charttime 2959/2959`; `hematocrit 2908/2959`; `hemoglobin 2785/2959`; `platelet 2820/2959`; `wbc 2759/2959`; `patient_key 2959/2959`; `encounter_key 2336/2959`; `specimen_key 2959/2959` |
| `chemistry` (3,289 rows) | `charttime TIMESTAMP_NTZ`; `albumin`, `globulin`, `total_protein`, `aniongap`, `bicarbonate`, `bun`, `calcium`, `chloride`, `creatinine`, `glucose`, `sodium`, `potassium DOUBLE`; `patient_key STRING`; nullable `encounter_key STRING`; `specimen_key STRING` | `charttime 3289/3289`; `albumin 625/3289`; `globulin 163/3289`; `total_protein 181/3289`; `aniongap 2860/3289`; `bicarbonate 2863/3289`; `bun 2973/3289`; `calcium 2377/3289`; `chloride 2981/3289`; `creatinine 3003/3289`; `glucose 2711/3289`; `sodium 3007/3289`; `potassium 3019/3289`; `patient_key 3289/3289`; `encounter_key 2501/3289`; `specimen_key 3289/3289` |
| `blood_differential` (2,763 rows) | `charttime TIMESTAMP_NTZ`; `wbc`, `atypical_lymphocytes`, `bands`, `immature_granulocytes`, `metamyelocytes`, `nrbc DOUBLE`; `basophils_abs`, `eosinophils_abs`, `lymphocytes_abs`, `monocytes_abs`, `neutrophils_abs DECIMAL(38,4)`; `patient_key STRING`; nullable `encounter_key STRING`; `specimen_key STRING` | `charttime 2763/2763`; `wbc 2762/2763`; `basophils_abs 938/2763`; `eosinophils_abs 938/2763`; `lymphocytes_abs 941/2763`; `monocytes_abs 938/2763`; `neutrophils_abs 938/2763`; `atypical_lymphocytes 404/2763`; `bands 395/2763`; `immature_granulocytes 226/2763`; `metamyelocytes 397/2763`; `nrbc 115/2763`; `patient_key 2763/2763`; `encounter_key 2149/2763`; `specimen_key 2763/2763` |
| `coagulation` (1,630 rows) | `charttime TIMESTAMP_NTZ`; `d_dimer`, `fibrinogen`, `thrombin`, `inr`, `pt`, `ptt DOUBLE`; `patient_key STRING`; nullable `encounter_key STRING`; `specimen_key STRING` | `charttime 1630/1630`; `d_dimer 1/1630`; `fibrinogen 164/1630`; `thrombin 1/1630`; `inr 1464/1630`; `pt 1464/1630`; `ptt 1483/1630`; `patient_key 1630/1630`; `encounter_key 1418/1630`; `specimen_key 1630/1630` |
| `enzyme` (1,411 rows) | `charttime TIMESTAMP_NTZ`; `alt`, `alp`, `ast`, `amylase`, `bilirubin_total`, `bilirubin_direct`, `bilirubin_indirect`, `ck_cpk`, `ck_mb`, `ggt`, `ld_ldh DOUBLE`; `patient_key STRING`; nullable `encounter_key STRING`; `specimen_key STRING` | `charttime 1411/1411`; `alt 1159/1411`; `alp 1138/1411`; `ast 1165/1411`; `amylase 41/1411`; `bilirubin_total 1146/1411`; `bilirubin_direct 53/1411`; `bilirubin_indirect 44/1411`; `ck_cpk 200/1411`; `ck_mb 179/1411`; `ggt 4/1411`; `ld_ldh 663/1411`; `patient_key 1411/1411`; `encounter_key 1005/1411`; `specimen_key 1411/1411` |

The direct ICU and Patient helper population counts were:

```text
patient:       100 rows; patient_key 100/100; subject_id_str 100/100
icu_encounter: 140 rows; icu_encounter_key 140/140; patient_key 140/140;
               stay_id_str 140/140; stay_id_system 140/140;
               intime 140/140; outtime 140/140
```

The `outtime` projection was counted to check the Encounter period shape but
is not needed by this source SQL.

## Upstream code-system confirmation

`first_day_lab.sql` contains **no coded filter**: its target code set is empty,
and there is no target-side `forEach` over `code.coding`.  The item codes below
were nevertheless checked to verify the five dependency boundaries.  They are
informational upstream evidence only; the implementer must consume the
completed dependency views and must not re-filter these codes in
`first_day_lab`.

The served system was exactly
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`.  The union probe
projected `forEach: "code.coding.where(system='.../mimic-d-labitems' and
(exact code predicates))"` and found **71,457 coding rows over 71,457 distinct
Observation resources = 1.000 codings/resource**.  There was no coding fan-out,
and all 71,457 rows belonged to the lab system.  Per-dependency ratios were:

```text
complete_blood_count  25,087/25,087 = 1.000
chemistry             26,767/26,767 = 1.000
blood_differential    11,908/11,908 = 1.000
coagulation            4,630/4,630 = 1.000
enzyme                 5,825/5,825 = 1.000
```

Each ledger entry below is `code: FHIR coded / FHIR Quantity / oracle raw /
oracle valuenum`.  The FHIR coded and oracle raw counts agreed for every
literal; FHIR Quantity and oracle `valuenum IS NOT NULL` counts also agreed
for every literal in this demo.  All observed `Quantity.comparator` counts
were zero in the union probe.  The discriminator is always `system + exact
string code`, never `meta.profile`; the itemid is carried verbatim by the ETL.

```text
complete_blood_count:
  51221: 2913/2908/2913/2908   51222: 2787/2785/2787/2785
  51248: 2760/2748/2760/2748   51249: 2760/2748/2760/2748
  51250: 2760/2748/2760/2748   51265: 2827/2820/2827/2820
  51279: 2760/2748/2760/2748   51277: 2760/2747/2760/2747
  52159:    0/0/0/0             51301: 2760/2759/2760/2759

chemistry:
  50862: 625/625/625/625       50930: 163/163/163/163
  50976: 181/181/181/181       50868: 2860/2860/2860/2860
  50882: 2863/2863/2863/2863   51006: 2974/2973/2974/2973
  50893: 2377/2377/2377/2377   50902: 2981/2981/2981/2981
  50912: 3003/3003/3003/3003   50931: 2711/2711/2711/2711
  50983: 3007/3007/3007/3007   50971: 3022/3019/3022/3019

blood_differential:
  51146: 943/938/943/938       52069: 569/565/569/565
  51199: 0/0/0/0                51200: 943/939/943/939
  52073: 569/565/569/565       51244: 943/939/943/939
  51245: 16/16/16/16            51133: 569/565/569/565
  52769: 16/16/16/16             51253: 0/0/0/0
  51254: 943/939/943/939       52074: 569/565/569/565
  51256: 943/939/943/939       52075: 569/565/569/565
  51143: 404/404/404/404       51144: 395/395/395/395
  51218: 2/2/2/2                52135: 227/226/227/226
  51251: 397/397/397/397       51257: 115/115/115/115
  51300: 16/16/16/16            51301: 2760/2759/2760/2759
  51755: 0/0/0/0

coagulation:
  51196: 1/1/1/1                51214: 166/164/166/164
  51297: 1/1/1/1                51237: 1481/1464/1481/1464
  51274: 1481/1464/1481/1464   51275: 1500/1483/1500/1483

enzyme:
  50861: 1163/1159/1163/1159  50863: 1138/1138/1138/1138
  50878: 1165/1165/1165/1165  50867: 41/41/41/41
  50885: 1164/1146/1164/1146  50883: 53/53/53/53
  50884: 47/45/47/45           50910: 200/200/200/200
  50911: 187/179/187/179       50927: 4/4/4/4
  50954: 663/663/663/663
```

The dead literals (`52159`, `51199`, `51253`, `51755`) are upstream
dependency facts, not target filters.  The absence of a coded filter in
`first_day_lab` means no dead filter is introduced by this consumer.

## Final output schema and source-to-output trace

The final SQL must preserve the following 88 manifest columns in source order;
all aggregate values are nullable.  `MIN` and `MAX` are independent per
analyte, exactly as in the source SQL; do not select a single latest dependency
row.

```text
subject_id INTEGER, stay_id INTEGER,

hematocrit_min DOUBLE, hematocrit_max DOUBLE,
hemoglobin_min DOUBLE, hemoglobin_max DOUBLE,
platelets_min DOUBLE, platelets_max DOUBLE,
wbc_min DOUBLE, wbc_max DOUBLE,

albumin_min DOUBLE, albumin_max DOUBLE,
globulin_min DOUBLE, globulin_max DOUBLE,
total_protein_min DOUBLE, total_protein_max DOUBLE,
aniongap_min DOUBLE, aniongap_max DOUBLE,
bicarbonate_min DOUBLE, bicarbonate_max DOUBLE,
bun_min DOUBLE, bun_max DOUBLE,
calcium_min DOUBLE, calcium_max DOUBLE,
chloride_min DOUBLE, chloride_max DOUBLE,
creatinine_min DOUBLE, creatinine_max DOUBLE,
glucose_min DOUBLE, glucose_max DOUBLE,
sodium_min DOUBLE, sodium_max DOUBLE,
potassium_min DOUBLE, potassium_max DOUBLE,

abs_basophils_min DECIMAL(38,4), abs_basophils_max DECIMAL(38,4),
abs_eosinophils_min DECIMAL(38,4), abs_eosinophils_max DECIMAL(38,4),
abs_lymphocytes_min DECIMAL(38,4), abs_lymphocytes_max DECIMAL(38,4),
abs_monocytes_min DECIMAL(38,4), abs_monocytes_max DECIMAL(38,4),
abs_neutrophils_min DECIMAL(38,4), abs_neutrophils_max DECIMAL(38,4),
atyps_min DOUBLE, atyps_max DOUBLE,
bands_min DOUBLE, bands_max DOUBLE,
imm_granulocytes_min DOUBLE, imm_granulocytes_max DOUBLE,
metas_min DOUBLE, metas_max DOUBLE,
nrbc_min DOUBLE, nrbc_max DOUBLE,

d_dimer_min DOUBLE, d_dimer_max DOUBLE,
fibrinogen_min DOUBLE, fibrinogen_max DOUBLE,
thrombin_min DOUBLE, thrombin_max DOUBLE,
inr_min DOUBLE, inr_max DOUBLE,
pt_min DOUBLE, pt_max DOUBLE,
ptt_min DOUBLE, ptt_max DOUBLE,

alt_min DOUBLE, alt_max DOUBLE,
alp_min DOUBLE, alp_max DOUBLE,
ast_min DOUBLE, ast_max DOUBLE,
amylase_min DOUBLE, amylase_max DOUBLE,
bilirubin_total_min DOUBLE, bilirubin_total_max DOUBLE,
bilirubin_direct_min DOUBLE, bilirubin_direct_max DOUBLE,
bilirubin_indirect_min DOUBLE, bilirubin_indirect_max DOUBLE,
ck_cpk_min DOUBLE, ck_cpk_max DOUBLE,
ck_mb_min DOUBLE, ck_mb_max DOUBLE,
ggt_min DOUBLE, ggt_max DOUBLE,
ld_ldh_min DOUBLE, ld_ldh_max DOUBLE
```

The source-to-output trace is:

```text
complete_blood_count.hematocrit -> hematocrit_min / hematocrit_max
complete_blood_count.hemoglobin  -> hemoglobin_min  / hemoglobin_max
complete_blood_count.platelet    -> platelets_min  / platelets_max
complete_blood_count.wbc         -> wbc_min         / wbc_max

chemistry.albumin       -> albumin_min / albumin_max
chemistry.globulin      -> globulin_min / globulin_max
chemistry.total_protein -> total_protein_min / total_protein_max
chemistry.aniongap      -> aniongap_min / aniongap_max
chemistry.bicarbonate   -> bicarbonate_min / bicarbonate_max
chemistry.bun           -> bun_min / bun_max
chemistry.calcium       -> calcium_min / calcium_max
chemistry.chloride      -> chloride_min / chloride_max
chemistry.creatinine    -> creatinine_min / creatinine_max
chemistry.glucose       -> glucose_min / glucose_max
chemistry.sodium        -> sodium_min / sodium_max
chemistry.potassium     -> potassium_min / potassium_max

blood_differential.basophils_abs       -> abs_basophils_min / abs_basophils_max
blood_differential.eosinophils_abs     -> abs_eosinophils_min / abs_eosinophils_max
blood_differential.lymphocytes_abs     -> abs_lymphocytes_min / abs_lymphocytes_max
blood_differential.monocytes_abs       -> abs_monocytes_min / abs_monocytes_max
blood_differential.neutrophils_abs     -> abs_neutrophils_min / abs_neutrophils_max
blood_differential.atypical_lymphocytes -> atyps_min / atyps_max
blood_differential.bands               -> bands_min / bands_max
blood_differential.immature_granulocytes -> imm_granulocytes_min / imm_granulocytes_max
blood_differential.metamyelocytes      -> metas_min / metas_max
blood_differential.nrbc                -> nrbc_min / nrbc_max

coagulation.d_dimer    -> d_dimer_min / d_dimer_max
coagulation.fibrinogen -> fibrinogen_min / fibrinogen_max
coagulation.thrombin   -> thrombin_min / thrombin_max
coagulation.inr        -> inr_min / inr_max
coagulation.pt         -> pt_min / pt_max
coagulation.ptt        -> ptt_min / ptt_max

enzyme.alt              -> alt_min / alt_max
enzyme.alp              -> alp_min / alp_max
enzyme.ast              -> ast_min / ast_max
enzyme.amylase          -> amylase_min / amylase_max
enzyme.bilirubin_total  -> bilirubin_total_min / bilirubin_total_max
enzyme.bilirubin_direct  -> bilirubin_direct_min / bilirubin_direct_max
enzyme.bilirubin_indirect -> bilirubin_indirect_min / bilirubin_indirect_max
enzyme.ck_cpk            -> ck_cpk_min / ck_cpk_max
enzyme.ck_mb             -> ck_mb_min / ck_mb_max
enzyme.ggt               -> ggt_min / ggt_max
enzyme.ld_ldh            -> ld_ldh_min / ld_ldh_max
```

The two identity columns are mapped as follows:

| Source column | Canonical FHIR mapping | FHIR type | Final target type / check |
|---|---|---|---|
| `icustays.subject_id` | ICU Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` plus `string` identifier | `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; emit `patient_key STRING` alongside it |
| `icustays.stay_id` | ICU Encounter identifier `forEach` with `{ "path": "value", "name": "stay_id_str" }` and `{ "path": "system", "name": "stay_id_system" }`; ICU Encounter key `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | identifier `string` plus resource key `string` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; emit `icu_encounter_key STRING` alongside it |
| `icustays.intime` | `{ "path": "period.start", "name": "intime" }` | FHIR `dateTime`, materialized `STRING` | `TRY_CAST(intime AS TIMESTAMP_NTZ)` for the inclusive dependency windows; do not apply offset-aware conversion |
| each dependency `charttime` | upstream `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }`, published as dependency `charttime` | FHIR `dateTime` | published `TIMESTAMP_NTZ`; use directly in the window predicate |

The in-memory candidate query used exactly these published dependency shapes,
joined on `patient_key`, and reproduced the DuckDB source query for **140/140
demo ICU stays**.  The keyed sets, `subject_id`, `stay_id`, every one of the
86 aggregate values, and all nulls agreed after normalizing only the display
scale of equivalent Decimal values.  Candidate keys were non-null and unique
for `patient_key` 140/140 (100 distinct patients) and
`icu_encounter_key` 140/140 (140 distinct ICU stays).  A direct FHIR-to-DuckDB
check for the ICU spine was also exact: stay id 140/140, subject id 140/140,
and `period.start`/`intime` 140/140.

## Gaps and representability

* **No identifier gap in the demo.** ICU Encounter identifier values recover
  `stay_id` exactly, Patient identifier values recover `subject_id` exactly,
  and the FHIR resource keys supply the required equality-join spine.  Resource
  ids are opaque and were not parsed or reconstructed.
* **No dependency-value gap in the demo.** The five published dependency
  schemas contain every field read by the source SQL, with typed nullable
  values.  A missing analyte is an ordinary aggregate NULL on the rows whose
  dependency has no value; it is not a missing row and must remain a typed
  NULL.  The 140-row in-memory keyed comparison was exact for all 88 manifest
  values.
* **Known datetime transformation loss:** `icustays.intime` is written by
  the ICU Encounter ETL through `CAST(... AS TIMESTAMPTZ)` before
  `Encounter.period.start`, and upstream labevents `charttime` is similarly
  normalized before `Observation.effectiveDateTime`. A nonexistent New York
  spring-forward 02:xx wall time can therefore be served as 03:xx; no FHIR
  element or opaque id can recover the original. This affects only rows whose
  source time falls in that DST gap. In this authoritative demo, the direct
  ICU `intime` check reached 0/140 such divergences and the complete target
  output check was 140/140 exact. On full data the potential propagation is
  essential in the ordinary sense because `intime` and dependency `charttime`
  control row inclusion in the inclusive temporal join and hence every
  affected min/max. The established MIMIC-on-FHIR ETL transformation is the
  documented upstream DST exception, not a permissible id-based derivation;
  any full-data divergence must be bounded and sent to the comparator/judge,
  not silently corrected by subtracting an hour or used as an early block.
* **No `hadm_id` gap is relevant to this consumer.** The source output and all
  five source joins use `subject_id`/patient identity and time only. The
  dependency `encounter_key`/`hadm_id` information is not read and no
  hospital Encounter view should be introduced just to recover it.
* **No terminology gap.** There is no target coded filter, and upstream
  itemids are carried verbatim in the proprietary lab coding system. No LOINC
  translation is involved.

## Notes and provisional fragments

Curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md` entries that changed this
mapping decision were:

* Delta tables are authoritative over stale NDJSON.
* MIMIC identifiers are string-valued `identifier.value`; resource/reference
  keys are UUID-like opaque strings and paired output keys are required.
* ICU/hospital/ED Encounter streams are separated by identifier system, not
  `Encounter.class`; ICU `stay_id` is the ICU identifier value.
* Itemid-derived lab Observation codes are verbatim and must use system plus
  exact string code, never `meta.profile` or an inferred LOINC mapping.
* Lab Observation specimens preserve the source specimen identifier, while
  lab Observation Encounter references are incomplete and must be left-sided
  when upstream dependencies are built.
* Lab `valueString` can be a comments fallback and Quantity values can be
  synthesized from comparator text; therefore this concept consumes completed
  dependency outputs rather than treating every served Quantity as relational
  `valuenum`.
* Quantity aliases are string-like upstream and datetime choices require
  direct `TIMESTAMP_NTZ` handling; the target published dependency `charttime`
  is already a native `TIMESTAMP_NTZ`.
* The labevents and Encounter DST-gap normalization is not recoverable from
  FHIR and can propagate through temporal windows.

I read these provisional fragments and treated each as a lead, not as
established evidence: `MIMIC_NOTES.d/README.md`,
`MIMIC_NOTES.d/first_day_bg.md`, `MIMIC_NOTES.d/complete_blood_count.md`,
`MIMIC_NOTES.d/chemistry.md`, `MIMIC_NOTES.d/blood_differential.md`, and
`MIMIC_NOTES.d/coagulation.md`.  I also confirmed that
`MIMIC_NOTES.d/enzyme.md` did not exist.  The comparator-text Quantity leads
were checked against the union probe: all target dependency codes had
`quantity_comparator 0`, and FHIR Quantity counts matched source non-null
`valuenum` counts.  The datetime-coercion leads were checked by projecting
dateTime, Period.start, and instant: the union had 71,457/71,457 dateTime
values and 0/71,457 for both alternate variants, and the published dependency
charttime columns were native `TIMESTAMP_NTZ`.  The lab Observation/Specimen
and incomplete Encounter leads were checked: the union had specimen references
on 71,457/71,457 rows, while Encounter references were present on 53,409/71,457;
the dependency outputs retained all rows and their nullable encounter keys.
The exact `first_day_bg` full-data specimen `44663261` was not present in the
demo oracle (0 matching rows), so that fragment's six-row full-data example
was not independently reproduced here; the underlying DST mechanism remains
the curated, dataset-wide note and was not treated as a new finding.

No new dataset-wide quirk was found.  Therefore nothing was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_lab.md`, and
`MIMIC_NOTES.md` was not edited.

This reusable mapping is the carryover artifact at:

`mimic-iv/concepts_fhir/carryover/first_day_lab/fhir-prober.md`
