# Source analysis: `creatinine_baseline`

## Source and DAG identity

- **Concept stem:** `creatinine_baseline`
- **Canonical SQL:** `mimic-iv/concepts/measurement/creatinine_baseline.sql`
- **DAG path:** `measurement/creatinine_baseline.sql`
- **DAG level:** `1`
- **DAG SHA-256:** `3ca2e029f27025df7c96b5364e4bc7acf7165510340160f9f32406a3e838cdda`
- **DAG dependencies:** `age`, `chemistry`
- **DAG dependents:** none recorded

The canonical query has three CTEs (`p`, `lab`, and `ckd`) followed by a final
select. This analysis describes the source SQL only; no SQL was executed and no
FHIR ViewDefinition or candidate SQL was authored.

## 1. Table and relation references

The `physionet-data` prefix in the quoted names is a project/catalog qualifier;
the MIMIC schema is the component after it.

### Physical tables

| SQL location | Schema | Table | Alias | Role |
|---|---|---|---|---|
| `p` CTE `FROM` | `mimiciv_derived` | `age` | `ag` | One age row per hospital admission; provides admission identity and age. |
| `p` CTE `LEFT JOIN` | `mimiciv_hosp` | `patients` | `p` | Provides patient gender for the MDRD estimate. |
| `lab` CTE `FROM` | `mimiciv_derived` | `chemistry` | none | Provides admission-linked chemistry creatinine values. |
| `ckd` CTE `FROM` | `mimiciv_hosp` | `diagnoses_icd` | none | Supplies CKD diagnosis evidence. |

No `mimiciv_icu` table is referenced.

### CTE relation references in the final query

| SQL clause | Relation | Type | Condition |
|---|---|---|---|
| final `FROM` | CTE `p` | base CTE relation | none |
| final `LEFT JOIN` | CTE `lab` | left join | `p.hadm_id = lab.hadm_id` |
| final `LEFT JOIN` | CTE `ckd` | left join | `p.hadm_id = ckd.hadm_id` |

## 2. Columns used and inferred types

Types below are inferred from the canonical source context and the MIMIC DDL;
the manifest confirms the final DuckDB-compatible types.

### Direct dependency/table columns referenced by this SQL

| Relation | Column | Inferred type | Uses |
|---|---|---|---|
| `mimiciv_derived.age` `ag` | `subject_id` | `INTEGER` | Join key to `patients`; carried in `p` but not emitted. |
| `mimiciv_derived.age` `ag` | `hadm_id` | `INTEGER` | Admission identity; joins both downstream CTEs and becomes the final key/output. |
| `mimiciv_derived.age` `ag` | `age` | `BIGINT`/integer-valued | Adult filter, MDRD exponent, and final `age` output. |
| `mimiciv_hosp.patients` `p` | `subject_id` | `INTEGER` | Equality join to `ag.subject_id`. |
| `mimiciv_hosp.patients` `p` | `gender` | `CHAR(1)` at source; final manifest type `VARCHAR` | Final `gender` output and female/non-female MDRD branch. |
| `mimiciv_derived.chemistry` | `hadm_id` | `INTEGER` | Grouping key in `lab` and join to `p`. |
| `mimiciv_derived.chemistry` | `creatinine` | `DOUBLE PRECISION`/`DOUBLE` | `MIN` aggregation into `scr_min`. |
| `mimiciv_hosp.diagnoses_icd` | `hadm_id` | `INTEGER` | Grouping key in `ckd` and join to `p`. |
| `mimiciv_hosp.diagnoses_icd` | `icd_code` | `CHAR(7)` | Three-character CKD prefix predicates. |
| `mimiciv_hosp.diagnoses_icd` | `icd_version` | `SMALLINT` | ICD-9 versus ICD-10 discriminator paired with `icd_code`. |

No other columns from these physical relations are selected or referenced by
`creatinine_baseline.sql`.

### Intermediate CTE columns

#### `p`

| Column | Expression | Inferred type | Notes |
|---|---|---|---|
| `subject_id` | `ag.subject_id` | `INTEGER` | Retained inside `p`; not in final output. |
| `hadm_id` | `ag.hadm_id` | `INTEGER` | Admission identity. |
| `age` | `ag.age` | `BIGINT` | Already derived by the `age` dependency. |
| `gender` | `p.gender` | `CHAR(1)`/string | Used in the final output and MDRD branch. |
| `mdrd_est` | the gender-dependent `POWER(...)` `CASE` | `DOUBLE` | Estimated baseline creatinine from age, gender, and fixed MDRD constants. |

