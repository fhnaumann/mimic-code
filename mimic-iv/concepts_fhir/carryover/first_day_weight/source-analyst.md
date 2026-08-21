# Source analysis: `first_day_weight`

## Scope and source identity

- Canonical SQL read: `mimic-iv/concepts/firstday/first_day_weight.sql` (21
  lines; source SQL hash in the DAG:
  `be5dbedf07b372ebb5e57f9a8004beaa988ac347e73822b72aedba34af3b69a3`).
- DAG node: `first_day_weight`, level 1, path
  `firstday/first_day_weight.sql`.
- DAG dependency: `weight_durations` (level 0), whose canonical SQL is
  `mimic-iv/concepts/demographics/weight_durations.sql`.
- This document describes the SQL and the dependency contract only. It does
  not author a ViewDefinition, FHIR mapping, or candidate SQL.

## Target SQL table references

The target SQL has one physical source table and one derived dependency:

| SQL clause | Exact relation | Schema/table | Alias | Columns referenced by `first_day_weight` |
|---|---|---|---|---|
| `FROM` (line 14) | ``physionet-data.mimiciv_icu.icustays`` | `mimiciv_icu.icustays` | `ie` | `subject_id`, `stay_id`, `intime` |
| `LEFT JOIN` (line 16) | ``physionet-data.mimiciv_derived.weight_durations`` | `mimiciv_derived.weight_durations` | `ce` | `stay_id`, `starttime`, `weight_type`, `weight` |

There is no `mimiciv_hosp` table reference and no other physical table in the
target SQL.

## Target column inventory and inferred types

The types below are inferred from the MIMIC schema and from the dependency's
canonical expressions. Aggregate outputs are nullable because the join is
left-outer and SQL aggregates ignore NULL values.

### `icustays ie`

- `ie.subject_id`: integer patient identifier. It is selected and grouped.
- `ie.stay_id`: integer ICU-stay identifier. It is selected, grouped, and is
  the join key to `ce.stay_id`.
- `ie.intime`: datetime/timestamp ICU admission time. It is used only in the
  join-time upper-bound expression `DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`.

### `weight_durations ce`

These are columns of the derived dependency as consumed by this target:

- `ce.stay_id`: integer ICU-stay identifier; join key.
- `ce.starttime`: datetime/timestamp interval start; compared to the first-day
  upper bound in the join predicate.
- `ce.weight_type`: text/string discriminator. The target tests the literal
  `'admit'`.
- `ce.weight`: numeric/decimal weight value. The dependency rounds source
  values to three decimal places before exposing this column.

`ce.endtime` is an output of `weight_durations` but is **not read** by
`first_day_weight`.

### Final output columns

The final result has one row for each grouped ICU stay and these six columns,
in this order:

| Output column | Expression | Inferred type | Meaning of the SQL operation |
|---|---|---|---|
| `subject_id` | `ie.subject_id` | integer | Patient identifier |
| `stay_id` | `ie.stay_id` | integer | ICU-stay identifier |
| `weight_admit` | `AVG(CASE WHEN weight_type = 'admit' THEN ce.weight ELSE NULL END)` | nullable numeric/decimal aggregate | Mean of matching admission-type weights only |
| `weight` | `AVG(ce.weight)` | nullable numeric/decimal aggregate | Mean of all matching weight rows |
| `weight_min` | `MIN(ce.weight)` | nullable numeric/decimal | Minimum of all matching weight rows |
| `weight_max` | `MAX(ce.weight)` | nullable numeric/decimal | Maximum of all matching weight rows |

`AVG` returns NULL when its input set has no non-NULL values. In particular,
`weight_admit` is NULL when no matched row has `weight_type = 'admit'`, while
the other three measurements are NULL when there are no matched non-NULL
weights. The exact physical aggregate widening (for example, a numeric AVG
implementation returning a wider numeric type) is engine-dependent, but all
four value columns derive from the dependency's numeric `weight`.

## Filters and join semantics

### Target filters

There is no `WHERE` clause in `first_day_weight.sql`. The only row-selection
predicate is inside the `LEFT JOIN` at lines 17--19:

```sql
ON ie.stay_id = ce.stay_id
    AND ce.starttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

Consequences of the exact predicate:

- The join is `LEFT`, so every `icustays` row remains in the result even when
  no dependency row matches; its aggregate outputs then become NULL.
- Matching requires equal `stay_id` and an inclusive upper bound of one day
  after `ie.intime` (`<=`, not `<`).
- There is no lower bound such as `ce.starttime >= ie.intime`. Dependency rows
  whose `starttime` precedes ICU admission can therefore participate if they
  satisfy the upper-bound test.
- The target does not filter on `weight_type` in the join. It aggregates all
  matching dependency rows into `weight`, `weight_min`, and `weight_max`, and
  uses `weight_type = 'admit'` only for the conditional `weight_admit` branch.
- NULL `ce.starttime` cannot satisfy the comparison and does not match, but
  the left-side ICU stay is still retained.

### Target coded literals

The target SQL contains no `itemid`, ICD, or other coded filter. Its only
literal discriminator is the exact string `'admit'` in the `CASE` expression;
it feeds the output column `weight_admit` by selecting `ce.weight` for that
dependency discriminator and NULL otherwise.

The numeric itemid specification is in the upstream dependency, not in this
consumer SQL. It is recorded here verbatim because it controls which rows and
which `weight_type`/`weight` values can reach this concept:

- Source table: `mimiciv_icu.chartevents` (dependency alias `c`), column
  `c.itemid`, CTE `wt_stg` in `weight_durations.sql`.
- Exact source-SQL set:

  ```sql
  AND c.itemid IN
  (
      226512 -- Admit Wt
      , 224639 -- Daily Weight
  )
  ```

- `226512` feeds `weight_type = 'admit'` through the dependency expression
  `CASE WHEN c.itemid = 226512 THEN 'admit' ELSE 'daily' END`; its resulting
  rows feed `ce.weight`, and then the target's `weight_admit`, `weight`,
  `weight_min`, and `weight_max` aggregates.
- `224639` is the other member of the exact filtered set and feeds
  `weight_type = 'daily'` through the same dependency `CASE`; its resulting
  rows feed `ce.weight`, and then the target's `weight`, `weight_min`, and
  `weight_max` (not `weight_admit`).
- There are no ICD codes or code-system URI literals in either the target SQL
  or the target's dependency reference. The source coding is the numeric
  `chartevents.itemid`; the target itself does not name a FHIR coding system.

The dependency also applies these non-coded value constraints to the same
`mimiciv_icu.chartevents` source before producing `weight_durations`:

```sql
WHERE c.valuenum IS NOT NULL
    AND c.itemid IN (...exact set above...)
    AND c.valuenum > 0
    AND c.valuenum < 1500
