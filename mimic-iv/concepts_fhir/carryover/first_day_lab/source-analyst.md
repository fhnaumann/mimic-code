# Source analysis: `first_day_lab`

## Source identity and DAG position

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_lab.sql`
- DAG stem: `first_day_lab`
- DAG path: `firstday/first_day_lab.sql`
- DAG SHA-256: `bf7b2828579565b923b9c132a3e0c3ec66ee61abf69b0f1c27b034039e72a0cf`
- DAG level: 1
- DAG dependencies: `blood_differential`, `chemistry`, `coagulation`,
  `complete_blood_count`, and `enzyme`
- The candidate-side dependency names after preprocessing are the same
  unqualified stems. This consumer must read those dependency views rather than
  rederive their values from FHIR resources.

## Table references

The project prefix in the canonical SQL is `physionet-data`; the MIMIC schema
and table references are:

| SQL occurrence | Join type | Schema | Table | Alias | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `cbc` | driving table | `mimiciv_icu` | `icustays` | `ie` | ICU stays and their `subject_id`, `stay_id`, and `intime` |
| `LEFT JOIN \`physionet-data.mimiciv_derived.complete_blood_count\` le` | LEFT | `mimiciv_derived` | `complete_blood_count` | `le` | CBC analytes and lab `charttime` |
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `chem` | driving table | `mimiciv_icu` | `icustays` | `ie` | Same ICU-stay spine |
| `LEFT JOIN \`physionet-data.mimiciv_derived.chemistry\` le` | LEFT | `mimiciv_derived` | `chemistry` | `le` | Chemistry analytes and lab `charttime` |
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `diff` | driving table | `mimiciv_icu` | `icustays` | `ie` | Same ICU-stay spine |
| `LEFT JOIN \`physionet-data.mimiciv_derived.blood_differential\` le` | LEFT | `mimiciv_derived` | `blood_differential` | `le` | Differential analytes and lab `charttime` |
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `coag` | driving table | `mimiciv_icu` | `icustays` | `ie` | Same ICU-stay spine |
| `LEFT JOIN \`physionet-data.mimiciv_derived.coagulation\` le` | LEFT | `mimiciv_derived` | `coagulation` | `le` | Coagulation analytes and lab `charttime` |
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `enz` | driving table | `mimiciv_icu` | `icustays` | `ie` | Same ICU-stay spine |
| `LEFT JOIN \`physionet-data.mimiciv_derived.enzyme\` le` | LEFT | `mimiciv_derived` | `enzyme` | `le` | Enzyme/bilirubin analytes and lab `charttime` |
| Final `FROM \`physionet-data.mimiciv_icu.icustays\` ie` | driving table | `mimiciv_icu` | `icustays` | `ie` | Final one-row-per-stay output spine |
| Final `LEFT JOIN cbc`, `chem`, `diff`, `coag`, `enz` | LEFT | CTEs | `cbc`, `chem`, `diff`, `coag`, `enz` | — | Attach each aggregate branch by `stay_id` |

There are no `mimiciv_hosp` table references and no raw labevents table
references in this SQL. The only raw-schema table is `mimiciv_icu.icustays`;
all five laboratory inputs are `mimiciv_derived` dependencies.

## Join predicates and temporal filters

Each of the five dependency joins has the same inclusive predicate, with the
dependency table named below substituted for `le`:

