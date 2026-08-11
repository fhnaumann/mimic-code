# Source analysis: `icustay_detail`

## Authority and DAG position

- The DAG node is `icustay_detail`, with source path
  `demographics/icustay_detail.sql`, level `0`, and SHA-256
  `35103cee621ed025d266e6c4c59916515ad2ecf59e6b1f1962bff5821e463cd8`.
  The hash of the authoritative SQL file was checked and matches this value.
- The authoritative source is
  `mimic-iv/concepts/demographics/icustay_detail.sql` (47 lines).
- The DAG records no `mimiciv_derived` dependencies and no dependents for this
  node. There are no CTEs in the source SQL; the query is one final `SELECT`.

## Table references

Every table reference in the source is listed below, including its SQL alias
and role:

| SQL clause | Fully qualified source table | Schema/table | Alias | Referenced columns |
|---|---|---|---|---|
| `FROM` | ``physionet-data.mimiciv_icu.icustays`` | `mimiciv_icu.icustays` | `ie` | `subject_id`, `hadm_id`, `stay_id`, `intime`, `outtime` |
| `INNER JOIN` | ``physionet-data.mimiciv_hosp.admissions`` | `mimiciv_hosp.admissions` | `adm` | `hadm_id`, `subject_id`, `admittime`, `dischtime`, `race`, `hospital_expire_flag` |
| `INNER JOIN` | ``physionet-data.mimiciv_hosp.patients`` | `mimiciv_hosp.patients` | `pat` | `subject_id`, `gender`, `dod`, `anchor_age`, `anchor_year` |

The `physionet-data` project qualifier is present in the canonical SQL. The
concept uses only the `mimiciv_icu` and `mimiciv_hosp` schemas; it does not
reference `mimiciv_derived` or any other schema.

## Joins and row-grain implications

1. `ie` is joined to `adm` with an `INNER JOIN` on
   `ie.hadm_id = adm.hadm_id` (source lines 43–45). This retains only ICU
   stay rows whose hospital admission exists. The predicate does not also
   compare `subject_id`; it relies on `hadm_id` identifying the admission and
   being consistent with the ICU row.
2. The result is joined to `pat` with an `INNER JOIN` on
   `ie.subject_id = pat.subject_id` (source lines 44–47). This retains only
   rows whose patient dimension row exists.

There is no `LEFT JOIN`, `RIGHT JOIN`, `FULL JOIN`, `CROSS JOIN`, or
self-join. The query has no `DISTINCT`, so any duplicate source rows or
non-unique matching rows in a join would be preserved/multiplied. Under the
MIMIC relational grain, the intended output is one row per qualifying ICU stay
(`stay_id`).

The SQL itself does not declare a key. The full oracle manifest records a
`keyed_join` comparison with natural key `stay_id`, and reports 73,181 rows.
`stay_id` is selected directly from `mimiciv_icu.icustays`; it is therefore the
key to preserve in a port. `subject_id` and `hadm_id` identify the patient and
hospitalization context, but are not the natural key. Multiple ICU stays can
share one `hadm_id`.

## Complete referenced-column inventory and inferred types

The input types below are from the MIMIC-IV PostgreSQL DDL at
`mimic-iv/buildmimic/postgres/create.sql` (admissions lines 23–41, patients
lines 227–235, and icustays lines 415–425). Output types are the inferred
types of the canonical expressions, cross-checked against the oracle manifest.

### `mimiciv_icu.icustays AS ie`

- `ie.subject_id`: `INTEGER`, selected as output `subject_id` and used in the
  patient join.
- `ie.hadm_id`: `INTEGER`, selected as output `hadm_id`, used in the admission
  join, and used to partition the ICU-stay window.
- `ie.stay_id`: `INTEGER`, selected as output `stay_id` and the natural key
  used by the oracle comparison.
- `ie.intime`: nullable `TIMESTAMP`, selected as `icu_intime`, used as the
  start of the ICU LOS calculation, and used to order/partition ICU sequence
  ranks.
- `ie.outtime`: nullable `TIMESTAMP`, selected as `icu_outtime` and used as
  the end of the ICU LOS calculation.

The source column `ie.los` exists in the raw table but is not referenced; the
query recomputes ICU LOS from `intime` and `outtime` instead.

### `mimiciv_hosp.admissions AS adm`

- `adm.hadm_id`: `INTEGER`, used only in the inner join.
- `adm.subject_id`: `INTEGER`, used in the hospital-stay window partition;
  it is not selected directly (the output `subject_id` comes from `ie`).
- `adm.admittime`: non-null `TIMESTAMP`, selected as `admittime`, used in
  hospital LOS, admission-age, and hospital-stay ordering expressions.
- `adm.dischtime`: nullable `TIMESTAMP`, selected as `dischtime` and used in
  the hospital LOS expression.
- `adm.race`: `VARCHAR(80)`, selected unchanged as `race`.
- `adm.hospital_expire_flag`: `SMALLINT`, selected unchanged as
  `hospital_expire_flag`.

Other admissions columns, including `deathtime`, are not referenced.

### `mimiciv_hosp.patients AS pat`

- `pat.subject_id`: `INTEGER`, used only in the inner join.
- `pat.gender`: `CHAR(1)` in the source table, selected as output `gender`
  (the oracle output type is `VARCHAR`).
- `pat.dod`: `DATE`, selected unchanged as `dod`.
- `pat.anchor_age`: nullable `SMALLINT`, used in the admission-age
  calculation.
