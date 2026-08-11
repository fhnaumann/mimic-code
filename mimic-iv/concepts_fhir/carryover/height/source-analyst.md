# Source Analysis: `height`

**Concept:** `height`

**Canonical SQL:** `mimic-iv/concepts/measurement/height.sql`

**DAG node:** stem `height`, path `measurement/height.sql`, level 0,
SHA256 `9b024d54f770b9a8e1f1ac0afe84fe5918295155eaa95872a849ef112c76d492`.
The hash was checked against the SQL file on disk.

**DAG dependencies:** none. The SQL does not reference `mimiciv_derived`.
The DAG lists `first_day_height` as a dependent, not as a dependency of this
concept.

**Oracle shape metadata:** the full oracle manifest records four output columns,
33,474 rows, `comparison: keyed_join`, and empirical natural key `stay_id`.
The manifest types are `INTEGER`, `INTEGER`, `TIMESTAMP`, and `DECIMAL(38,2)`
for the columns below, respectively. The key is empirical metadata from the
full oracle; it is not declared or enforced by this SQL.

## 1. Table references

| # | Schema | Table | Alias | Used in | Role |
|---|---|---|---|---|---|
| 1 | `mimiciv_icu` | `chartevents` | `c` | `ht_in` | Source rows for the inches stream; filtered to itemid `226707` |
| 2 | `mimiciv_icu` | `chartevents` | `c` | `ht_cm` | Source rows for the centimetres stream; filtered to itemid `226730` |

The source text qualifies these as
``physionet-data.mimiciv_icu.chartevents``; the physical MIMIC schema/table
reference is `mimiciv_icu.chartevents`. There are no references to
`mimiciv_hosp` tables, dimension tables such as `d_items`, or any
`mimiciv_derived` table. `ht_cm` and `ht_in` in the final CTE are CTE
references, not additional physical tables.

The relevant `chartevents` source types from the MIMIC-IV DDL are:

| Source column | DDL type | Use |
|---|---|---|
| `subject_id` | `INTEGER NOT NULL` | Selected, coalesced, and output |
| `stay_id` | `INTEGER NOT NULL` | Selected, coalesced, and output; omitted from the join condition |
| `charttime` | `TIMESTAMP NOT NULL` | Selected, coalesced, and used in the join condition |
| `itemid` | `INTEGER NOT NULL` | Coded stream discriminator in each source CTE |
| `valuenum` | `FLOAT` | Null filter, numeric conversion, and intermediate `height_orig` |

Other `chartevents` columns (`hadm_id`, `caregiver_id`, `storetime`, `value`,
`valueuom`, and `warning`) are not referenced.

## 2. CTEs and column flow

### `ht_in` — height charted in inches (SQL lines 2–12)

Reads `mimiciv_icu.chartevents c` and selects:

| Column | Inferred type | Expression / purpose |
|---|---|---|
| `subject_id` | `INTEGER` | `c.subject_id` |
| `stay_id` | `INTEGER` | `c.stay_id` |
| `charttime` | `TIMESTAMP` | `c.charttime` |
| `height` | `NUMERIC`/`DECIMAL`, rounded to 2 decimal places | `ROUND(CAST(c.valuenum * 2.54 AS NUMERIC), 2)`; converts inches to centimetres |
| `height_orig` | `FLOAT` | `c.valuenum`; retained only inside this CTE and not propagated |

The source `valuenum` is required to be non-null and the row must have itemid
`226707`. The `2.54` factor is a scalar conversion; it is not an aggregation.

### `ht_cm` — height charted in centimetres (SQL lines 14–23)

Reads `mimiciv_icu.chartevents c` and selects:

| Column | Inferred type | Expression / purpose |
|---|---|---|
| `subject_id` | `INTEGER` | `c.subject_id` |
| `stay_id` | `INTEGER` | `c.stay_id` |
| `charttime` | `TIMESTAMP` | `c.charttime` |
| `height` | `NUMERIC`/`DECIMAL`, rounded to 2 decimal places | `ROUND(CAST(c.valuenum AS NUMERIC), 2)` |

The source `valuenum` is required to be non-null and the row must have itemid
`226730`.

### `ht_stg0` — merge the two streams (SQL lines 26–36)

The CTE selects four coalesced columns:

| Column | Inferred type | Expression |
|---|---|---|
| `subject_id` | `INTEGER`, nullable at the outer-join stage | `COALESCE(h1.subject_id, h2.subject_id)` |
| `stay_id` | `INTEGER`, nullable at the outer-join stage | `COALESCE(h1.stay_id, h2.stay_id)` |
| `charttime` | `TIMESTAMP`, nullable at the outer-join stage | `COALESCE(h1.charttime, h2.charttime)` |
| `height` | `NUMERIC`/`DECIMAL`, rounded to 2 places | `COALESCE(h1.height, h2.height)` |

`height_orig` is deliberately not selected into `ht_stg0`. In an inner match,
the centimetre row (`h1`, from `ht_cm`) has precedence because its non-null
`height` is the first argument to `COALESCE`; the inches value (`h2`) is used
only when no centimetre value is present on the joined row.

## 3. Final output and types

The final query (SQL lines 38–42) selects, in this order:

| # | Output column | Source expression | Oracle manifest type |
|---|---|---|---|
| 1 | `subject_id` | `ht_stg0.subject_id` | `INTEGER` |
| 2 | `stay_id` | `ht_stg0.stay_id` | `INTEGER` |
| 3 | `charttime` | `ht_stg0.charttime` | `TIMESTAMP` |
| 4 | `height` | `ht_stg0.height` | `DECIMAL(38,2)` |

