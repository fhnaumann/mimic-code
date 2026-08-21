# Source analysis: `kdigo_stages`

## Source and DAG identity

- DAG stem: `kdigo_stages`
- DAG path: `organfailure/kdigo_stages.sql`
- SQL read: `mimic-iv/concepts/organfailure/kdigo_stages.sql`
- DAG level: 2
- DAG dependencies: `crrt`, `kdigo_creatinine`, and `kdigo_uo`
- The dependency stems are the derived tables that the consumer must use; the
  consumer must not rederive them from FHIR resources.

## 1. Table and CTE references

The canonical SQL uses the `physionet-data` project prefix. The schema/table
references, using the repository's schema names, are:

| SQL location | Join kind | Schema | Table | Alias | Columns read by `kdigo_stages` |
|---|---|---|---|---|---|
| `cr_stg` `FROM` | base | `mimiciv_derived` | `kdigo_creatinine` | `cr` | `stay_id`, `charttime`, `creat_low_past_7day`, `creat_low_past_48hr`, `creat` |
| `uo_stg` `FROM` | base | `mimiciv_derived` | `kdigo_uo` | `uo` | `stay_id`, `charttime`, `weight`, `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr`, `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr` |
| `uo_stg` `JOIN` | `INNER JOIN` | `mimiciv_icu` | `icustays` | `ie` | `stay_id`, `intime` |
| `crrt_stg` `FROM` | base | `mimiciv_derived` | `crrt` | none | `stay_id`, `charttime`, `crrt_mode` |
| final `FROM` | base | `mimiciv_icu` | `icustays` | `ie` | `subject_id`, `hadm_id`, `stay_id`, `intime` |

The other `FROM`/`JOIN` references are CTE references, not physical tables:
`cr_stg`, `uo_stg`, `crrt_stg`, and `tm_stg`.

### Derived dependency contract

These are the exact columns read from the three `mimiciv_derived` tables:

1. `kdigo_creatinine` (`FROM ...mimiciv_derived.kdigo_creatinine cr`):
   `stay_id`, `charttime`, `creat_low_past_7day`, `creat_low_past_48hr`, and
   `creat`. Its `hadm_id` and any other column are not read.
2. `kdigo_uo` (`FROM ...mimiciv_derived.kdigo_uo uo`): `stay_id`, `charttime`,
   `weight`, `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr`, `uo_tm_6hr`,
   `uo_tm_12hr`, and `uo_tm_24hr`.
3. `crrt` (`FROM ...mimiciv_derived.crrt`): `stay_id`, `charttime`, and
   `crrt_mode`.

The unqualified candidate-side table names for these dependencies are the
stems `kdigo_creatinine`, `kdigo_uo`, and `crrt`, respectively. The target
reads the already-derived values above; it does not read raw labevents,
outputevents, or chartevents directly.

## 2. Columns and inferred types

Types below are inferred from MIMIC context and the SQL expressions, rather
than asserted from a catalog. Nullable means the SQL can produce or carry a
NULL at this stage.

### Intermediate CTE columns

#### `cr_stg`

| Column | Inferred type | Nullable | Role |
|---|---|---:|---|
| `stay_id` | integer identifier | yes in the CTE contract | event key and later join key |
| `charttime` | timestamp/datetime | yes in the CTE contract | event key and later join key |
| `creat_low_past_7day` | numeric/decimal | yes | seven-day creatinine baseline used by stage branches |
| `creat_low_past_48hr` | numeric/decimal | yes | 48-hour creatinine baseline used by stage branches |
| `creat` | numeric/decimal | yes | current creatinine and stage input |
| `aki_stage_creat` | integer stage value | no within `cr_stg` because the searched `CASE` has `ELSE 0` | creatinine-derived stage |

`aki_stage_creat` is an integer from the numeric literals `0`, `1`, `2`, and
`3`. The `CASE` falls through to `0` when no comparison is true; comparison
with a NULL baseline is unknown and also falls through. The final LEFT JOIN
can still make the final output column NULL when there is no matching
creatinine event at a `tm_stg` time.

#### `uo_stg`

| Column | Inferred type | Nullable | Role |
|---|---|---:|---|
| `stay_id` | integer identifier | yes in the CTE contract | event key and later join key |
| `charttime` | timestamp/datetime | yes in the CTE contract | event key, ICU-time gate, and later join key |
| `weight` | numeric/decimal | yes | selected from the dependency but not referenced by any `kdigo_stages` expression |
| `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr` | numeric/decimal rates | yes | UO stage predicates and final output |
| `aki_stage_uo` | nullable integer stage value | yes | UO-derived stage; explicitly NULL when `uo_rt_6hr` is NULL |

The duration columns are read from the dependency but are not projected by
this CTE's select list:
`uo_tm_6hr`, `uo_tm_12hr`, and `uo_tm_24hr` are nullable numeric/decimal
durations and control the stage predicates.

