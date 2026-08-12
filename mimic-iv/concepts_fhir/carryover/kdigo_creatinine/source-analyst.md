# Source analysis: `kdigo_creatinine`

## Source identity and DAG position

- Canonical SQL: `mimic-iv/concepts/organfailure/kdigo_creatinine.sql`
- DAG-resolved path: `organfailure/kdigo_creatinine.sql`
- DAG level: `0`
- DAG SHA256: `a7daeaf1c58c6f3b6a3f6fb0e8b7623e1b922123451ee485cc93bb4beb8b30b4`
- Checked SHA256: `a7daeaf1c58c6f3b6a3f6fb0e8b7623e1b922123451ee485cc93bb4beb8b30b4`
- DAG dependencies: none (`dependencies: []`). The SQL has no reference to
  `mimiciv_derived` and therefore has no derived-concept prerequisite. The DAG
  lists `kdigo_stages` as a dependent, not as a dependency of this concept.

The source SQL uses BigQuery-style fully qualified names with the project
prefix `physionet-data`. The schema/table names below omit that project prefix
when identifying the MIMIC schema.

## Table and relation references

### Physical tables

| SQL reference | Schema | Table | Alias | Role |
|---|---|---|---|---|
| `` `physionet-data.mimiciv_icu.icustays` ie `` | `mimiciv_icu` | `icustays` | `ie` | ICU-stay driving relation in `cr`; supplies stay/admission identifiers and ICU time bounds |
| `` `physionet-data.mimiciv_hosp.labevents` le `` | `mimiciv_hosp` | `labevents` | `le` | Laboratory creatinine observations joined to each ICU stay |

There are no references to any other `mimiciv_hosp` or `mimiciv_icu` table,
and no reference to `mimiciv_derived`.

### CTE relations

The following `FROM`/`JOIN` clauses refer to CTEs rather than physical tables:

| CTE | Clause | Join type and condition |
|---|---|---|
| `cr48` | `FROM cr` | Drives one row for each `cr.stay_id, cr.charttime` group |
| `cr48` | `LEFT JOIN cr cr48` | `cr.stay_id = cr48.stay_id AND cr48.charttime < cr.charttime AND cr48.charttime >= DATETIME_SUB(cr.charttime, INTERVAL '48' HOUR)` |
| `cr7` | `FROM cr` | Drives one row for each `cr.stay_id, cr.charttime` group |
| `cr7` | `LEFT JOIN cr cr7` | `cr.stay_id = cr7.stay_id AND cr7.charttime < cr.charttime AND cr7.charttime >= DATETIME_SUB(cr.charttime, INTERVAL '7' DAY)` |
| final `SELECT` | `FROM cr` | One output row per `cr` row before the two enrichment joins |
| final `SELECT` | `LEFT JOIN cr48` | `cr.stay_id = cr48.stay_id AND cr.charttime = cr48.charttime` |
| final `SELECT` | `LEFT JOIN cr7` | `cr.stay_id = cr7.stay_id AND cr.charttime = cr7.charttime` |

All CTE joins and final enrichment joins are `LEFT JOIN`s. There is no
`INNER JOIN` in this SQL.

## Columns and inferred types

Types are inferred from the MIMIC-IV DDL and the expressions in the SQL. The
canonical DDL declares `icustays` identifiers as `INTEGER`, ICU times as
`TIMESTAMP`, `labevents.charttime` as `TIMESTAMP(0)`, and `labevents.valuenum`
as `DOUBLE PRECISION`.

### Physical columns referenced

