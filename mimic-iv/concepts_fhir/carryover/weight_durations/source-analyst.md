# Source analysis: `weight_durations`

## Source and DAG metadata

- Canonical SQL: `mimic-iv/concepts/demographics/weight_durations.sql`.
- The SQL uses BigQuery-style fully qualified names (`physionet-data.mimiciv_icu...`); the logical MIMIC schema is `mimiciv_icu`.
- DAG node: stem `weight_durations`, path `demographics/weight_durations.sql`, level `0`, recorded SHA256 `82e23dd4ac6d0dc316438d08ee3f5edab2c4ca0f6535c23b3ab40eb7cafcd795`.
- DAG dependencies: none. There is no reference to `mimiciv_derived` in this SQL, so no other concept must be ported first for this source.
- DAG dependents are `first_day_weight`, `kdigo_uo`, and `urine_output_rate`; these consume this derived table but are not dependencies of it.
- The stored DAG passed `uv run mimic_utils concept_dag --check`.

The canonical query has six CTE stages (`wt_stg`, `wt_stg1`, `wt_stg2`,
`wt_stg3`, `wt1`, and `wt_fix`) and a final `UNION ALL`. It does not create a
table in the SQL text; its intended derived output is
`mimiciv_derived.weight_durations`.

## Physical table references

Every physical source table reference is in the ICU schema:

| SQL location | Schema | Table | Alias | Use |
|---|---|---|---|---|
| `weight_durations.sql:10` | `mimiciv_icu` | `chartevents` | `c` | Select qualifying numeric weight chart events. |
| `weight_durations.sql:46-47` | `mimiciv_icu` | `icustays` | `ie` | Attach ICU `intime`/`outtime` and provide the stay spine. |
| `weight_durations.sql:95-107` | `mimiciv_icu` | `icustays` | `ie` | Identify stays needing a synthetic pre-first-measurement interval. |

The other `FROM` clauses refer to CTEs or a derived subquery, not physical
tables:

- `wt_stg1` reads `wt_stg` (`:31`).
- `wt_stg2` reads `wt_stg1` and inner-joins `icustays` (`:45-47`).
- `wt_stg3` reads `wt_stg2` (`:61`).
- `wt1` reads `wt_stg3` (`:80`).
- The `wt_fix` subquery reads `wt1` (`:105`), and the outer `wt_fix` query reads
  `icustays` and that subquery (`:95-107`).
- The final two branches read `wt1` and `wt_fix` (`:119-127`).

There are no references to `mimiciv_hosp`, `d_items`, `patients`,
`admissions`, or any other source table.

## Source columns and inferred types

The source DDL defines `chartevents.stay_id` and `itemid` as `INTEGER`,
`charttime` as `TIMESTAMP`, and `valuenum` as `FLOAT`; it defines
`icustays.stay_id` as `INTEGER` and `intime`/`outtime` as `TIMESTAMP`. The
canonical SQL's `DATETIME_*` expressions are therefore described below as
datetime/timestamp values; the exact physical timestamp representation is
dialect-specific.

### Physical source columns referenced

| Source field | Inferred type | Referenced for |
|---|---|---|
| `mimiciv_icu.chartevents.stay_id` | integer | Output, ICU-stay join, all partitions/windows, and final row identity. |
| `mimiciv_icu.chartevents.charttime` | timestamp/datetime | Output of `wt_stg`; chronological ordering; ordinary `starttime`; interval carry-forward. |
| `mimiciv_icu.chartevents.itemid` | integer | Item filter and `admit` versus `daily` discriminator. |
| `mimiciv_icu.chartevents.valuenum` | floating numeric | Non-null/positive/plausibility filters and rounded `weight`. |
| `mimiciv_icu.icustays.stay_id` | integer | Inner-join key and synthetic-row stay id. |
| `mimiciv_icu.icustays.intime` | timestamp/datetime, nullable in source DDL | Backdating the first admission weight, backfill start, and backfill inclusion test. |
| `mimiciv_icu.icustays.outtime` | timestamp/datetime, nullable in source DDL | Default end of the last measurement and the second end-time fallback. |