`ie.intime` is a timestamp/datetime. It is used in the UO stage `CASE`, but is
not projected by `uo_stg`.

#### `crrt_stg`

| Column | Inferred type | Nullable | Role |
|---|---|---:|---|
| `stay_id` | integer identifier | yes in the CTE contract | event key and later join key |
| `charttime` | timestamp/datetime | yes | event key and later join key |
| `aki_stage_crrt` | nullable integer stage value | yes | fixed CRRT stage; 3 only when `charttime IS NOT NULL` |

`crrt_mode` is a text/string dependency column. It is filtered in this CTE
but is not projected.

#### `tm_stg`

`tm_stg` contains `stay_id` (integer identifier) and `charttime`
(timestamp/datetime), both nullable in the outer-join context. It is the
distinct union of the `(stay_id, charttime)` pairs from the three stage CTEs.

### Final output columns

The final select emits, in order:

| Output column | Inferred type | Source/derivation |
|---|---|---|
| `subject_id` | integer identifier | `ie.subject_id` |
| `hadm_id` | integer identifier | `ie.hadm_id` |
| `stay_id` | integer identifier | `ie.stay_id` |
| `charttime` | timestamp/datetime | `tm.charttime` |
| `creat_low_past_7day` | nullable numeric/decimal | `cr.creat_low_past_7day` |
| `creat_low_past_48hr` | nullable numeric/decimal | `cr.creat_low_past_48hr` |
| `creat` | nullable numeric/decimal | `cr.creat` |
| `aki_stage_creat` | nullable integer | `cr.aki_stage_creat` |
| `uo_rt_6hr` | nullable numeric/decimal | `uo.uo_rt_6hr` |
| `uo_rt_12hr` | nullable numeric/decimal | `uo.uo_rt_12hr` |
| `uo_rt_24hr` | nullable numeric/decimal | `uo.uo_rt_24hr` |
| `aki_stage_uo` | nullable integer | `uo.aki_stage_uo` |
| `aki_stage_crrt` | nullable integer | `crrt.aki_stage_crrt` |
| `aki_stage` | integer-valued stage | `GREATEST` of the three `COALESCE`d stage values |
| `aki_stage_smoothed` | integer-valued stage | six-hour windowed `MAX` of the same combined stage expression |

`weight`, `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr`, and `crrt_mode` are
intermediate inputs but are not final output columns.

## 3. Filters and value constraints

### Explicit `WHERE` predicates

The target SQL has exactly one `WHERE` clause:

- In `crrt_stg`, `WHERE crrt_mode IS NOT NULL`. This excludes derived CRRT
  rows whose mode is NULL before the CRRT stage and event-time union are built.

There are no `WHERE` clauses in `cr_stg`, `uo_stg`, `tm_stg`, or the final
select. In particular, `kdigo_stages.sql` has no raw itemid, ICD, code-system,
time-window, or numeric value filter in a `WHERE` clause.

### Stage predicates (not row filters)

These predicates alter stage values rather than filtering rows.

#### Creatinine stage (`cr_stg`)

The searched `CASE` is evaluated top-to-bottom:

1. `cr.creat >= (cr.creat_low_past_7day * 3.0)` → stage `3`.
2. `cr.creat >= 4` **and**
   (`cr.creat >= (cr.creat_low_past_48hr + 0.3)` **or**
   `cr.creat >= (1.5 * cr.creat_low_past_7day)`) → stage `3`.
3. `cr.creat >= (cr.creat_low_past_7day * 2.0)` → stage `2`.
4. `cr.creat >= (cr.creat_low_past_48hr + 0.3)` → stage `1`.
5. `cr.creat >= (cr.creat_low_past_7day * 1.5)` → stage `1`.
6. Otherwise → stage `0`.

The `4` threshold is inclusive, the multiplicative thresholds are inclusive,
and the `0.3` increase thresholds are inclusive. The SQL contains a comment
`TODO: initiation of RRT`, but no RRT criterion is implemented in this CTE.

#### Urine-output stage (`uo_stg`)

The searched `CASE` is evaluated top-to-bottom:

1. `uo.uo_rt_6hr IS NULL` → `NULL`.
2. `uo.charttime <= DATETIME_ADD(ie.intime, INTERVAL '6' HOUR)` → stage `0`.
3. `uo.uo_tm_24hr >= 24 AND uo.uo_rt_24hr < 0.3` → stage `3`.
4. `uo.uo_tm_12hr >= 12 AND uo.uo_rt_12hr = 0` → stage `3`.
5. `uo.uo_tm_12hr >= 12 AND uo.uo_rt_12hr < 0.5` → stage `2`.
6. `uo.uo_tm_6hr >= 6 AND uo.uo_rt_6hr < 0.5` → stage `1`.
7. Otherwise → stage `0`.