| Source column | Inferred type | Use |
|---|---|---|
| `mimiciv_icu.icustays.subject_id` (`ie.subject_id`) | `INTEGER` | Join key to `le.subject_id`; not selected in the output |
| `mimiciv_icu.icustays.hadm_id` (`ie.hadm_id`) | `INTEGER` | Selected into `cr`; grouped; final `hadm_id` output |
| `mimiciv_icu.icustays.stay_id` (`ie.stay_id`) | `INTEGER` | Selected into `cr`; grouping, temporal self-joins, final `stay_id` output |
| `mimiciv_icu.icustays.intime` (`ie.intime`) | `TIMESTAMP` | Lower bound of the initial seven-day lab window |
| `mimiciv_icu.icustays.outtime` (`ie.outtime`) | `TIMESTAMP` | Inclusive upper bound of the initial lab window |
| `mimiciv_hosp.labevents.subject_id` (`le.subject_id`) | `INTEGER` | Join key to `ie.subject_id`; not selected in the output |
| `mimiciv_hosp.labevents.itemid` (`le.itemid`) | `INTEGER` | Exact coded filter `= 50912`; selects creatinine lab rows |
| `mimiciv_hosp.labevents.valuenum` (`le.valuenum`) | `DOUBLE PRECISION` / `DOUBLE` | Non-null and upper-bound filters; input to `AVG` |
| `mimiciv_hosp.labevents.charttime` (`le.charttime`) | `TIMESTAMP` | Selected and grouped in `cr`; output event time and temporal-window basis |

The SQL does **not** reference `labevents.hadm_id`, `labevent_id`,
`specimen_id`, `value`, `valueuom`, `storetime`, reference ranges, flags,
priority, comments, or any other labevents column.

### Intermediate CTE columns

#### `cr`

```text
hadm_id  INTEGER       = ie.hadm_id
stay_id  INTEGER       = ie.stay_id
charttime TIMESTAMP    = le.charttime
creat    DOUBLE        = AVG(le.valuenum)
```

`cr` is grouped by `ie.hadm_id, ie.stay_id, le.charttime`, so its intended
measurement grain is one row per ICU stay and lab chart time after averaging
all qualifying item `50912` values at that time. Because the driving join is a
`LEFT JOIN`, an ICU stay with no qualifying lab row can also produce a grouped
row with a null `charttime` and null `creat`.

#### `cr48`

```text
stay_id              INTEGER    = cr.stay_id
charttime            TIMESTAMP  = cr.charttime
creat_low_past_48hr  DOUBLE     = MIN(cr48.creat)
```

`creat_low_past_48hr` is nullable. The self-join only admits strictly earlier
measurements in the interval `[cr.charttime - 48 hours, cr.charttime)`, so the
current creatinine is excluded and the lower endpoint is included.

#### `cr7`

```text
stay_id             INTEGER    = cr.stay_id
charttime           TIMESTAMP  = cr.charttime
creat_low_past_7day DOUBLE     = MIN(cr7.creat)
```

`creat_low_past_7day` is nullable. The self-join only admits strictly earlier
measurements in `[cr.charttime - 7 days, cr.charttime)`, again excluding the
current measurement and including the lower endpoint.

### Final output schema

The final `SELECT` emits exactly six columns, in this order:

| Output column | Inferred/manifest type | Expression | Nullability/meaning |
|---|---|---|---|
| `hadm_id` | `INTEGER` | `cr.hadm_id` | ICU stay's hospital admission identifier |
| `stay_id` | `INTEGER` | `cr.stay_id` | ICU stay identifier |
| `charttime` | `TIMESTAMP` | `cr.charttime` | Creatinine measurement/group time; can be null on the unmatched left-join row |
| `creat` | `DOUBLE` | `cr.creat` | Average qualifying creatinine at the stay/time |
| `creat_low_past_48hr` | `DOUBLE` | `cr48.creat_low_past_48hr` | Minimum qualifying prior creatinine in the preceding 48-hour window |
| `creat_low_past_7day` | `DOUBLE` | `cr7.creat_low_past_7day` | Minimum qualifying prior creatinine in the preceding seven-day window |

The oracle manifest records this exact six-column schema and reports
`comparison: full_tuple_multiset` with `key: null` (no authoritative natural
key selected for comparison). The SQL's logical non-null measurement grain is
`(stay_id, charttime)`; `hadm_id` is also grouped in `cr`, and the final
baseline joins use only `(stay_id, charttime)`. Do not treat the manifest as
endorsing a keyed comparison: the authoritative comparison is the full tuple
multiset. The SQL has no explicit primary-key declaration.

## Filters and time windows

There is no `WHERE` clause in the file. Every initial-row restriction is part
of the `ON` predicate of the `ie LEFT JOIN le`:

```sql
ie.subject_id = le.subject_id
AND le.itemid = 50912
AND le.valuenum IS NOT NULL
AND le.valuenum <= 150
AND le.charttime >= DATETIME_SUB(ie.intime, INTERVAL '7' DAY)
AND le.charttime <= ie.outtime
```

