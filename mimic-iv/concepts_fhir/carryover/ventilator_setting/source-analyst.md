# Source analysis: `ventilator_setting`

## Source and DAG identity

- Concept stem: `ventilator_setting`
- DAG-resolved source path: `mimic-iv/concepts/measurement/ventilator_setting.sql`
- DAG node: level `0`, dependencies `[]`, dependent `ventilation`
- DAG SQL SHA256: `80ac2b4bde1d4e8324f1818bd36c453fe0b70b2e90e228762ecfe65fcc757708`
- The source file's SHA256 was checked against the DAG and matched exactly.

The SQL uses the dataset-qualified reference
``physionet-data.mimiciv_icu.chartevents``. In schema/table terms this is
schema `mimiciv_icu`, table `chartevents`.

## Query shape and natural grain

The query has one CTE, `ce`, followed by one grouped pivot query. It returns one
row for each distinct `(subject_id, charttime)` among the rows surviving the
CTE's filters. `stay_id` is not part of the `GROUP BY`; the output value is
`MAX(stay_id)`. Thus the SQL's natural output grain/key is
`(subject_id, charttime)`, not `(subject_id, stay_id, charttime)` and not one
row per source chartevents row.

Within a group, each item-specific numeric output is the maximum cleaned
`valuenum` for that item, and each textual mode/type output is the lexicographic
maximum `value` for that item. Repeated source rows are therefore collapsed by
the aggregates. The query does not select or preserve a source row identifier.

## Table references

| SQL construct | Join type | Reference | Columns used by this concept |
|---|---|---|---|
| `FROM` in CTE `ce` (line 34) | N/A | `mimiciv_icu.chartevents` (written as ``physionet-data.mimiciv_icu.chartevents``) | `subject_id`, `stay_id`, `charttime`, `itemid`, `value`, `valuenum`, `valueuom`, `storetime` |

There are no `JOIN` clauses and no dimension-table references. In particular,
`mimiciv_icu.d_items` is not referenced. Other `chartevents` columns such as
`hadm_id`, `caregiver_id`, and `warning` are also not selected or referenced.

## CTE `ce`

`ce` selects the following source columns and derived column:

| CTE column | Source/expression | Inferred source/output type | Use after/within CTE |
|---|---|---|---|
| `subject_id` | `ce.subject_id` | `INTEGER` | Selected into the CTE; final grouping key and output column. |
| `stay_id` | `ce.stay_id` | `INTEGER` | CTE filter; final `MAX(stay_id)` output. |
| `charttime` | `ce.charttime` | `TIMESTAMP` | Final grouping key and output column. |
| `itemid` | `itemid` | `INTEGER` | CTE item filter; all cleaning/pivot discriminators. |
| `value` | `value` | `VARCHAR(200)` | CTE non-NULL filter; final textual pivots for ventilator mode/type. |
| `valuenum` | source `valuenum` used in the `CASE` expression | `FLOAT` floating-point numeric | Cleaned into the CTE's derived `valuenum`; final numeric pivots. |
| `valueuom` | `valueuom` | `VARCHAR(20)` | Selected into `ce` but never referenced by the outer query; no final output effect. |
| `storetime` | `storetime` | `TIMESTAMP` | Selected into `ce` but never referenced by the outer query; no final output effect. |
| `valuenum` (derived) | The item-specific cleaning `CASE` at lines 9-31 | `FLOAT` floating-point numeric, nullable | Consumed by all numeric `MAX(CASE...)` expressions. |

The types above follow the MIMIC-IV ICU `chartevents` schema: integer IDs,
timestamp `charttime`/`storetime`, `VARCHAR(200)` `value`, floating-point
`valuenum`, and `VARCHAR(20)` `valueuom`. The exact physical floating-point
name can be dialect-specific; the source schema declares it as `FLOAT`.

## Filters and value cleaning

### Row filters (`WHERE`, lines 35-50)

The complete `WHERE` predicate is:

```sql
ce.value IS NOT NULL
AND ce.stay_id IS NOT NULL
AND ce.itemid IN
(
    224688 -- Respiratory Rate (Set)
    , 224689 -- Respiratory Rate (spontaneous)
    , 224690 -- Respiratory Rate (Total)
    , 224687 -- minute volume
    , 224685, 224684, 224686 -- tidal volume
    , 224696 -- PlateauPressure
    , 220339, 224700 -- PEEP
    , 223835 -- fio2
    , 223849 -- vent mode
    , 229314 -- vent mode (Hamilton)
    , 223848 -- vent type
    , 224691 -- Flow Rate (L)
)
```

There is no time-window predicate, no date predicate, no `valuenum` row
filter, no unit filter, no code exclusion beyond the positive `itemid IN`
set, and no predicate on `storetime` or `valueuom`.

