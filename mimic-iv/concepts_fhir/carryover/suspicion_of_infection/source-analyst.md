# Source analysis — `sepsis/suspicion_of_infection`

Canonical SQL: `mimic-iv/concepts/sepsis/suspicion_of_infection.sql` (193
lines). The DAG node is stem `suspicion_of_infection`, level 1, with the
exact source SHA256
`943d9a7a4058c03d03f1965a58d89e1b6eabcccd50e5b75de835030fe784e29d`.
Its only DAG dependency is `antibiotic`; its dependent is `sepsis3`.

This analysis describes the SQL only. It does not derive or reconstruct any
FHIR/resource identifier.

## 1. Table and CTE references

### Physical tables referenced by this SQL

| SQL reference | Schema | Table | Use |
|---|---|---|---|
| ``physionet-data.mimiciv_derived.antibiotic`` `abx` | `mimiciv_derived` | `antibiotic` | Source of antibiotic rows in `ab_tbl`; this is the DAG dependency. |
| ``physionet-data.mimiciv_hosp.microbiologyevents`` | `mimiciv_hosp` | `microbiologyevents` | Source of cultures in `me`. |

The target SQL does not directly read `mimiciv_hosp.prescriptions` or
`mimiciv_icu.icustays`; those are upstream inputs of the separate
`mimiciv_derived.antibiotic` concept. The relevant source DDL confirms that
`prescriptions` has `subject_id`, `hadm_id`, `starttime`, `stoptime`, `drug`,
`drug_type`, and `route`, while `icustays` has `subject_id`, `hadm_id`,
`stay_id`, `intime`, and `outtime`.

### CTE references

- `ab_tbl` is read by both culture-matching CTEs and again by the final
  `SELECT`.
- `me` is read twice: as `me72` in `me_then_ab` and as `me24` in
  `ab_then_me`.
- `ab_then_me` and `me_then_ab` are both read by the final `SELECT`.

## 2. Columns and inferred types

### `ab_tbl`

`ab_tbl` reads these exact dependency columns from
`mimiciv_derived.antibiotic`:

- `subject_id` — INTEGER; partition and culture-match identity, final output.
- `hadm_id` — INTEGER; retained for output and used as an `ab_id` ordering
  tiebreaker, but not used in either microbiology time join.
- `stay_id` — INTEGER, nullable where the dependency's ICU left join found no
  stay; retained for output and used as an `ab_id` ordering tiebreaker.
- `antibiotic` — VARCHAR/string; final output and `ab_id` ordering.
- `starttime` — TIMESTAMP; renamed `antibiotic_time`, used for all precise
  time-window predicates and final output.
- `stoptime` — TIMESTAMP; renamed `antibiotic_stoptime`, used only in the
  `ab_id` ordering.

Derived `ab_tbl` columns are:

- `antibiotic_time` — TIMESTAMP, alias of `abx.starttime`.
- `antibiotic_date` — DATE/DATETIME day boundary, from
  `DATETIME_TRUNC(abx.starttime, DAY)`; used only by date-only culture
  windows.
- `antibiotic_stoptime` — TIMESTAMP, alias of `abx.stoptime`; not in the final
  output.
- `ab_id` — BIGINT, from `ROW_NUMBER()` partitioned by `subject_id` and
  ordered by `starttime`, `stoptime`, `antibiotic`, `hadm_id`, `stay_id`.

### `me`

`me` reads these `mimiciv_hosp.microbiologyevents` columns:

- `micro_specimen_id` — INTEGER; grouping key and final tie-break key for
  choosing one culture per antibiotic.
- `subject_id` — INTEGER; aggregated with `MAX`, then used in both culture
  joins.
- `hadm_id` — INTEGER, nullable; aggregated with `MAX` but not consumed by
  either matching CTE or the final output.
- `chartdate` — source TIMESTAMP(0) in the DDL; `CAST(MAX(chartdate) AS
  DATE)` produces `chartdate` as DATE for date-only matching.