Fields present in the physical tables but not used include `subject_id`,
`hadm_id`, `value`, `valueuom`, and `warning` from `chartevents`, and the
care-unit/LOS fields from `icustays`. There is no unit conversion or unit
filter.

### CTE columns

| CTE | Columns and inferred type |
|---|---|
| `wt_stg` | `stay_id` integer; `charttime` timestamp/datetime; `weight_type` string; `weight` numeric/decimal rounded to 3 decimal places. |
| `wt_stg1` | `stay_id` integer; `charttime` timestamp/datetime; `weight_type` string; `weight` numeric; `rn` integer/bigint from `ROW_NUMBER()`. |
| `wt_stg2` | `stay_id` integer; `intime` and `outtime` timestamp/datetime; `weight_type` string; `starttime` timestamp/datetime; `weight` numeric. |
| `wt_stg3` | `stay_id` integer; `intime` and `outtime` timestamp/datetime; `starttime` and `endtime` timestamp/datetime; `weight` numeric; `weight_type` string. |
| `wt1` | `stay_id` integer; `starttime` and `endtime` timestamp/datetime; `weight` numeric; `weight_type` string. |
| `wt_fix` inner subquery | `stay_id` integer; `starttime` timestamp/datetime; `weight` numeric; `weight_type` string; `rn` integer/bigint. |
| `wt_fix` | `stay_id` integer; `starttime` and `endtime` timestamp/datetime; `weight` numeric; `weight_type` string. |

The final output has exactly these five columns, in this order:

1. `stay_id` — integer.
2. `starttime` — timestamp/datetime.
3. `endtime` — timestamp/datetime.
4. `weight` — numeric/decimal, obtained by casting `valuenum` to `NUMERIC`
   and rounding to three decimal places.
5. `weight_type` — string, either `admit` or `daily` for rows admitted by the
   current item set.

`intime`, `outtime`, `charttime`, `itemid`, `valuenum`, and all `rn` values are
intermediate inputs only; they are not final columns.

## Filters and literal code specification

### Predicates

`wt_stg` applies all source-event filters (`weight_durations.sql:11-18`):

- `c.valuenum IS NOT NULL`.
- `c.itemid IN (...)` as specified verbatim below.
- `c.valuenum > 0`.
- `c.valuenum < 1500`.

`wt_stg1` additionally applies `weight IS NOT NULL` (`:32`). Because `weight`
is derived from a non-null `valuenum`, this is effectively redundant for
ordinary numeric casts, but it is part of the canonical behavior.

The `wt_fix` inner join has two row-selection predicates in its `ON` clause
(`:107-109`): `wt.rn = 1` and `ie.intime < wt.starttime`. Equality does not
qualify for the backfill. There is no explicit date window, adult/age filter,
subject filter, admission filter, or code exclusion. The opening comment says
“adult ICU patients,” but the SQL contains no adult-age predicate; the actual
population is determined by the two itemids, the numeric filters, and the
stay join.

### Literal code set (verbatim)

The only coded filter is the following exact itemid set on
`mimiciv_icu.chartevents.itemid` (`weight_durations.sql:12-17`):

```sql
c.itemid IN
(
    226512 -- Admit Wt
    , 224639 -- Daily Weight
)
```

This set feeds `wt_stg.weight_type` and therefore the final
`weight_durations.weight_type` column. The classification expression is also
literal and itemid-dependent (`:7-8`):

```sql
CASE WHEN c.itemid = 226512 THEN 'admit'
    ELSE 'daily' END AS weight_type
```

Given the preceding `IN` filter, `226512` produces `admit` and `224639`
produces `daily`; the `ELSE` is not a separate filter. No ICD codes, other
itemids, or expected-absent/dead code filters occur.