The female branch is:

```sql
POWER(75.0 / 186.0 / POWER(ag.age, -0.203) / 0.742, -1 / 1.154)
```

The other branch is:

```sql
POWER(75.0 / 186.0 / POWER(ag.age, -0.203), -1 / 1.154)
```

#### `lab`

| Column | Expression | Inferred type | Notes |
|---|---|---|---|
| `hadm_id` | `hadm_id` from `chemistry` | `INTEGER` | One grouped row per admission represented in `chemistry`. |
| `scr_min` | `MIN(creatinine)` | `DOUBLE` | Minimum chemistry creatinine over all chemistry rows for that `hadm_id`. |

#### `ckd`

| Column | Expression | Inferred type | Notes |
|---|---|---|---|
| `hadm_id` | `hadm_id` from `diagnoses_icd` | `INTEGER` | One grouped row per admission with a qualifying CKD diagnosis. |
| `ckd_flag` | `MAX(1)` | `INTEGER` | Always `1` for a grouped qualifying admission. |

## 3. Final output columns and types

The final output order, also recorded in
`oracle/oracle_manifest.full.json`, is:

| Position | Output | Expression | Manifest/inferred type | Nullability/meaning |
|---:|---|---|---|---|
| 1 | `hadm_id` | `p.hadm_id` | `INTEGER` | Admission identity and natural key. |
| 2 | `gender` | `p.gender` | `VARCHAR` (source `CHAR(1)`) | Patient sex/gender value; the left join permits SQL-level NULL if no patient matches. |
| 3 | `age` | `p.age` | `BIGINT` | Age supplied by the `age` dependency; `p` retains only rows with age at least 18. |
| 4 | `scr_min` | `lab.scr_min` | `DOUBLE` | Minimum chemistry creatinine for the admission; NULL when no grouped chemistry row exists. |
| 5 | `ckd` | `COALESCE(ckd.ckd_flag, 0)` | `INTEGER` | `1` for a qualifying CKD diagnosis, otherwise `0`. |
| 6 | `mdrd_est` | `p.mdrd_est` | `DOUBLE` | Gender-dependent simplified MDRD estimate. |
| 7 | `scr_baseline` | final baseline `CASE` | `DOUBLE` | Selected measured minimum or MDRD estimate. |

The manifest reports `row_count: 431231`, `comparison: keyed_join`, and
`key: ["hadm_id"]` for the full oracle. The source grain is therefore one
result row per adult hospital admission (`hadm_id`), assuming the upstream
`age` relation is admission-grained and the two grouped CTEs remain at most one
row per admission. `subject_id` participates in the upstream patient join but
is not emitted by this concept.

## 4. Filters, branch predicates, and value constraints

### `p` CTE `WHERE`

```sql
WHERE ag.age >= 18
```

This excludes admissions whose dependency age is below 18 or NULL. There is no
time window in this predicate.

### `ckd` CTE `WHERE`

The query retains a diagnosis row when either of these complete, paired
predicates is true:

```sql
(
    SUBSTR(icd_code, 1, 3) = '585'
    AND
    icd_version = 9
)
OR
(
    SUBSTR(icd_code, 1, 3) = 'N18'
    AND
    icd_version = 10
)
```

There is no admission-time, diagnosis-time, or other date window. No direct
`itemid`, LOINC, or other measurement code filter occurs in this SQL. The
`chemistry` dependency has its own itemid and value filters; those are inherited
dependency behavior, not additional filters written in
`creatinine_baseline.sql`.

### Non-`WHERE` branch predicates

These conditions alter values and branch selection rather than removing rows:

- `p.gender = 'F'` selects the female MDRD adjustment (`0.742`); every other
  value, including SQL NULL from the left join, takes the other branch.
- `lab.scr_min <= 1.1` selects the measured minimum as `scr_baseline`.
- `ckd.ckd_flag = 1` selects `scr_min` as `scr_baseline` when the first branch
  did not apply. The test uses the raw joined flag, while the emitted `ckd`
  column uses `COALESCE`.
- Otherwise, `mdrd_est` is selected as `scr_baseline`.

The fixed numeric literals in the MDRD computation are `75.0`, `186.0`,
`-0.203`, `0.742`, and `-1 / 1.154`; they are formula constants, not coded
filters.

## 5. Literal code specification (verbatim)

The only coded filter directly named by `creatinine_baseline.sql` is on
`mimiciv_hosp.diagnoses_icd`. It uses three-character prefixes, not a list of
expanded full ICD codes. The exact literals and paired version predicates are:

| Source table | Exact SQL literal/predicate | Feeds |
|---|---|---|
| `mimiciv_hosp.diagnoses_icd` | `SUBSTR(icd_code, 1, 3) = '585'` with `icd_version = 9` | `ckd.ckd_flag = 1`, then final `ckd = 1` and the CKD branch of `scr_baseline` |
| `mimiciv_hosp.diagnoses_icd` | `SUBSTR(icd_code, 1, 3) = 'N18'` with `icd_version = 10` | `ckd.ckd_flag = 1`, then final `ckd = 1` and the CKD branch of `scr_baseline` |

Verbatim code predicate:

```sql
(
    SUBSTR(icd_code, 1, 3) = '585'
    AND
    icd_version = 9
)
OR
(
    SUBSTR(icd_code, 1, 3) = 'N18'
    AND
    icd_version = 10
)
```

There are no direct `itemid` literals in this concept SQL and no dead direct
filter identified. The `chemistry` dependency's creatinine item is the exact
itemid `50912` in its own source SQL, but it must remain attributed to the
`chemistry` concept's code specification rather than being presented as a
direct `creatinine_baseline` filter.

## 6. Joins

| Location | Type | Join condition | Effect |
|---|---|---|---|
| `p` CTE | `LEFT JOIN` | `ag.subject_id = p.subject_id` | Retains every adult `age` row and attaches gender when a patient row matches. |
| final query | `LEFT JOIN` | `p.hadm_id = lab.hadm_id` | Retains adult admissions even when no chemistry aggregate exists; `scr_min` can be NULL. |
| final query | `LEFT JOIN` | `p.hadm_id = ckd.hadm_id` | Retains adult admissions without a qualifying CKD diagnosis; raw `ckd_flag` is NULL and final `ckd` is coalesced to `0`. |

There are no inner joins, right joins, cross joins, range joins, or joins on
time. The `lab` and `ckd` CTEs group by `hadm_id` before the final joins, so
each is intended to contribute at most one row per admission and not multiply
the `p` rows.

## 7. Aggregations and windows

- `lab`: `MIN(creatinine)` grouped by `hadm_id` produces `scr_min`.
- `ckd`: `MAX(1)` grouped by `hadm_id` produces `ckd_flag`.
- No `GROUP BY` occurs in `p` or the final query.
- No window functions, `DISTINCT`, `ORDER BY`, `AVG`, `SUM`, `ARRAY_AGG`, or
  temporal carry-forward operation is present.
- `POWER` is used for the numeric MDRD expression, not as an aggregation.

The creatinine minimum is over the rows supplied by `mimiciv_derived.chemistry`
for an admission; this SQL itself adds no chart-time window. Likewise, CKD is
an admission-level existence flag represented by `MAX(1)`.

## 8. Dependencies and dependency tracing

### `age` dependency

`mimiciv_derived.age` is a required level-0 dependency. This concept consumes
only its `subject_id`, `hadm_id`, and `age` outputs. The upstream canonical age
SQL derives `age` from:

```sql
pa.anchor_age + DATETIME_DIFF(
    ad.admittime,
    DATETIME(pa.anchor_year, 1, 1, 0, 0, 0),
    YEAR
)
```

Thus the age value consumed here traces to `mimiciv_hosp.admissions.admittime`
and `mimiciv_hosp.patients.anchor_age`/`anchor_year`, with
`admissions.subject_id` and `patients.subject_id` establishing the upstream
patient join and `admissions.hadm_id` establishing admission identity.

Within `creatinine_baseline`, `age` has three consequences:

1. `ag.age >= 18` determines whether the admission is included at all.
2. `ag.age` is an exponent input to `mdrd_est`.
3. `p.age` is emitted as the final `age` column.

The curated `MIMIC_NOTES.md` already records that FHIR `Patient.birthDate` is
synthesised from `MIN(transfers.intime) - anchor_age`, not the canonical
`anchor_year - anchor_age`, and that the resulting `age` conflict propagates to
`creatinine_baseline`. This is an existing dataset-wide note, not a new finding
from this source-analysis pass.

### `chemistry` dependency

`mimiciv_derived.chemistry` is the other required level-0 dependency. This
concept consumes its `hadm_id` and `creatinine` columns only. The dependency's
source SQL creates `creatinine` from `mimiciv_hosp.labevents` using exact
itemid `50912`, with `valuenum IS NOT NULL`, the global positivity predicate
`(valuenum > 0 OR itemid = 50868)`, and the creatinine-specific upper bound
`valuenum <= 150`; it groups first by `specimen_id` and then this concept groups
the resulting values by `hadm_id` with `MIN`.