The six-hour admission check is an inclusive `<=` comparison. The SQL uses
the dependency's duration columns to require the specified observation span;
it does not require a separate raw-event count.

#### CRRT stage (`crrt_stg`)

`CASE WHEN charttime IS NOT NULL THEN 3 ELSE NULL END AS aki_stage_crrt`.
Together with `WHERE crrt_mode IS NOT NULL`, this makes a retained non-NULL
mode/time row a stage-3 CRRT signal. A retained row with NULL `charttime`
would have a NULL stage; its NULL time also cannot match the final timestamp
equality joins because SQL NULLs do not equal NULLs.

#### Combined stage

`aki_stage` is:

```text
GREATEST(
  COALESCE(cr.aki_stage_creat, 0),
  COALESCE(uo.aki_stage_uo, 0),
  COALESCE(crrt.aki_stage_crrt, 0)
)
```

Thus a missing component stage contributes zero to the combined stage. The
same expression is repeated inside the smoothing window.

## 4. Joins and set operations

1. `uo_stg` uses an **INNER JOIN** from
   `mimiciv_icu.icustays ie` to the `kdigo_uo uo` dependency on
   `uo.stay_id = ie.stay_id`. This restricts the UO stage CTE to UO rows whose
   stay has an ICU-stay row and supplies `ie.intime`.
2. The final query uses a **LEFT JOIN** from `mimiciv_icu.icustays ie` to
   `tm_stg tm` on `ie.stay_id = tm.stay_id`.
3. It then uses a **LEFT JOIN** to `cr_stg cr` on
   `ie.stay_id = cr.stay_id AND tm.charttime = cr.charttime`.
4. It uses a **LEFT JOIN** to `uo_stg uo` on
   `ie.stay_id = uo.stay_id AND tm.charttime = uo.charttime`.
5. It uses a **LEFT JOIN** to `crrt_stg crrt` on
   `ie.stay_id = crrt.stay_id AND tm.charttime = crrt.charttime`.

There are no direct final joins among the three stage CTEs. `tm_stg` is the
alignment spine. Its three inputs are combined with `UNION DISTINCT`, in this
order: `(stay_id, charttime)` from `cr_stg`, then `uo_stg`, then `crrt_stg`.
This deduplicates equal stay/time pairs across and within the three inputs.

## 5. Aggregations and windows

- There is no `GROUP BY` in `kdigo_stages.sql`.
- `UNION DISTINCT` performs set deduplication of the event-time pairs.
- `GREATEST` combines the three component stage values row-wise; it is not a
  SQL aggregate.
- `aki_stage_smoothed` uses a windowed `MAX` over the repeated combined-stage
  expression:

  ```sql
  MAX(GREATEST(COALESCE(...), COALESCE(...), COALESCE(...))) OVER (
      PARTITION BY ie.subject_id
      ORDER BY DATETIME_DIFF(tm.charttime, ie.intime, SECOND)
      RANGE BETWEEN 21600 PRECEDING AND CURRENT ROW
  )
  ```

  The order expression is numeric elapsed seconds relative to each row's ICU
  `intime`; `21600` is a six-hour preceding range. The partition is by
  `subject_id`, **not** by `stay_id`, and there is no tie-breaker beyond the
  elapsed-seconds order value. Consequently, the smoothing window is exactly
  subject-partitioned and can span rows from multiple ICU stays of the same
  subject when their relative elapsed-second order values fall in the same
  range.

## 6. Literal code set

`kdigo_stages.sql` contains **no literal coded filter**. There are:

- no `itemid` literals,
- no `icd_code` or `icd_version` literals,
- no code-system literals, and
- no other enumerated code set.

The only inclusion predicate in this SQL is the non-coded `crrt_mode IS NOT
NULL` test. The itemid/code literals used to construct the
upstream `crrt`, `kdigo_creatinine`, and `kdigo_uo` concepts belong to those
dependency SQL specifications, not to the `kdigo_stages` code specification;
this consumer reads their derived columns listed above and must not invent a
replacement code mapping.

## 7. Natural grain and row behavior

The intended event grain is one row per `(stay_id, charttime)` for every
distinct charttime contributed by a creatinine, UO, or retained CRRT row. The
final output also carries `subject_id` and `hadm_id` from the ICU stay, but
those are attributes rather than the event key. `tm_stg`'s `UNION DISTINCT`
is what establishes one event-axis row per distinct pair, assuming each
dependency is at its expected one-row-per-stay/time grain.

Because the final base is `icustays` and the join to `tm_stg` is LEFT, an ICU
stay with no event pair in `tm_stg` still has a final row with `charttime =
NULL` and NULL component columns; the combined `COALESCE`d stage expression
evaluates to zero. A NULL charttime is not a usable equality-join key, so it
does not match NULL charttimes in the component CTEs.