- `charttime` — nullable TIMESTAMP(0); `MAX(charttime)` retains the precise
  culture time when available and also determines whether the precise-time or
  date-only branch is used.
- `spec_type_desc` — VARCHAR(100), non-null in the source DDL; `MAX` produces
  the specimen description used as `specimen` and as the existence test for a
  matching culture.
- `org_itemid` — nullable INTEGER; used by the positivity `CASE`.
- `org_name` — nullable VARCHAR(100); used by the positivity `CASE`.

The CTE output columns are:

- `micro_specimen_id` — INTEGER.
- `subject_id` — INTEGER.
- `hadm_id` — INTEGER.
- `chartdate` — DATE.
- `charttime` — TIMESTAMP, nullable.
- `spec_type_desc` — VARCHAR(100).
- `positiveculture` — INTEGER, the `MAX` of a 0/1 `CASE` over all rows in a
  specimen group.

The `microevent_id`, `spec_itemid`, `test_seq`, `test_itemid`, `test_name`,
`isolate_num`, `ab_itemid`, `ab_name`, susceptibility fields, and `comments`
exist in the source schema but are not referenced by this SQL.

### `me_then_ab` and `ab_then_me`

Both CTEs carry the antibiotic identity columns `subject_id`, `hadm_id`,
`stay_id`, and `ab_id` from `ab_tbl`, plus `micro_specimen_id` and a selected
culture's derived fields. Their output aliases are:

- `me_then_ab`: `last72_charttime` (TIMESTAMP/DATETIME),
  `last72_positiveculture` (INTEGER), `last72_specimen` (VARCHAR), and
  `micro_seq` (BIGINT) for the selected culture before the antibiotic.
- `ab_then_me`: `next24_charttime` (TIMESTAMP/DATETIME),
  `next24_positiveculture` (INTEGER), `next24_specimen` (VARCHAR), and
  `micro_seq` (BIGINT) for the selected culture after the antibiotic.

`last72_charttime` and `next24_charttime` are each
`COALESCE(charttime, DATETIME(chartdate))`; therefore date-only cultures are
represented at the date's midnight for the downstream time outputs and
ordering.

### Final output

The final table has one row per `ab_tbl` row and these columns. Types below
agree with the full oracle manifest:

| Output column | Type | Meaning in the SQL |
|---|---|---|
| `subject_id` | INTEGER | Dependency antibiotic subject. |
| `stay_id` | INTEGER | Dependency ICU stay, nullable when no stay matched upstream. |
| `hadm_id` | INTEGER | Dependency hospitalization. |
| `ab_id` | BIGINT | Subject-local antibiotic-row ordinal. |
| `antibiotic` | VARCHAR | Dependency antibiotic drug-name value. |
| `antibiotic_time` | TIMESTAMP | Dependency `starttime`. |
| `suspected_infection` | INTEGER | `0` if neither selected culture exists, else `1`. |
| `suspected_infection_time` | TIMESTAMP, nullable | Selected prior culture time when present, otherwise antibiotic time for a selected subsequent culture; NULL when neither exists. |
| `culture_time` | TIMESTAMP, nullable | Selected prior culture time, otherwise selected subsequent culture time. |
| `specimen` | VARCHAR, nullable | Selected prior specimen description, otherwise selected subsequent specimen description. |
| `positive_culture` | INTEGER, nullable | Positive flag from the selected prior culture, otherwise the selected subsequent culture; NULL with no culture. |

The final output does not expose `antibiotic_stoptime`, `antibiotic_date`,
`micro_specimen_id`, or the intermediate `micro_seq`.

## 3. Filters and temporal rules

There is **no `WHERE` clause** in `suspicion_of_infection.sql`. Row inclusion
and culture selection are implemented by `CASE` expressions, temporal `ON`
predicates, window ordering, and final `LEFT JOIN ... micro_seq = 1`
conditions.

### Culture positivity predicate in `me`

For each `micro_specimen_id`, a microbiology row is positive when all of these
are true:

```sql
org_name IS NOT NULL
AND org_itemid != 90856
AND org_name != ''
```