The value constraints are applied to the original `valuenum` before the
`NUMERIC` cast/three-place rounding; the rounded value is what reaches the
output.

## Joins

1. **`wt_stg2`: INNER JOIN** `mimiciv_icu.icustays ie` to `wt_stg1`:
   `ie.stay_id = wt_stg1.stay_id` (`:46-47`). A qualifying chart event with no
   matching ICU stay is dropped. This join supplies `intime` and `outtime`.
2. **`wt_fix`: INNER JOIN** `mimiciv_icu.icustays ie` to the first-row
   subquery `wt`:
   `ie.stay_id = wt.stay_id AND wt.rn = 1 AND ie.intime < wt.starttime`
   (`:95-109`). It emits only a stay's first `wt1` interval when that interval
   starts strictly after ICU `intime`, creating one backfill row for that stay.

There are no LEFT joins, cross joins, joins to a dimension table, or joins on
patient/admission identifiers.

## Windows, interval arithmetic, and row construction

There is no `GROUP BY` and no aggregate function. `ROUND` is a scalar numeric
transformation, not an aggregation. The four window expressions are:

1. `wt_stg1.rn`:
   `ROW_NUMBER() OVER (PARTITION BY stay_id, weight_type ORDER BY charttime)`
   (`:28-30`). It numbers each weight type independently within a stay. The
   first admission-weight row (`weight_type = 'admit'`, `rn = 1`) is the one
   whose start is backdated; this is not the first weight across both types.
2. `wt_stg3.endtime`:
   `LEAD(starttime) OVER (PARTITION BY stay_id ORDER BY starttime)`
   (`:55-57`). It takes the next start across both weight types, not the next
   start within one type, and falls back to `outtime + 2 hours` at the end.
3. `wt1.endtime`:
   `LEAD(starttime) OVER (PARTITION BY stay_id ORDER BY starttime)` inside the
   `COALESCE` fallback (`:69-76`). This repeats the same stay-wide temporal
   ordering if `wt_stg3.endtime` is null, then again falls back to
   `outtime + 2 hours`.
4. The `wt_fix` subquery's `rn`:
   `ROW_NUMBER() OVER (PARTITION BY wt1.stay_id ORDER BY wt1.starttime)`
   (`:102-104`). It selects the first interval per stay for the backfill test.

The canonical ordering clauses have no tie-breaker beyond the listed time
column. Duplicate timestamps can therefore have an unspecified order for
`ROW_NUMBER()`/`LEAD()`; the SQL does not deduplicate tied events.

Datetime arithmetic is:

- `wt_stg2.starttime`: for the first admission weight only,
  `DATETIME_SUB(ie.intime, INTERVAL '2' HOUR)`; otherwise the original
  `charttime` (`:41-43`).
- `wt_stg3.endtime`: next `starttime`, or
  `DATETIME_ADD(outtime, INTERVAL '2' HOUR)` (`:55-58`).
- `wt1.endtime`: existing `wt_stg3.endtime`, otherwise next `starttime`,
  otherwise the same `outtime + 2 hours` expression (`:69-77`).
- `wt_fix.starttime`: `DATETIME_SUB(ie.intime, INTERVAL '2' HOUR)` (`:89-93`).
- `wt_fix.endtime`: the first `wt1.starttime` for the stay (`:100-109`).

No source charttime is explicitly constrained to `intime`/`outtime`; chart
events are attached by `stay_id`, ordered by their effective start, and only
the synthetic backfill condition compares the first start with `intime`.

The final query is:

- all `wt1` interval rows, followed by
- all qualifying `wt_fix` backfill rows,

combined with `UNION ALL` (`:113-127`). It preserves multiplicity and does not
remove duplicate or overlapping intervals.

## Natural grain and key