```sql
ON le.subject_id = ie.subject_id
    AND le.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
    AND le.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

This is a LEFT JOIN, so every `icustays` row remains in each CTE even when no
dependency row matches. The accepted window is from six hours before
`ie.intime` through one day after `ie.intime`, inclusive: `[-6 hours, +1 day]`.
The join uses patient identity plus time only; it does not join on `stay_id`,
`hadm_id`, `outtime`, or any ICU location field. There is no additional
restriction to the ICU stay interval.

The final joins are all LEFT joins and are exactly:

```sql
ie.stay_id = cbc.stay_id
ie.stay_id = chem.stay_id
ie.stay_id = diff.stay_id
ie.stay_id = coag.stay_id
ie.stay_id = enz.stay_id
```

There is no `WHERE` clause anywhere in the query. Consequently there are no
WHERE predicates, value-range constraints, exclusions, or time filters beyond
the five `ON`-clause windows above.

## Dependency columns read by this consumer

These are the exact columns read from each `mimiciv_derived` table. The
dependency outputs are the boundary for this concept; the implementer should
not reconstruct them from FHIR resources or add upstream item filtering here.

| Dependency table / candidate stem | Exact consumer columns | CTE/output branch |
|---|---|---|
| `mimiciv_derived.complete_blood_count` / `complete_blood_count` | `subject_id`, `charttime`, `hematocrit`, `hemoglobin`, `platelet`, `wbc` | `cbc` → hematocrit, hemoglobin, platelets, and WBC min/max |
| `mimiciv_derived.chemistry` / `chemistry` | `subject_id`, `charttime`, `albumin`, `globulin`, `total_protein`, `aniongap`, `bicarbonate`, `bun`, `calcium`, `chloride`, `creatinine`, `glucose`, `sodium`, `potassium` | `chem` → chemistry min/max |
| `mimiciv_derived.blood_differential` / `blood_differential` | `subject_id`, `charttime`, `basophils_abs`, `eosinophils_abs`, `lymphocytes_abs`, `monocytes_abs`, `neutrophils_abs`, `atypical_lymphocytes`, `bands`, `immature_granulocytes`, `metamyelocytes`, `nrbc` | `diff` → differential min/max |
| `mimiciv_derived.coagulation` / `coagulation` | `subject_id`, `charttime`, `d_dimer`, `fibrinogen`, `thrombin`, `inr`, `pt`, `ptt` | `coag` → coagulation min/max |
| `mimiciv_derived.enzyme` / `enzyme` | `subject_id`, `charttime`, `alt`, `alp`, `ast`, `amylase`, `bilirubin_total`, `bilirubin_direct`, `bilirubin_indirect`, `ck_cpk`, `ck_mb`, `ggt`, `ld_ldh` | `enz` → enzyme/bilirubin min/max |

No other dependency column is referenced. In particular, this consumer does
not read any dependency `itemid`, `hadm_id`, lab label, unit, specimen id, or
source-row identifier.

## Column list and inferred types

The SQL has no explicit casts. Inferred source types are:

- `mimiciv_icu.icustays.subject_id` and `stay_id`: integer-valued MIMIC
  identifiers.
- `mimiciv_icu.icustays.intime` and every dependency `charttime`: datetime /
  timestamp values (the SQL uses BigQuery `DATETIME_SUB` and `DATETIME_ADD`).
- Every analyte listed in the dependency table above: nullable numeric values;
  `MIN` and `MAX` preserve the dependency's numeric type and the LEFT JOIN makes
  the aggregate outputs nullable. No numeric value is rounded, cast, or
  otherwise transformed by this query.

The raw columns referenced by the query are therefore:

```text
mimiciv_icu.icustays:
  subject_id, stay_id, intime

mimiciv_derived.complete_blood_count:
  subject_id, charttime, hematocrit, hemoglobin, platelet, wbc

mimiciv_derived.chemistry:
  subject_id, charttime, albumin, globulin, total_protein, aniongap,
  bicarbonate, bun, calcium, chloride, creatinine, glucose, sodium, potassium

mimiciv_derived.blood_differential:
  subject_id, charttime, basophils_abs, eosinophils_abs, lymphocytes_abs,
  monocytes_abs, neutrophils_abs, atypical_lymphocytes, bands,
  immature_granulocytes, metamyelocytes, nrbc

mimiciv_derived.coagulation:
  subject_id, charttime, d_dimer, fibrinogen, thrombin, inr, pt, ptt

mimiciv_derived.enzyme:
  subject_id, charttime, alt, alp, ast, amylase, bilirubin_total,
  bilirubin_direct, bilirubin_indirect, ck_cpk, ck_mb, ggt, ld_ldh