That row contributes `1`; every other row contributes `0`; `MAX` makes
`positiveculture = 1` if any row in the specimen group is positive, otherwise
`0`. SQL NULL behavior is material: a NULL `org_itemid` does not satisfy
`org_itemid != 90856`, and a NULL/empty `org_name` is not positive.

### Prior-culture window: `me_then_ab`

The `me72` `LEFT JOIN` matches only the same `subject_id`; it does **not** use
`hadm_id` or `stay_id`. It then applies one of two branches:

1. If `me72.charttime IS NOT NULL`, the antibiotic is strictly after the
   culture and no later than 72 hours after it:

   `ab_tbl.antibiotic_time > me72.charttime` and
   `ab_tbl.antibiotic_time <= DATETIME_ADD(me72.charttime, INTERVAL 72 HOUR)`.
2. If `me72.charttime IS NULL`, the day-truncated antibiotic date is from the
   culture date through three days after it, inclusive:

   `antibiotic_date >= me72.chartdate` and
   `antibiotic_date <= DATE_ADD(me72.chartdate, INTERVAL 3 DAY)`.

Among matches, `ROW_NUMBER()` partitions by `(ab_tbl.subject_id, ab_tbl.ab_id)`
and orders by `me72.chartdate`, `me72.charttime NULLS LAST`,
`me72.positiveculture DESC`, and `me72.micro_specimen_id`. The final query
keeps only `me2ab.micro_seq = 1`.

### Subsequent-culture window: `ab_then_me`

The `me24` `LEFT JOIN` also matches only the same `subject_id`, not
`hadm_id`/`stay_id`. It applies:

1. If `me24.charttime IS NOT NULL`, the antibiotic is at or after 24 hours
   before the culture and strictly before the culture:

   `ab_tbl.antibiotic_time >= DATETIME_SUB(me24.charttime, INTERVAL 24 HOUR)`
   and `ab_tbl.antibiotic_time < me24.charttime`.
2. If `me24.charttime IS NULL`, the day-truncated antibiotic date is from one
   day before the culture date through the culture date, inclusive:

   `ab_tbl.antibiotic_date >= DATE_SUB(me24.chartdate, INTERVAL 1 DAY)` and
   `ab_tbl.antibiotic_date <= me24.chartdate`.

Among matches, `ROW_NUMBER()` partitions by `(ab_tbl.subject_id, ab_tbl.ab_id)`
and orders by `me24.chartdate`, `me24.charttime NULLS LAST`,
`me24.positiveculture DESC`, and `me24.micro_specimen_id`. The final query
keeps only `ab2me.micro_seq = 1`.

### Final derivation rules

- `suspected_infection = 0` exactly when both `last72_specimen` and
  `next24_specimen` are NULL; otherwise it is `1`.
- `suspected_infection_time` is NULL for the no-culture case. Otherwise it is
  `COALESCE(last72_charttime, antibiotic_time)`, so a prior culture wins and a
  subsequent-only culture uses the antibiotic time rather than the subsequent
  culture time.
- `culture_time` is `COALESCE(last72_charttime, next24_charttime)`.
- `specimen` is `COALESCE(last72_specimen, next24_specimen)`.
- `positive_culture` is `COALESCE(last72_positiveculture,
  next24_positiveculture)`.

There is no carry-forward computation beyond these two bounded culture
windows and the one-culture-per-window selection.

## 4. Joins

All joins in the canonical target SQL are `LEFT JOIN`s:

1. In `me_then_ab`, `ab_tbl LEFT JOIN me me72` joins on
   `ab_tbl.subject_id = me72.subject_id` and the precise-time/date-only
   prior-culture window described above.
2. In `ab_then_me`, `ab_tbl LEFT JOIN me me24` joins on
   `ab_tbl.subject_id = me24.subject_id` and the precise-time/date-only
   subsequent-culture window described above.
3. In the final query, `ab_tbl LEFT JOIN ab_then_me ab2me` joins on
   `subject_id`, `ab_id`, and `ab2me.micro_seq = 1`.