For this consumer, the important dependency traces are:

- `labevents.itemid` (especially exact `50912`) controls whether a row can
  contribute to the dependency's creatinine column.
- `labevents.valuenum` controls non-null/positivity eligibility and the numeric
  value, including the `<= 150` creatinine bound.
- `labevents.specimen_id` controls chemistry's specimen-level grouping.
- The chemistry-derived `hadm_id` controls which admission receives the
  creatinine value and therefore which `lab` group receives it.

The full twelve-item chemistry code list remains specified by the `chemistry`
source analysis; this concept directly uses only the dependency output named
`creatinine`.

## 9. Semantically essential inputs

The following inputs can change inclusion, identity, grouping, or a clinically
meaningful output of this query:

| Input | Branch/group/join controlled | Outputs affected |
|---|---|---|
| `ag.subject_id` and `patients.subject_id` | Patient equality join in `p`; determines which gender row is attached. | `gender`, `mdrd_est`, `scr_baseline`; `subject_id` is also the upstream patient identity. |
| `ag.hadm_id` | Final natural identity and both downstream admission joins. | Final `hadm_id`, `scr_min`, `ckd`, `scr_baseline`, and row alignment. |
| `ag.age` | Adult inclusion predicate and MDRD exponent. | Row inclusion, final `age`, `mdrd_est`, and fallback `scr_baseline`. |
| `patients.gender` | Exact discriminator `gender = 'F'`. | Final `gender`, `mdrd_est`, and fallback `scr_baseline`. |
| `chemistry.hadm_id` | Admission grouping in `lab` and join to `p`. | Which output admission receives `scr_min`; row-level `scr_min` and `scr_baseline`. |
| `chemistry.creatinine` | `MIN` within each admission. | `scr_min`; measured-baseline branch and final `scr_baseline`. |
| `diagnoses_icd.hadm_id` | Admission grouping in `ckd` and join to `p`. | Which admission receives `ckd_flag`; final `ckd` and CKD branch selection. |
| `diagnoses_icd.icd_code` plus `icd_version` | Exact CKD prefix/version filter. | `ckd.ckd_flag`, final `ckd`, and measured-versus-MDRD `scr_baseline` branch. |
| Upstream age inputs `admittime`, `anchor_age`, `anchor_year` | Determine the consumed `age` value. | Inherited effect on adult inclusion, `age`, `mdrd_est`, and `scr_baseline`. |
| Upstream chemistry inputs `labevents.itemid`, `valuenum`, `specimen_id`, and admission association | Determine the dependency's `creatinine` and `hadm_id` values before this query's `MIN`. | `scr_min` and all outputs depending on it. |

There is no temporal carry-forward, time-window membership, or window-function
state in this concept. The only temporal information is indirect through the
upstream age value; chemistry measurements are admission-associated by the
dependency rather than by a time predicate in this SQL.

## 10. Read surface and new dataset-wide quirks

Read before analysis:

- `mimic-iv/AGENTS.md` conventions supplied for this goal.
- `mimic-iv/concept_dag/concept_dag.json` and the `creatinine_baseline` node.
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`.
- Relevant provisional fragments `MIMIC_NOTES.d/chemistry.md` and
  `MIMIC_NOTES.d/kdigo_creatinine.md`; no `MIMIC_NOTES.d/age.md` or
  `MIMIC_NOTES.d/creatinine_baseline.md` existed to read.
- Existing reusable dependency analyses
  `carryover/age/source-analyst.md` and `carryover/chemistry/source-analyst.md`.
- The full oracle manifest entry for `creatinine_baseline` and the current
  `state/creatinine_baseline/state.json` for attempt context.
- Canonical dependency SQL `age.sql` and `chemistry.sql`, plus relevant source
  DDL definitions in `buildmimic/postgres/create.sql`.

No new dataset-wide quirk was discovered. Nothing was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/creatinine_baseline.md`.

## Summary

`creatinine_baseline` emits one row per adult `hadm_id` from the derived age
table, left-joins the admission minimum chemistry creatinine and an admission
CKD flag, and chooses either measured minimum creatinine or a gender- and
age-dependent MDRD estimate. Its direct coded specification is the paired ICD
prefix/version set `585`/9 and `N18`/10 on `mimiciv_hosp.diagnoses_icd`; its
other required inputs are the `age` and `chemistry` derived dependencies.