### FIO2 cleaning (lines 10-22)

For `itemid = 223835`, the derived CTE `valuenum` is assigned as follows:

- `valuenum >= 0.20 AND valuenum <= 1`: output `valuenum * 100`.
- `valuenum > 1 AND valuenum < 20`: output `NULL`.
- `valuenum >= 20 AND valuenum <= 100`: output the original `valuenum`.
- Otherwise, including values outside those ranges and a NULL source
  `valuenum`, output `NULL`.

These are value-cleaning branches, not row filters: the source row remains in
the grouped result even when its cleaned numeric value is NULL.

### PEEP cleaning (lines 24-30)

For `itemid IN (220339, 224700)`, the derived CTE `valuenum` is assigned as
follows:

- `valuenum > 100`: output `NULL`.
- `valuenum < 0`: output `NULL`.
- Otherwise, output the original `valuenum` (which is also NULL when the
  source is NULL).

Again, the branches null the value, not the row.

### Other items (line 31)

For every other item in the filtered set, the derived CTE `valuenum` is the
source `valuenum` unchanged. The source `value` is retained unchanged for the
textual pivot branches.

## Literal code specification

The source table filtered by every code set below is
`mimiciv_icu.chartevents`. The following is the `itemid` set verbatim from the
SQL, in its source order; the comments are retained only as source annotations
and do not replace the numeric codes:

```text
224688 -- Respiratory Rate (Set)
, 224689 -- Respiratory Rate (spontaneous)
, 224690 -- Respiratory Rate (Total)
, 224687 -- minute volume
, 224685, 224684, 224686 -- tidal volume
, 224696 -- PlateauPressure
, 220339, 224700 -- PEEP
, 223835 -- fio2
, 223849 -- vent mode
, 229314 -- vent mode (Hamilton)
, 223848 -- vent type
, 224691 -- Flow Rate (L)
```

The exact code-to-CTE/output feeds are:

| Exact `itemid` literal(s) | CTE branch/feed | Final output column(s) fed |
|---|---|---|
| `224688` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224688` | `respiratory_rate_set` |
| `224689` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224689` | `respiratory_rate_spontaneous` |
| `224690` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224690` | `respiratory_rate_total` |
| `224687` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224687` | `minute_volume` |
| `224685` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224685` | `tidal_volume_observed` |
| `224684` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224684` | `tidal_volume_set` |
| `224686` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224686` | `tidal_volume_spontaneous` |
| `224696` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224696` | `plateau_pressure` |
| `220339, 224700` | CTE PEEP-cleaning branch; outer `CASE WHEN itemid IN (220339, 224700)` | `peep` |
| `223835` | CTE FIO2-cleaning branch; outer `CASE WHEN itemid = 223835` | `fio2` |
| `223849` | `ce.value` unchanged; outer `CASE WHEN itemid = 223849` | `ventilator_mode` |
| `229314` | `ce.value` unchanged; outer `CASE WHEN itemid = 229314` | `ventilator_mode_hamilton` |
| `223848` | `ce.value` unchanged; outer `CASE WHEN itemid = 223848` | `ventilator_type` |
| `224691` | `ce.valuenum` unchanged; outer `CASE WHEN itemid = 224691` | `flow_rate` |

The code literals `223835`, `220339`, and `224700` are each used both in the
row-selection code set and in their corresponding cleaning/pivot discriminator
branches. No other coded system, ICD code, or `mimiciv_derived` code is named.

## Final output columns and inferred types