4. In the final query, `ab_tbl LEFT JOIN me_then_ab me2ab` joins on
   `subject_id`, `ab_id`, and `me2ab.micro_seq = 1`.

The final joins are deliberately left joins: every antibiotic row remains in
the result even when neither culture window matches. The `micro_seq = 1`
predicates are in `ON`, not `WHERE`, so they do not turn the final joins into
inner joins.

## 5. `mimiciv_derived` dependency

The DAG records exactly one dependency: `antibiotic` from
`medication/antibiotic.sql`. The consumer reads these dependency output
columns, with the following target uses:

| Dependency column | Target use |
|---|---|
| `subject_id` | `ab_tbl` identity; `ROW_NUMBER` partition; both microbiology joins; final output and final joins. |
| `hadm_id` | `ab_tbl` value; `ab_id` ordering tiebreak; final output. Not used to constrain cultures. |
| `stay_id` | `ab_tbl` value; `ab_id` ordering tiebreak; final output. |
| `antibiotic` | `ab_tbl` value; `ab_id` ordering; final output. |
| `starttime` | Aliased to `antibiotic_time`; precise culture windows, date truncation, and final output. |
| `stoptime` | Aliased to `antibiotic_stoptime`; `ab_id` ordering only. |

The dependency's `route` column is not read by this consumer. The candidate
must preserve the dependency boundary and consume the completed dependency
under the unqualified concept stem `antibiotic`; it must not rederive these
values from FHIR resources.

## 6. Aggregations and windows

- `ab_tbl`: `ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY starttime,
  stoptime, antibiotic, hadm_id, stay_id)` creates `ab_id`.
- `me`: `GROUP BY micro_specimen_id`; `MAX` collapses duplicate microbiology
  rows for a specimen for `subject_id`, `hadm_id`, `chartdate`, `charttime`,
  `spec_type_desc`, and the positivity `CASE`. `chartdate` is cast to DATE
  after `MAX`.
- `me_then_ab`: `ROW_NUMBER()` by `(subject_id, ab_id)` with the prior-culture
  ordering described above.
- `ab_then_me`: `ROW_NUMBER()` by `(subject_id, ab_id)` with the
  subsequent-culture ordering described above.
- There is no final `GROUP BY`, `DISTINCT`, or aggregate. The final
  `COALESCE`/`CASE` expressions are scalar value derivations.

## 7. Literal code set and literal predicates — verbatim

The only coded literal in the target SQL is an organism `itemid` exclusion;
there are no ICD codes and no `WHERE itemid IN (...)` set.

### Organism itemid exclusion

- Source table: `mimiciv_hosp.microbiologyevents`.
- Source column: `org_itemid`.
- Exact source predicate: `org_itemid != 90856`.
- Exact literal code: `90856` (integer).
- Feeds: `me.positiveculture`, then `last72_positiveculture` /
  `next24_positiveculture`, the positive-culture-priority ordering in both
  culture windows, and final `positive_culture`.

The SQL also names these non-code value predicates in the same positivity
filter; they are recorded verbatim because they affect the coded result:

- Source table/column: `mimiciv_hosp.microbiologyevents.org_name`; exact
  predicates `org_name IS NOT NULL` and `org_name != ''`; the exact empty
  string literal is `''`.
- The exact time-branch predicates are `me72.charttime IS NOT NULL`,
  `me72.charttime IS NULL`, `me24.charttime IS NOT NULL`, and
  `me24.charttime IS NULL`.
- The exact row-selection predicates are `ab2me.micro_seq = 1` and
  `me2ab.micro_seq = 1`.

No dead-filter status is asserted here: the SQL names `90856`, but this source
analysis does not substitute a data-presence claim for the literal.

## 8. Semantically essential inputs

These are the inputs whose values can change row inclusion, row identity,
grouping, temporal selection, or a clinically meaningful output:

| Input/discriminator | What it controls |
|---|---|
| Dependency `subject_id` | Antibiotic ordinal partition; both culture candidate sets; final row joins; output identity. |
| Dependency `starttime` | `antibiotic_time`; precise 72-hour/24-hour windows; day-only fallback via `antibiotic_date`; suspected-infection timing; `ab_id` order. |
| Dependency `stoptime` | `ab_id` order, and therefore the subject-local identity used to attach cultures. It is not otherwise output. |
| Dependency `antibiotic` | Output drug-name value and `ab_id` order; changing it can change the ordinal and downstream culture attachment. |
| Dependency `hadm_id` and `stay_id` | Output values and `ab_id` tie-breaking. `hadm_id`/`stay_id` do not filter microbiology matches. The upstream ICU fan-out means one hospitalization's prescription can appear once per matching ICU stay. |
| Generated `ab_id` | Natural row identity and the final joins to the selected prior/subsequent cultures. |
| `micro_specimen_id` | `me` grouping key and deterministic tie-break when cultures otherwise share ordering values. It selects which specimen's time, positivity, and description feed the output. |
| Microbiology `subject_id` | Determines whether a culture can match an antibiotic; it is not replaced by `hadm_id`. |
| `charttime` and `chartdate` | Select precise versus date-only temporal branches, define the culture windows, order candidate cultures, and generate `culture_time`/`specimen`/`suspected_infection_time`. |
| `spec_type_desc` | Determines whether a selected culture exists (`IS NULL` versus non-NULL) and is the emitted `specimen`. |
| `org_itemid` and `org_name` | Determine each organism row's positivity, specimen-level `positiveculture`, same-time culture priority, and final `positive_culture`. |
| `positiveculture` | Chooses a positive culture ahead of a negative one when date/time tie, then feeds final `positive_culture`. |

The source microbiology `hadm_id` is referenced and aggregated, but it is not
used after `me` is built and therefore cannot change this target's final
values or row matching. Likewise, raw microbiology fields not listed above
are not semantically consumed by this SQL.

## 9. Grain and key

The semantic grain is **one output row per row of `ab_tbl`**, i.e. one row per
record emitted by the completed `antibiotic` dependency, including the
dependency's ICU-stay fan-out copies. The target does not produce one row per
microbiology event; `me` collapses rows by `micro_specimen_id`, and each
antibiotic receives at most one selected culture from each temporal direction.

`ab_id` is a subject-local `ROW_NUMBER` assigned after the dependency rows are
read. The source SQL's natural/comparison key is `(subject_id, ab_id)`; the
oracle manifest confirms this keyed join. `pharmacy_id` and `drug_type` from
the upstream prescriptions table are not carried into this target, so they
are not part of its output key. Resource/FHIR keys, if later carried beside
these columns, are opaque identity values and are not part of this source
key or a means to infer any source value.

## Evidence

Concept: `suspicion_of_infection`; source path:
`/Users/nau025/Documents/mimic-code/mimic-iv/concepts/sepsis/suspicion_of_infection.sql`.
Read and checked the DAG node in
`mimic-iv/concept_dag/concept_dag.json`, the canonical target SQL, the
upstream `mimic-iv/concepts/medication/antibiotic.sql` and its carryover
analysis for the dependency boundary, the relevant MIMIC-IV PostgreSQL source
DDL/constraints for `microbiologyevents`, `prescriptions`, and `icustays`, the
oracle manifest entry for output types and `(subject_id, ab_id)` key,
`LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and the carryover ledger convention.
Checked tables, columns, all CTE joins and windows, all temporal branches,
the organism literal `90856`, the empty-string/non-NULL positivity predicates,
the scalar output derivations, and the sole `mimiciv_derived` dependency with
its exact consumed columns. Reusable artifact written to
`/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/carryover/suspicion_of_infection/source-analyst.md`.
Summary: this is an antibiotic-grain table that selects at most one
microbiology culture before and after each dependency antibiotic using
subject-only bounded time windows, derives suspicion and positivity, and has
no direct raw-table joins beyond `microbiologyevents`.