The final `height` is always intended to be in centimetres and is rounded to
two decimal places. There is no output unit, original-value, itemid, `hadm_id`,
or source `value` column.

## 4. Filters

All predicates in the canonical SQL are:

1. `ht_in`: `c.valuenum IS NOT NULL`.
2. `ht_in`: `c.itemid = 226707` (commented as height measured in inches).
3. `ht_cm`: `c.valuenum IS NOT NULL`.
4. `ht_cm`: `c.itemid = 226730` (commented as height in cm).
5. Final query: `height IS NOT NULL`.
6. Final query: `height > 120`.
7. Final query: `height < 230`.

The final bounds are strict: exactly `120` and exactly `230` are excluded, as
are NULLs and values outside the open interval `(120, 230)` centimetres. There
are no time-window predicates, admission/stay-window predicates, `hadm_id`
predicates, unit predicates, value-string predicates, or coded exclusions
beyond the two exact itemid predicates.

The `height IS NOT NULL` predicate is applied after the full outer join and
coalescing. Given the source `valuenum IS NOT NULL` filters, each computed
component height is normally non-null, but this source predicate is still part
of the specification and must be retained.

## 5. Joins

There is one physical-data join expressed through the two source CTEs:

```sql
FROM ht_cm h1
FULL OUTER JOIN ht_in h2
  ON h1.subject_id = h2.subject_id
 AND h1.charttime = h2.charttime
```

- **Type:** `FULL OUTER JOIN`.
- **Left input:** `ht_cm h1`, sourced from `mimiciv_icu.chartevents` itemid
  `226730`.
- **Right input:** `ht_in h2`, sourced from `mimiciv_icu.chartevents` itemid
  `226707`.
- **Join keys:** `subject_id` and `charttime`, equality on both.
- **Not a join key:** `stay_id` is selected and coalesced, but is *not* part
  of the `ON` condition.

The full join preserves unmatched centimetre and inches rows. It does not
deduplicate or aggregate. If multiple rows exist on either side for the same
`subject_id`/`charttime`, matching rows can fan out. If matched rows have
different `stay_id` values, the emitted `stay_id` is the centimetre-side value
because of `COALESCE(h1.stay_id, h2.stay_id)`. If a centimetre row exists at a
matching key, its computed height also wins over the inches-side height,
regardless of whether the centimetre value later fails the final plausibility
filter.

## 6. Aggregations and transformations

- No `GROUP BY`.
- No aggregate functions (`MIN`, `MAX`, `AVG`, `ARRAY_AGG`, etc.).
- No window functions.
- Scalar transformations only: inches-to-centimetres multiplication by
  `2.54`, `CAST(... AS NUMERIC)`, `ROUND(..., 2)`, and `COALESCE`.

## 7. Literal code specification

The source names one proprietary ICU `chartevents.itemid` per height unit. The
codes are copied verbatim and are not translated, normalized, or expanded.

| Source table and column | Exact SQL literal | Predicate | Feeds |
|---|---:|---|---|
| `mimiciv_icu.chartevents.itemid` | `226707` | `c.itemid = 226707` in `ht_in` | `ht_in.height` (converted cm), `ht_in.height_orig`, `ht_in.subject_id`, `ht_in.stay_id`, `ht_in.charttime`; then the inches-side inputs to `ht_stg0` and final `height` |
| `mimiciv_icu.chartevents.itemid` | `226730` | `c.itemid = 226730` in `ht_cm` | `ht_cm.height` (rounded cm), `ht_cm.subject_id`, `ht_cm.stay_id`, `ht_cm.charttime`; then the centimetre-side inputs to `ht_stg0` and final `height` |

No ICD, LOINC, or other standard code is named by the canonical SQL, and no
coding-system URI is present in it. The source coding discriminator is the
integer MIMIC ICU `chartevents.itemid`; the downstream FHIR policy must retain
these exact values rather than substitute labels.

No coded filter is identifiable as a dead filter from the SQL text alone; both
itemids are present-in-SQL specifications. No code was omitted or inferred.

## 8. Natural-key implications

The SQL does not declare a primary key, `DISTINCT`, `GROUP BY`, or window-based
deduplication. Its logical row source is the filtered chart-event streams
merged at `(subject_id, charttime)`, with the caveats about possible join
fan-out and centimetre-side precedence above.

For comparison, the immutable full oracle manifest reports:

- empirical key: `stay_id` only;
- comparison: `keyed_join`;
- row count: `33,474`;
- `charttime` is an output attribute but is not part of the manifest key.

This `stay_id` key must be treated as manifest metadata discovered from full
data, not as a uniqueness guarantee derivable from the source SQL. A candidate
must preserve all four output columns and the source join semantics; it must
not add `stay_id` to the source join merely because it appears in the output.

## Summary

`height` is a level-0, dependency-free two-stream ICU chart-event derivation.
It reads `mimiciv_icu.chartevents` twice, converts itemid `226707` from inches
to centimetres, rounds itemid `226730` centimetres, full-outer-merges the
streams on patient and chart time (not stay), and emits only heights strictly
between 120 and 230 cm as `(subject_id, stay_id, charttime, height)` with
manifest types `(INTEGER, INTEGER, TIMESTAMP, DECIMAL(38,2))`.