The logical grain is one weight-measurement interval per qualifying ICU
weight chart event, plus at most one synthetic pre-first-measurement interval
per ICU stay. `wt1` retains one row per qualifying event after the stay join;
it is not one row per stay and is not aggregated. `wt_fix` contributes at
most one row per `stay_id` because it uses the first `wt1` row and an inner
join condition.

There is no declared or selected source event identifier and no guaranteed
unique final key. The temporal identities used by the SQL are:

- `(stay_id, weight_type, charttime)` for the first-admission ranking;
- `(stay_id, starttime)` for the stay-wide interval ranking and `LEAD()`; and
- `stay_id` for the optional backfill row.

These are logical grouping/order keys, not guaranteed unique keys: duplicate
chart events, tied timestamps, and the `UNION ALL` can produce repeated
`(stay_id, starttime, weight_type)` tuples. Any downstream keyed comparison
must therefore treat the source grain as potentially duplicate unless its
manifest explicitly establishes a key.

## Semantically essential inputs and their effects

- **`chartevents.itemid`**: controls inclusion in the item set, maps
  `226512` to `admit` versus `224639` to `daily`, determines the
  `stay_id + weight_type` ranking partition, and affects final `weight_type`.
- **`chartevents.valuenum`**: controls row inclusion through null/positive/
  `<1500` predicates and supplies the clinically meaningful numeric `weight`
  after `NUMERIC` casting and three-decimal rounding.
- **`chartevents.stay_id`**: controls the ICU-stay inner join, all temporal
  partitions/windows, final output identity, and the backfill grouping.
- **`chartevents.charttime`**: controls the first-admission `rn`, supplies
  ordinary measurement `starttime`, orders all later intervals, determines
  each `LEAD()`-derived `endtime`, and determines which interval is copied by
  `wt_fix`.
- **`icustays.stay_id`**: supplies the matching stay spine and the synthetic
  row's output `stay_id`.
- **`icustays.intime`**: changes the first admission weight's start time,
  changes every synthetic backfill's start time, and controls whether a
  backfill row is included through the strict `< wt.starttime` predicate.
- **`icustays.outtime`**: controls the terminal two-hour end-time extension
  whenever no next measurement start exists (and the repeated fallback).
- **Derived `weight_type`, `starttime`, and `rn`**: these are not independent
  source fields, but they are essential intermediate discriminators. The
  type controls ranking; the first admission `rn` controls backdating; the
  stay-wide first `rn` controls backfill; and `starttime` controls interval
  carry-forward and the backfill's end.

`subject_id`, `hadm_id`, `value`, `valueuom`, care-unit fields, LOS, and item
labels do not affect this SQL because they are never selected, filtered, or
joined.

## Relevant shared MIMIC-on-FHIR notes / possible dataset-wide consideration

The existing `mimic-iv/concepts_fhir/MIMIC_NOTES.md` has two relevant
dataset-wide facts for downstream probing, without changing what the source
SQL specifies:

1. Itemid-derived Observation coding carries the relational itemid verbatim in
   `Observation.code.coding.code`; the ICU chartevents stream uses the
   `mimic-chartevents-d-items` system. The exact source filter above must be
   confirmed against those two itemids; no label substitution is justified.
2. The upstream FHIR ETL can normalize spring-forward DST-gap chartevent times
   before writing `Observation.effectiveDateTime`, and the shared note warns
   that downstream interval/grouping logic can amplify that shift. This
   concept uses chart time in `ROW_NUMBER()`, `LEAD()`, strict backfill
   comparison, and output interval boundaries, so this is a dataset-wide
   timestamp consideration for `MIMIC_NOTES.d/weight_durations.md` and for
   later equivalence analysis. The ICU encounter/identifier note also makes
   `stay_id` a required identifier value rather than a resource UUID when the
   output stay key is reconstructed.

No new dataset-wide quirk was established by this source-only analysis, and no
sibling `MIMIC_NOTES.d` fragment was used as evidence.