| Output column | SQL expression | Inferred type | Meaning of SQL operation |
|---|---|---|---|
| `subject_id` | `subject_id` | `INTEGER` | Grouping key and direct grouped value. |
| `stay_id` | `MAX(stay_id)` | `INTEGER` | Maximum non-NULL filtered stay ID in the `(subject_id, charttime)` group. |
| `charttime` | `charttime` | `TIMESTAMP` | Grouping key and direct grouped value. |
| `respiratory_rate_set` | `MAX(CASE WHEN itemid = 224688 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum cleaned numeric value for item `224688`. |
| `respiratory_rate_total` | `MAX(CASE WHEN itemid = 224690 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum cleaned numeric value for item `224690`. |
| `respiratory_rate_spontaneous` | `MAX(CASE WHEN itemid = 224689 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum cleaned numeric value for item `224689`. |
| `minute_volume` | `MAX(CASE WHEN itemid = 224687 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224687`. |
| `tidal_volume_set` | `MAX(CASE WHEN itemid = 224684 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224684`. |
| `tidal_volume_observed` | `MAX(CASE WHEN itemid = 224685 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224685`. |
| `tidal_volume_spontaneous` | `MAX(CASE WHEN itemid = 224686 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224686`. |
| `plateau_pressure` | `MAX(CASE WHEN itemid = 224696 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224696`. |
| `peep` | `MAX(CASE WHEN itemid IN (220339, 224700) THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum cleaned numeric value across items `220339` and `224700`. |
| `fio2` | `MAX(CASE WHEN itemid = 223835 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum FIO2-cleaned numeric value for item `223835`. |
| `flow_rate` | `MAX(CASE WHEN itemid = 224691 THEN valuenum ELSE NULL END)` | `FLOAT` | Maximum numeric value for item `224691`. |
| `ventilator_mode` | `MAX(CASE WHEN itemid = 223849 THEN value ELSE NULL END)` | `VARCHAR(200)` | Lexicographic maximum source text for item `223849`. |
| `ventilator_mode_hamilton` | `MAX(CASE WHEN itemid = 229314 THEN value ELSE NULL END)` | `VARCHAR(200)` | Lexicographic maximum source text for item `229314`. |
| `ventilator_type` | `MAX(CASE WHEN itemid = 223848 THEN value ELSE NULL END)` | `VARCHAR(200)` | Lexicographic maximum source text for item `223848`. |

Item-specific aggregate outputs can be NULL when their item-specific branch has
no non-NULL aggregate value in a group. Under the `stay_id IS NOT NULL`
predicate, the `MAX(stay_id)` output is non-NULL. The query does not emit
`valueuom` or `storetime`.

## Joins and dependencies

- Joins: none. There are no INNER or LEFT joins and therefore no join
  conditions.
- `mimiciv_derived` dependencies: none. The CTE `ce` is local to this SQL and
  reads only `mimiciv_icu.chartevents`.
- DAG dependency status: the empty dependency list is consistent with the
  SQL. `ventilation` is a downstream dependent, not an input dependency.

## Aggregations and temporal logic

- `GROUP BY subject_id, charttime` at line 93.
- `MAX(stay_id)` at line 56.
- Numeric `MAX` pivots at lines 58-86.
- Text `MAX` pivots at lines 87-91.
- No `MIN`, `AVG`, `SUM`, `ARRAY_AGG`, `DISTINCT`, window function, `ORDER BY`,
  or subquery-level aggregation other than the final grouped pivot.
- There is no temporal range/window predicate, interval arithmetic, temporal
  carry-forward, or chronological ordering. `charttime` is used only as an
  exact equality/grouping key and is emitted unchanged. `storetime` is selected
  by the CTE but is not used to choose a row or an aggregate value.

The chartevents notes read for context record that itemid-derived Observation
codes retain the source itemid, that chartevents resources can repeat at one
stay/time, and that the FHIR ETL can normalize DST-gap effective times. Those
facts concern a later FHIR representation; the canonical SQL itself groups on
the source `charttime` and applies its `MAX` pivots without any such
normalization or recovery logic.

## Semantically essential source inputs

These are the source fields/discriminators whose values can alter inclusion,
the natural key/grouping, or a clinically meaningful derived output:

1. **`subject_id`** — controls the first component of the output natural key
   and therefore which source rows are aggregated together; it is also emitted
   as `subject_id`.
2. **`charttime`** — controls the second component of the output natural key,
   partitions the exact-time pivot groups, and is emitted as `charttime`. There
   is no time carry-forward or range membership; a changed charttime changes
   grouping and the output time.
3. **`stay_id`** — `IS NOT NULL` controls row inclusion and `MAX(stay_id)`
   controls the output `stay_id`. Because it is not grouped, multiple stay IDs
   for a subject/time are represented by the maximum one rather than separate
   output rows.
4. **`itemid`** — controls row inclusion through the exact literal set,
   selects FIO2/PEEP cleaning branches, selects numeric versus textual pivot
   branches, and determines which final output column receives a row. It is
   therefore both a row discriminator and a clinically meaningful output
   discriminator.
5. **`value`** — `value IS NOT NULL` controls row inclusion for every selected
   item. Its text feeds `ventilator_mode`, `ventilator_mode_hamilton`, and
   `ventilator_type`; those outputs use `MAX(value)` within the time group.
6. **`valuenum`** — supplies every numeric output. For item `223835` it can be
   converted from a fraction to a percentage or nulled; for items `220339` and
   `224700` it can be nulled when outside the PEEP bounds; for other selected
   items it passes through. The cleaned result is then aggregated with `MAX`
   into the numeric output columns.

The following CTE inputs are **not** semantically used by the final result:
`valueuom` and `storetime` are selected but never projected, filtered,
grouped, ordered, or aggregated. There is consequently no source-unit
discriminator and no store-time tie-breaking logic in this concept.