```

### Intermediate CTE schemas

Each CTE has one `stay_id` plus the nullable numeric aggregate aliases shown
below. The CTEs do not select `subject_id`.

- `cbc(stay_id, hematocrit_min, hematocrit_max, hemoglobin_min,
  hemoglobin_max, platelets_min, platelets_max, wbc_min, wbc_max)`
- `chem(stay_id, albumin_min, albumin_max, globulin_min, globulin_max,
  total_protein_min, total_protein_max, aniongap_min, aniongap_max,
  bicarbonate_min, bicarbonate_max, bun_min, bun_max, calcium_min,
  calcium_max, chloride_min, chloride_max, creatinine_min, creatinine_max,
  glucose_min, glucose_max, sodium_min, sodium_max, potassium_min,
  potassium_max)`
- `diff(stay_id, abs_basophils_min, abs_basophils_max, abs_eosinophils_min,
  abs_eosinophils_max, abs_lymphocytes_min, abs_lymphocytes_max,
  abs_monocytes_min, abs_monocytes_max, abs_neutrophils_min,
  abs_neutrophils_max, atyps_min, atyps_max, bands_min, bands_max,
  imm_granulocytes_min, imm_granulocytes_max, metas_min, metas_max,
  nrbc_min, nrbc_max)`
- `coag(stay_id, d_dimer_min, d_dimer_max, fibrinogen_min, fibrinogen_max,
  thrombin_min, thrombin_max, inr_min, inr_max, pt_min, pt_max, ptt_min,
  ptt_max)`
- `enz(stay_id, alt_min, alt_max, alp_min, alp_max, ast_min, ast_max,
  amylase_min, amylase_max, bilirubin_total_min, bilirubin_total_max,
  bilirubin_direct_min, bilirubin_direct_max, bilirubin_indirect_min,
  bilirubin_indirect_max, ck_cpk_min, ck_cpk_max, ck_mb_min, ck_mb_max,
  ggt_min, ggt_max, ld_ldh_min, ld_ldh_max)`

### Final output schema, in SQL order

The final result has 88 columns: two integer-valued identifiers followed by 86
nullable numeric min/max outputs.

```text
subject_id, stay_id,
hematocrit_min, hematocrit_max,
hemoglobin_min, hemoglobin_max,
platelets_min, platelets_max,
wbc_min, wbc_max,
albumin_min, albumin_max,
globulin_min, globulin_max,
total_protein_min, total_protein_max,
aniongap_min, aniongap_max,
bicarbonate_min, bicarbonate_max,
bun_min, bun_max,
calcium_min, calcium_max,
chloride_min, chloride_max,
creatinine_min, creatinine_max,
glucose_min, glucose_max,
sodium_min, sodium_max,
potassium_min, potassium_max,
abs_basophils_min, abs_basophils_max,
abs_eosinophils_min, abs_eosinophils_max,
abs_lymphocytes_min, abs_lymphocytes_max,
abs_monocytes_min, abs_monocytes_max,
abs_neutrophils_min, abs_neutrophils_max,
atyps_min, atyps_max,
bands_min, bands_max,
imm_granulocytes_min, imm_granulocytes_max,
metas_min, metas_max,
nrbc_min, nrbc_max,
d_dimer_min, d_dimer_max,
fibrinogen_min, fibrinogen_max,
thrombin_min, thrombin_max,
inr_min, inr_max,
pt_min, pt_max,
ptt_min, ptt_max,
alt_min, alt_max,
alp_min, alp_max,
ast_min, ast_max,
amylase_min, amylase_max,
bilirubin_total_min, bilirubin_total_max,
bilirubin_direct_min, bilirubin_direct_max,
bilirubin_indirect_min, bilirubin_indirect_max,
ck_cpk_min, ck_cpk_max,
ck_mb_min, ck_mb_max,
ggt_min, ggt_max,
ld_ldh_min, ld_ldh_max
```

## Filters and literal code specification

There are **no coded filters** in this canonical SQL. The literal code set is
empty: no `itemid`, `icd_code`, `icd_version`, LOINC, code system, or other
coded literal is named. Therefore there is no source table or output CTE to
which a code set feeds, and no dead coded filter to report. The dependency
tables are selected by their derived-table names, not by a code predicate in
this consumer.

There are also no `WHERE` predicates, no value constraints, and no code
exclusions. The only inclusion predicates are the five repeated
subject-and-time predicates in the LEFT JOIN `ON` clauses documented above.

## Aggregations and grain

Each of `cbc`, `chem`, `diff`, `coag`, and `enz` has:

```sql
GROUP BY ie.stay_id
```

and applies `MIN` and `MAX` independently to every analyte column selected in
that branch. There are no window functions, no `ARRAY_AGG`, no `COUNT`, no
`DISTINCT`, and no final aggregation. The final query only joins the five
one-row-per-stay CTEs back to `icustays`.

The source natural grain is one output row per `mimiciv_icu.icustays.stay_id`,
with `subject_id` identifying the patient for that ICU stay. The final
`icustays` driving table preserves the stay even when all five branches have no
matching lab rows; in that case the aggregate columns are NULL. For a matched
branch, SQL `MIN`/`MAX` ignore NULL analyte values, and remain NULL if no
non-NULL value contributes.

## Semantically essential inputs

These inputs can change row inclusion, the natural key, grouping, temporal
membership, or a clinically meaningful output:

| Input | What it controls | Affected result |
|---|---|---|
| `icustays.stay_id` | The CTE `GROUP BY` key, the final join key, and the output identity/grain | Every output row and its `stay_id`; all aggregate columns are attached to this key |
| `icustays.subject_id` | Patient equality in all five dependency joins and the final patient identifier | Whether dependency rows enter each branch; final `subject_id` |
| `icustays.intime` | Both boundaries of all five inclusive temporal windows | Which dependency rows contribute to every corresponding min/max pair |
| Each dependency `subject_id` | Patient equality against the ICU stay | Inclusion of that dependency row in its branch and therefore its branch's aggregates |
| Each dependency `charttime` | The `-6 hour` / `+1 day` window test | Inclusion of that dependency row and every min/max output in the corresponding branch |
| Each dependency analyte value | The numeric value passed to the branch's `MIN` and `MAX` | The matching output pair: e.g. `hematocrit` → `hematocrit_min/max`, `bilirubin_direct` → `bilirubin_direct_min/max` |
| Dependency relation identity (`complete_blood_count`, `chemistry`, `blood_differential`, `coagulation`, `enzyme`) | Which CTE branch and analyte family a row belongs to | The corresponding named output group; there is no row-level discriminator or itemid filter in this consumer |

The analyte-to-output trace is exact and one-to-one within each branch (each
source value feeds the two extrema aliases shown):

- `cbc`: `hematocrit` → `hematocrit_min/max`; `hemoglobin` →
  `hemoglobin_min/max`; `platelet` → `platelets_min/max`; `wbc` →
  `wbc_min/max`.
- `chem`: `albumin` → `albumin_min/max`; `globulin` → `globulin_min/max`;
  `total_protein` → `total_protein_min/max`; `aniongap` →
  `aniongap_min/max`; `bicarbonate` → `bicarbonate_min/max`; `bun` →
  `bun_min/max`; `calcium` → `calcium_min/max`; `chloride` →
  `chloride_min/max`; `creatinine` → `creatinine_min/max`; `glucose` →
  `glucose_min/max`; `sodium` → `sodium_min/max`; `potassium` →
  `potassium_min/max`.
- `diff`: `basophils_abs` → `abs_basophils_min/max`; `eosinophils_abs` →
  `abs_eosinophils_min/max`; `lymphocytes_abs` →
  `abs_lymphocytes_min/max`; `monocytes_abs` → `abs_monocytes_min/max`;
  `neutrophils_abs` → `abs_neutrophils_min/max`; `atypical_lymphocytes` →
  `atyps_min/max`; `bands` → `bands_min/max`; `immature_granulocytes` →
  `imm_granulocytes_min/max`; `metamyelocytes` → `metas_min/max`; `nrbc` →
  `nrbc_min/max`.
- `coag`: `d_dimer` → `d_dimer_min/max`; `fibrinogen` →
  `fibrinogen_min/max`; `thrombin` → `thrombin_min/max`; `inr` →
  `inr_min/max`; `pt` → `pt_min/max`; `ptt` → `ptt_min/max`.
- `enz`: `alt` → `alt_min/max`; `alp` → `alp_min/max`; `ast` → `ast_min/max`;
  `amylase` → `amylase_min/max`; `bilirubin_total` →
  `bilirubin_total_min/max`; `bilirubin_direct` →
  `bilirubin_direct_min/max`; `bilirubin_indirect` →
  `bilirubin_indirect_min/max`; `ck_cpk` → `ck_cpk_min/max`; `ck_mb` →
  `ck_mb_min/max`; `ggt` → `ggt_min/max`; `ld_ldh` → `ld_ldh_min/max`.

The SQL has no carry-forward logic. `charttime` is essential only as a temporal
join discriminator, not as a window-order or carry-forward value. No missing
source discriminator is introduced by this query beyond the upstream
dependency boundaries.

## Notes and dataset-wide quirks

The authoritative `MIMIC_NOTES.md` records a dataset-wide labevents
`TIMESTAMPTZ`/DST normalization quirk: FHIR lab effective times can be shifted
by one hour for nonexistent spring-forward wall times, and dependent first-day
time-window aggregates can consequently change inclusion or extrema. That is
directly relevant because this SQL consumes dependency `charttime` values and
uses inclusive time windows and min/max aggregation. It is already present in
the curated notes; this source-only analysis found no new dataset-wide quirk to
append to `MIMIC_NOTES.d/first_day_lab.md`.

Relevant provisional fragments read were `blood_differential.md`,
`chemistry.md`, `coagulation.md`, `complete_blood_count.md`, and
`first_day_bg.md`; `MIMIC_NOTES.d/enzyme.md` does not exist. Those sibling
fragments were treated as leads under the loop contract and are not cited as
evidence for these source-SQL facts.

## Evidence boundary

This is a source-SQL analysis only. It does not author a ViewDefinition or
`concept.sql`, does not run SQL, and makes no clinical or representability
decision. The implementer must preserve the five dependency boundaries, exact
column names, inclusive `[-6 hours, +1 day]` windows, LEFT-join behavior,
stay-level grain, and all listed aggregate output columns.