- `pat.anchor_year`: non-null `SMALLINT`, used to construct the anchor
  datetime in the admission-age calculation.

Other patient columns, including `anchor_year_group`, are not referenced.

### Final output schema, in SQL order

| # | Output column | Canonical expression / source | Inferred oracle type |
|---:|---|---|---|
| 1 | `subject_id` | `ie.subject_id` | `INTEGER` |
| 2 | `hadm_id` | `ie.hadm_id` | `INTEGER` |
| 3 | `stay_id` | `ie.stay_id` | `INTEGER` |
| 4 | `gender` | `pat.gender` | `VARCHAR` |
| 5 | `dod` | `pat.dod` | `DATE` |
| 6 | `admittime` | `adm.admittime` | `TIMESTAMP` |
| 7 | `dischtime` | `adm.dischtime` | `TIMESTAMP` |
| 8 | `los_hospital` | `DATETIME_DIFF(adm.dischtime, adm.admittime, DAY)` | `BIGINT` |
| 9 | `admission_age` | `pat.anchor_age + DATETIME_DIFF(adm.admittime, DATETIME(pat.anchor_year, 1, 1, 0, 0, 0), YEAR)` | `BIGINT` |
| 10 | `race` | `adm.race` | `VARCHAR` |
| 11 | `hospital_expire_flag` | `adm.hospital_expire_flag` | `SMALLINT` |
| 12 | `hospstay_seq` | `DENSE_RANK() OVER (PARTITION BY adm.subject_id ORDER BY adm.admittime)` | `BIGINT` |
| 13 | `first_hosp_stay` | `CASE WHEN` the same hospital rank `= 1` `THEN TRUE ELSE FALSE END` | `BOOLEAN` |
| 14 | `icu_intime` | `ie.intime` | `TIMESTAMP` |
| 15 | `icu_outtime` | `ie.outtime` | `TIMESTAMP` |
| 16 | `los_icu` | `ROUND(CAST(DATETIME_DIFF(ie.outtime, ie.intime, HOUR) / 24.0 AS NUMERIC), 2)` | `DECIMAL(38,2)` |
| 17 | `icustay_seq` | `DENSE_RANK() OVER (PARTITION BY ie.hadm_id ORDER BY ie.intime)` | `BIGINT` |
| 18 | `first_icu_stay` | `CASE WHEN` the same ICU rank `= 1` `THEN TRUE ELSE FALSE END` | `BOOLEAN` |

There are no intermediate CTE columns. The output manifest confirms the
18-column order and types above. `los_hospital` is a whole-day difference;
`los_icu` is an hour difference divided by 24 and rounded to two decimal
places. Neither uses the stored `ie.los`.

## Filters and predicates

There is no `WHERE`, `HAVING`, `QUALIFY`, or `FILTER` clause. Specifically,
the source contains:

- no `itemid` filter;
- no `icd_code`/`icd_version` filter;
- no other coded-value inclusion or exclusion;
- no time-window predicate;
- no numeric/value plausibility constraint; and
- no null-value predicate or explicit code exclusion.

The two `INNER JOIN` predicates are the only row-retention predicates. The
`DATETIME_DIFF` calls are calculations, not time filters. `gender`, `race`,
and `hospital_expire_flag` are output values only and are never used to
restrict rows.

## Literal code specification

There are no coded filters in this SQL. Therefore the exact literal code set
is empty: no `itemid`, ICD code/version, LOINC code, or other code literal is
named, no source table is filtered by a code set, and no code feeds an output
column or CTE. There are no dead coded filters to report.

## Window functions, scalar calculations, and ordering semantics

- The hospital window is textually invoked twice: `DENSE_RANK()` partitions
  by `adm.subject_id` and orders by `adm.admittime`. It feeds
  `hospstay_seq` and the `first_hosp_stay` boolean.
- The ICU window is textually invoked twice: `DENSE_RANK()` partitions by
  `ie.hadm_id` and orders by `ie.intime`. It feeds `icustay_seq` and the
  `first_icu_stay` boolean.
- There is no `GROUP BY`, aggregate function, aggregate value pivot, or outer
  `ORDER BY`. `ROUND` is scalar rounding, not an aggregation.
- Because these are `DENSE_RANK` windows, tied admission times receive the
  same hospital sequence, and tied ICU start times receive the same ICU
  sequence. Consequently, all tied rank-1 rows satisfy the corresponding
  first-stay flag; the flags are not guaranteed to be unique.
- The hospital rank is evaluated after the ICU-to-admission inner join. Thus
  `hospstay_seq`/`first_hosp_stay` rank the patient's admissions represented by
  the joined ICU rows, not admissions with no ICU stay. The ICU rank is over
  ICU stays within each joined `hadm_id`.
- The canonical expressions do not specify `NULLS FIRST` or `NULLS LAST`.
  `adm.admittime` is non-null in the source DDL; `ie.intime` is nullable, so
  the placement of null ICU start times follows the target SQL engine's
  default ordering unless a dialect transpilation supplies an explicit null
  ordering.

## Dependency and coding conclusion

`icustay_detail` is a level-0, raw-table concept with no derived-table
dependency. It is a relational demographic/detail projection at ICU-stay
grain, enriched by hospital admission and patient attributes, with two LOS
calculations and two rank/first-stay pairs. It has no source code system or
literal coded filter to port.