The ordinary non-NULL natural key is therefore `(stay_id, charttime)`. The
NULL-charttime fallback row is stay-level rather than a meaningful timed
event, and SQL NULL-key semantics must be preserved. The final query has no
`DISTINCT`, `GROUP BY`, or final deduplication beyond `tm_stg`; an unexpected
duplicate in a dependency at the same stay/time would fan out the final row.

## 8. Semantically essential inputs and trace

These are the inputs whose values can change inclusion in the event axis,
natural grain, stage branches, or six-hour carry-forward. This is a source
description, not a representability decision.

### Event identity and inclusion

- `stay_id` from `icustays` and all three dependencies controls every join and
  defines the ICU-stay component of the natural key. It determines which
  patient/stay receives each stage and which rows enter `tm_stg`.
- `charttime` from `kdigo_creatinine`, `kdigo_uo`, and `crrt` controls the
  event-time union, exact component alignment, final `charttime` output, the
  UO admission-age test, the CRRT non-NULL-time stage branch, and the smoothing
  order. Changing it can add/remove a `tm_stg` pair, move a component to a
  different row, or change the six-hour window.
- `crrt_mode` controls row inclusion in `crrt_stg` through
  `WHERE crrt_mode IS NOT NULL`. Its retained row then supplies the CRRT
  event-time pair and, when its charttime is non-NULL, the fixed stage-3
  signal.
- `subject_id` from `icustays` is the partition discriminator for
  `aki_stage_smoothed` and is also a final output identifier. It is not
  interchangeable with `stay_id` for the window because the SQL deliberately
  partitions at subject level.
- `intime` from `icustays` controls the UO six-hour eligibility branch and the
  numeric elapsed-seconds ordering used by `aki_stage_smoothed`.
- `hadm_id` from `icustays` is a final output identifier. It does not control a
  row filter, join, stage branch, or window in this SQL, but changing it changes
  the emitted admission identity.

### Creatinine branch

- `creat` from `kdigo_creatinine` feeds every creatinine stage comparison and
  the final `creat` column.
- `creat_low_past_7day` feeds the stage-3 three-times-baseline branch, the
  stage-2 two-times-baseline branch, the stage-3 `>= 4` associated-increase
  branch, and the stage-1 1.5-times-baseline branch; it is also emitted.
- `creat_low_past_48hr` feeds the stage-3 `>= 4` associated-increase branch
  and the stage-1 acute-increase branch; it is also emitted.
- The dependency `aki_stage_creat` is recomputed here; `kdigo_stages` does not
  consume a precomputed creatinine stage from `kdigo_creatinine`.

### Urine-output branch

- `uo_rt_6hr` controls the initial NULL branch and the stage-1 threshold, and
  is emitted.
- `uo_rt_12hr` controls the anuria stage-3 branch and the stage-2 threshold,
  and is emitted.
- `uo_rt_24hr` controls the 24-hour stage-3 threshold and is emitted.
- `uo_tm_6hr`, `uo_tm_12hr`, and `uo_tm_24hr` control whether the corresponding
  duration requirement is met before a rate can produce stages. They are not
  emitted.
- `weight` is selected into `uo_stg` but is not referenced by any expression
  in `kdigo_stages`; the dependency has already used it to derive the UO rates.
  It is consequently a dependency-contract column, but not an independently
  operative input to this consumer after the rates and durations are supplied.

### Combined and smoothed outputs

- `aki_stage_creat`, `aki_stage_uo`, and `aki_stage_crrt` feed the row-level
  `aki_stage` maximum after NULLs are replaced with zero. Each component can
  therefore raise the row-level stage, while a missing component contributes
  zero.
- The same combined stage, `subject_id`, `intime`, and `charttime` feed the
  `MAX` carry-forward over the six-hour numeric `RANGE`. Any change to a stage
  or its event-time/order value can change `aki_stage_smoothed` on the current
  row and on subsequent rows in that subject partition.

## Dataset-note cross-check

I read the shared `MIMIC_NOTES.md` and the relevant fragments
`MIMIC_NOTES.d/crrt.md`, `kdigo_creatinine.md`, `kdigo_uo.md`,
`urine_output.md`, `first_day_urine_output.md`, `weight_durations.md`,
`creatinine_baseline.md`, and `icustay_times.md` before recording this
analysis. Existing notes identify dataset-wide DST normalization effects in
labevents, outputevents, and chartevents that can propagate through the
dependency windows and this concept's time-based joins/windows. They also
document repeated same-time chartevents and outputevents dateTime-only
timing. No new dataset-wide quirk was established by this source-only read;
those are existing dataset notes, while the subject-partitioned smoothing
window and NULL-charttime fallback above are facts specific to this SQL.