```

These constraints are inherited through the dependency; they are not filters
that should be independently re-derived in the `first_day_weight` consumer.

## Aggregations and windows

### `first_day_weight` itself

- `GROUP BY ie.subject_id, ie.stay_id`.
- `AVG` of the conditional admission branch.
- `AVG`, `MIN`, and `MAX` of `ce.weight`.
- No CTEs, window functions, `ORDER BY`, `DISTINCT`, `UNION`, or explicit
  value transformation occur in the target SQL.

The aggregation is over all dependency rows for a stay that pass the join
predicate. It does not choose one weight, carry a value forward, or use
`endtime`.

### Relevant dependency mechanics

The consumer must use the completed `weight_durations` dependency as a table;
it must not rederive it from FHIR resources. For completeness, the dependency
constructs the consumed fields as follows:

- `wt_stg` reads `c.stay_id`, `c.charttime`, `c.itemid`, and `c.valuenum`
  from `mimiciv_icu.chartevents`; it creates `weight_type` and rounded numeric
  `weight`.
- `wt_stg1` applies
  `ROW_NUMBER() OVER (PARTITION BY stay_id, weight_type ORDER BY charttime)`
  as `rn` after `WHERE weight IS NOT NULL`.
- `wt_stg2` inner-joins `wt_stg1` to `mimiciv_icu.icustays` on `stay_id` and
  replaces the first admission weight's `charttime` with
  `DATETIME_SUB(ie.intime, INTERVAL '2' HOUR)`; other starts retain
  `charttime`.
- `wt_stg3` uses
  `LEAD(starttime) OVER (PARTITION BY stay_id ORDER BY starttime)` and
  `COALESCE(..., DATETIME_ADD(outtime, INTERVAL '2' HOUR))` to form `endtime`.
- `wt1` repeats a `LEAD(starttime)` fallback when selecting the interval rows.
- `wt_fix` inner-joins `mimiciv_icu.icustays` to the first `wt1` row per stay
  (`ROW_NUMBER() OVER (PARTITION BY wt1.stay_id ORDER BY wt1.starttime)`) and
  adds a backfill row when `ie.intime < wt.starttime`; the backfill starts at
  `DATETIME_SUB(ie.intime, INTERVAL '2' HOUR)`.
- The dependency's final output is `wt1 UNION ALL wt_fix`, so rows are not
  deduplicated by the dependency. Its output columns are `stay_id`,
  `starttime`, `endtime`, `weight`, and `weight_type`; the consumer reads all
  except `endtime`.

The dependency's physical table/join inventory is therefore:

| Dependency SQL clause | Relation | Type/condition |
|---|---|---|
| `wt_stg` `FROM` | `mimiciv_icu.chartevents c` | Physical source |
| `wt_stg2` `FROM` | CTE `wt_stg1` | Intermediate relation |
| `wt_stg2` `INNER JOIN` | `mimiciv_icu.icustays ie` | `ie.stay_id = wt_stg1.stay_id` |
| `wt_stg3` `FROM` | CTE `wt_stg2` | Intermediate relation |
| `wt1` `FROM` | CTE `wt_stg3` | Intermediate relation |
| `wt_fix` `FROM` | `mimiciv_icu.icustays ie` | Physical source |
| `wt_fix` `INNER JOIN` | subquery over CTE `wt1` (`wt`) | `ie.stay_id = wt.stay_id AND wt.rn = 1 AND ie.intime < wt.starttime` |
| final first branch | CTE `wt1` | `UNION ALL` branch |
| final second branch | CTE `wt_fix` | `UNION ALL` branch |

## Natural grain and key

The target output grain is one row per ICU stay. The SQL grouping key is the
compound `(subject_id, stay_id)`. In the MIMIC ICU source, `stay_id` is the
natural unique ICU-stay identifier, with `subject_id` identifying the patient
associated with it; `subject_id` alone is not a key because a patient can have
multiple stays. The derived weight table is many-row-per-`stay_id`, and the
target collapses those rows to the one-stay grain.

## Semantically essential inputs and control flow

These values can change inclusion, keying, grouping, or a clinically
meaningful output:

1. `icustays.subject_id` — controls the grouped patient identifier and the
   output `subject_id`; it is part of the SQL grouping key.
2. `icustays.stay_id` — controls the output/grouping key and the only target
   join, so it determines which weight-duration rows are eligible for a stay.
3. `icustays.intime` — controls the inclusive `starttime <= intime + 1 day`
   temporal gate. Changing it can add or remove every one of the four weight
   aggregates for that stay. The same source field also participates upstream
   in the dependency's admission-time adjustment and gap backfill.
4. `weight_durations.stay_id` — controls association of each derived weight
   row to an ICU stay through the equality join.
5. `weight_durations.starttime` — controls whether each dependency row passes
   the first-day upper-bound predicate. It is therefore an inclusion field,
   even though it is not an output column.
6. `weight_durations.weight_type` — controls the conditional branch for
   `weight_admit`; only the exact value `'admit'` enters that aggregate.
7. `weight_durations.weight` — controls the numeric inputs to `weight_admit`,
   `weight`, `weight_min`, and `weight_max`; its NULL status also controls
   whether a row contributes to each aggregate.
8. Upstream `chartevents.itemid` — through the dependency's exact set
   (`226512`, `224639`) controls row inclusion and the admit/daily
   discriminator that reaches the target.
9. Upstream `chartevents.valuenum` — through the dependency's non-NULL,
   positive, `< 1500` constraints controls row inclusion and the rounded
   numeric `weight` reaching the target.
10. Upstream `chartevents.charttime` and dependency sequencing — chart time
    controls the `ROW_NUMBER` order and normally becomes `starttime`; for the
    first admission weight, the dependency substitutes `icustays.intime - 2
    hours`. This can change whether a row passes the target's first-day gate.
    The dependency's backfill branch can add another row when the first weight
    starts after `intime`; `UNION ALL` preserves that added row and can change
    all applicable aggregates.

`weight_durations.endtime` and its `LEAD` calculations are not consumed by
`first_day_weight`, so they do not directly control this target's inclusion or
numeric outputs. They remain part of the dependency's published schema but
are not a required consumer input.

## Notes and provisional leads checked

- Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md`. Its general identifier,
  datetime, itemid, and chartevents ETL notes do not change the source SQL
  facts above. No FHIR mapping was made here.
- Read the provisional lead
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/weight_durations.md`. It reports
  concept-specific probe findings about global chartevents omissions and ICU
  Encounter `intime` DST normalization, including possible arithmetic effects
  on first-admission weight starts. Those are provisional dataset/ETL leads,
  not additional predicates in `first_day_weight.sql`; they should be checked
  by the FHIR prober and must not be used to alter the literal source contract.