Semantically:

1. Match labevents to an ICU stay by `subject_id` only, subject to the other
   predicates.
2. Keep only the exact creatinine item `50912`.
3. Require a numeric `valuenum` and reject values greater than `150`.
   There is no lower value bound.
4. Keep lab chart times from seven days before ICU `intime` through ICU
   `outtime`, inclusive at both ends.
5. For each current measurement, the 48-hour and seven-day baseline joins use
   strict `prior.charttime < current.charttime` and inclusive lower bounds.

No patient/admission time window is applied outside the ICU-stay bounds, no
ICD or other code exclusion exists, and no null-handling predicate is applied
to `charttime` beyond ordinary SQL comparison behavior.

## Literal coding specification

The complete executable coded set contains one literal:

| Source table/column filtered | Exact SQL literal, verbatim | Predicate | Feeds |
|---|---:|---|---|
| `mimiciv_hosp.labevents.itemid` | `50912` | `le.itemid = 50912` | `cr.creat` via `AVG(le.valuenum)`, then final output column `creat`; the same filtered `cr` rows feed both baseline CTEs |

This is an `itemid` code from `mimiciv_hosp.labevents`; the source SQL names no
ICD code, LOINC code, code-system URI, or second itemid. The literal must not
be normalized, translated, expanded, or replaced by a label. The SQL's
`valuenum <= 150` predicate is a value constraint, not a coded filter.

## Aggregations and windows

- `cr`: `AVG(le.valuenum)` after the join filters, grouped by
  `ie.hadm_id, ie.stay_id, le.charttime`.
- `cr48`: `MIN(cr48.creat)`, grouped by `cr.stay_id, cr.charttime`, over a
  self-join restricted to the previous 48 hours.
- `cr7`: `MIN(cr7.creat)`, grouped by `cr.stay_id, cr.charttime`, over a
  self-join restricted to the previous seven days.
- There are no SQL window functions (`OVER`), no `ORDER BY`, no `UNION`, no
  `DISTINCT`, and no final aggregation.
- The interval calculations use the exact source expressions
  `DATETIME_SUB(ie.intime, INTERVAL '7' DAY)`,
  `DATETIME_SUB(cr.charttime, INTERVAL '48' HOUR)`, and
  `DATETIME_SUB(cr.charttime, INTERVAL '7' DAY)`.

## Join and cardinality implications for downstream mapping

The lab table is not joined through `labevents.hadm_id`; it is associated to
the ICU stay by `subject_id` plus the item/value/time predicates above. The
source then intentionally collapses all qualifying creatinine lab rows that
land at the same `(stay_id, charttime)` into one average. A downstream
reproduction must preserve that aggregation grain rather than emit one output
row per FHIR Observation or group by a lab specimen identifier. The two
baseline calculations are derived from the already-aggregated `cr` rows and
must remain left-preserving: absence of an earlier value yields a null minimum,
not removal of the current row.

## Relevant read-only dataset notes

The source-only review found no new dataset-wide quirk to append. Existing
notes that are relevant leads for later FHIR probing/implementation are:

- `MIMIC_NOTES.md`: labevents itemids are emitted verbatim in the proprietary
  labevents Observation coding system; no itemid-to-label translation is
  required or allowed.
- `MIMIC_NOTES.md`: lab Observation encounter references are incomplete. This
  source SQL does not use `labevents.hadm_id`, but a later port must not turn a
  missing FHIR encounter reference into row loss.
- `MIMIC_NOTES.md`: materialized Quantity-value aliases can be strings and
  require numeric casting before reproducing `AVG`, `MIN`, and `<= 150`.
- `MIMIC_NOTES.md` and the chemistry fragment: FHIR lab datetimes carry an
  offset and should be treated as MIMIC wall-clock values with
  `TIMESTAMP_NTZ`; the existing notes also document irreversible DST-gap
  normalization. These are downstream representation concerns, not changes to
  the canonical source SQL.

No new section is proposed for `MIMIC_NOTES.d/kdigo_creatinine.md` from this
source analysis alone; any dataset-wide claim discovered by the later prober
or full run belongs there as an append-only orchestrator finding.
