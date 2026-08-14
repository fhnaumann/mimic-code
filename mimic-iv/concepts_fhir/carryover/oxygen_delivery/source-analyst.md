# Source analysis: `oxygen_delivery`

## Source and DAG position

- Canonical SQL: `mimic-iv/concepts/measurement/oxygen_delivery.sql` (111
  lines).
- DAG node: `oxygen_delivery`, path `measurement/oxygen_delivery.sql`, level
  0, source SHA256
  `b3c9df45c64ac7364e98c8eba0ebf233dc153ffecdc8ad23bb4b9cea53bd2752`.
- The DAG declares **no `mimiciv_derived` dependencies** for this concept.
  `oxygen_delivery` is a dependency of `ventilation`; it is not a consumer of
  `ventilation` or any other derived concept.
- `uv run mimic_utils concept_dag --check` reported that the stored DAG matches
  the generated DAG, and `uv run mimic_utils depcheck oxygen_delivery` reported
  that its (empty) dependency set is met.

## Physical table references

The only physical table referenced by the canonical SQL is
`mimiciv_icu.chartevents` (the ICU schema, table `chartevents`). It is read
twice:

1. `ce_stg1` reads it as `ce` for flow itemids.
2. `o2` reads it directly for itemid `226732` device rows.

The other `FROM` references are CTE relations: `ce_stg2` reads `ce_stg1`, and
`stg` reads `ce_stg2` and `o2`. There are no `mimiciv_hosp` tables, no
dimension-table joins, and no `mimiciv_derived` table references.

The raw MIMIC-IV 2.2 schema, checked in
`mimic-iv/buildmimic/postgres/create.sql`, defines the relevant source columns
as:

| Source field | Inferred/raw type | Use in this SQL |
|---|---|---|
| `subject_id` | `INTEGER` | Partitioning, join, grouping, and final output |
| `stay_id` | `INTEGER` | Carried through the CTEs and final `MAX` output |
| `charttime` | `TIMESTAMP` | Partitioning, join, grouping, and final output |
| `itemid` | `INTEGER` | Item filter, flow-code merge, pivot discriminator |
| `value` | `VARCHAR(200)` | Non-NULL flow-row filter, device output, device tie-break |
| `valuenum` | `FLOAT` | Flow output and flow-row tie-break |
| `valueuom` | `VARCHAR(20)` | Selected in `ce_stg1`/`ce_stg2` but not used in the final result |
| `storetime` | `TIMESTAMP` | Recency/tie-break ordering in both window functions |

## CTE column flow and types

### `ce_stg1`

`ce_stg1` selects from `mimiciv_icu.chartevents AS ce`:

- `subject_id` (`INTEGER`)
- `stay_id` (`INTEGER`)
- `charttime` (`TIMESTAMP`)
- `itemid` (`INTEGER`), computed as:
  `CASE WHEN itemid IN (223834, 227582) THEN 223834 ELSE itemid END`
- `value` (`VARCHAR(200)`)
- `valuenum` (`FLOAT`)
- `valueuom` (`VARCHAR(20)`)
- `storetime` (`TIMESTAMP`)

It retains only non-NULL `value` rows whose source itemid is in the flow code
set. The `itemid` expression intentionally merges source itemids `223834`
and `227582` into the derived itemid `223834`; `227287` remains distinct.

### `ce_stg2`

`ce_stg2` reads `ce_stg1` and selects:

- `subject_id` (`INTEGER`)
- `stay_id` (`INTEGER`)
- `charttime` (`TIMESTAMP`)
- merged `itemid` (`INTEGER`)
- `value` (`VARCHAR(200)`)
- `valuenum` (`FLOAT`)
- `valueuom` (`VARCHAR(20)`)
- `rn` (integer row-number type, typically `BIGINT`/`INT64`)

`storetime` is not projected, but it is referenced by the window ordering. The
window is `ROW_NUMBER() OVER (PARTITION BY subject_id, charttime, itemid
ORDER BY storetime DESC, valuenum DESC)`. Since the normalized itemid is used
in the partition, `223834` and `227582` compete for one selected flow row at a
given subject/time. `stay_id` is notably absent from this partition.

### `o2`

`o2` reads `mimiciv_icu.chartevents` and selects:

- `subject_id` (`INTEGER`)
- `stay_id` (`INTEGER`)
- `charttime` (`TIMESTAMP`)
- `itemid` (`INTEGER`, always source itemid `226732` here)
- `o2_device` (`VARCHAR(200)`, the source `value`)
- `rn` (integer row-number type, typically `BIGINT`/`INT64`)

Its window is
`ROW_NUMBER() OVER (PARTITION BY subject_id, charttime, itemid ORDER BY
storetime DESC NULLS LAST, value DESC NULLS LAST)`. Unlike `ce_stg1`, this CTE
does not filter `value IS NOT NULL`. It retains all device rows and assigns a
rank; the final projection only consumes ranks 1 through 4.

### `stg`

`stg` reads `ce_stg2 AS ce FULL OUTER JOIN o2` and selects:

- `COALESCE(ce.subject_id, o2.subject_id)` as `subject_id` (`INTEGER`)
- `COALESCE(ce.stay_id, o2.stay_id)` as `stay_id` (`INTEGER`)
- `COALESCE(ce.charttime, o2.charttime)` as `charttime` (`TIMESTAMP`)
- `COALESCE(ce.itemid, o2.itemid)` as `itemid` (`INTEGER`)
- `ce.value` (`VARCHAR(200)`)
- `ce.valuenum` (`FLOAT`)
- `o2.o2_device` (`VARCHAR(200)`)
- `o2.rn` (integer row-number type)

The `ce.rn` column is referenced by the `WHERE` predicate but is not selected
into `stg`.

## Join

There is one physical-table join, represented in `stg` as a **FULL OUTER JOIN**:

```sql
FULL OUTER JOIN o2
  ON ce.subject_id = o2.subject_id
 AND ce.charttime = o2.charttime
```

The join does **not** compare `stay_id`. The subsequent `WHERE ce.rn = 1`
removes every o2-only row because `ce.rn` is NULL on the right-only side.
Therefore, despite the declared FULL OUTER JOIN, the surviving result is
ce-driven: a device row contributes only when its `(subject_id, charttime)`
matches a selected flow row. A selected flow row with no device match remains,
with device fields NULL. Multiple device rows at a matching subject/time fan
out against the selected flow rows and are subsequently pivoted by device
rank.

## Filters and predicates

### `ce_stg1` filters

```sql
WHERE ce.value IS NOT NULL
  AND ce.itemid IN
  (
      223834
      , 227582
      , 227287
  )
```

The filter is only a non-NULL text-value check plus the exact flow itemid set;
there is no time window, unit/value-range constraint, admission constraint, or
numeric `valuenum IS NOT NULL` predicate.

### `o2` filter

```sql
WHERE itemid = 226732
```

There is no `value IS NOT NULL` predicate in this CTE.

### `stg` filter

```sql
WHERE ce.rn = 1
```

This retains only the highest-ranked flow row for each normalized
`(subject_id, charttime, itemid)` group and, as described above, eliminates
right-only device rows from the FULL OUTER JOIN.

There is no final `WHERE` clause. There are no time windows, value limits,
regular-expression predicates, code exclusions, or joins to `d_items`.

## Exact literal code specification

All listed codes filter the single source table `mimiciv_icu.chartevents`.
They are source `itemid` values and must be treated as exact literals; the
canonical query does not use labels or a terminology translation.

| Exact SQL literal(s) | Predicate/operation | Source table | Feeds |
|---|---|---|---|
| `223834, 227582, 227287` | `ce.itemid IN (...)` in `ce_stg1` | `mimiciv_icu.chartevents` | Flow-row population of `ce_stg1`, then the final flow outputs |
| `223834, 227582` | `WHEN itemid IN (223834, 227582) THEN 223834` | `mimiciv_icu.chartevents` | Merged `ce_stg1.itemid`; both source codes feed final `o2_flow` via itemid `223834` |
| `226732` | `WHERE itemid = 226732` in `o2` | `mimiciv_icu.chartevents` | `o2.o2_device`, then `o2_delivery_device_1` through `_4` |
| `223834` | `CASE WHEN itemid = 223834 THEN valuenum` | `mimiciv_icu.chartevents` via `ce_stg1`/`stg` | Final `o2_flow` |
| `227287` | `CASE WHEN itemid = 227287 THEN valuenum` | `mimiciv_icu.chartevents` via `ce_stg1`/`stg` | Final `o2_flow_additional` |

Verbatim active code literals from the canonical SQL are:

```sql
WHEN itemid IN (223834, 227582) THEN 223834

AND ce.itemid IN
(
    223834 -- o2 flow
    , 227582 -- bipap o2 flow
    , 227287 -- additional o2 flow
)

WHERE itemid = 226732 -- oxygen delivery device(s)

CASE WHEN itemid = 223834 THEN valuenum ELSE NULL END
CASE WHEN itemid = 227287 THEN valuenum ELSE NULL END
```

The commented-out `224691` (“Flow Rate (L)”) is explicitly described as not
oxygen flow but is **not an executable filter** and is not part of the code
specification. The other itemids in the explanatory comment in `o2` are also
comments, not active filters.

## Aggregations and windows

The query has two window functions:

1. `ce_stg2`: `ROW_NUMBER()` partitioned by
   `(subject_id, charttime, normalized itemid)`, ordered by `storetime DESC,
   valuenum DESC`.
2. `o2`: `ROW_NUMBER()` partitioned by
   `(subject_id, charttime, itemid)`, ordered by `storetime DESC NULLS LAST,
   value DESC NULLS LAST`.

The final query groups by exactly `(subject_id, charttime)` and computes:

- `MAX(stay_id)` as `stay_id`;
- `MAX(CASE WHEN itemid = 223834 THEN valuenum ELSE NULL END)` as `o2_flow`;
- `MAX(CASE WHEN itemid = 227287 THEN valuenum ELSE NULL END)` as
  `o2_flow_additional`;
- `MAX(CASE WHEN rn = 1/2/3/4 THEN o2_device ELSE NULL END)` as the four
  device-slot columns.

There is no `MIN`, `AVG`, `SUM`, `ARRAY_AGG`, or other aggregation. The query
does not group by `stay_id`; it takes the maximum stay id among rows in each
subject/time group.

## Final output schema and grain

The final columns, in order, are:

| Output column | Inferred type | Meaning produced by the SQL |
|---|---|---|
| `subject_id` | `INTEGER` | Grouping patient identifier |
| `stay_id` | `INTEGER` | `MAX(stay_id)` within the patient/time group |
| `charttime` | `TIMESTAMP` | Grouping/chart timestamp |
| `o2_flow` | `FLOAT` | Selected numeric flow for source `223834` or merged `227582` |
| `o2_flow_additional` | `FLOAT` | Selected numeric flow for source `227287` |
| `o2_delivery_device_1` | `VARCHAR`/`STRING` | Ranked device value for `o2.rn = 1` |
| `o2_delivery_device_2` | `VARCHAR`/`STRING` | Ranked device value for `o2.rn = 2` |
| `o2_delivery_device_3` | `VARCHAR`/`STRING` | Ranked device value for `o2.rn = 3` |
| `o2_delivery_device_4` | `VARCHAR`/`STRING` | Ranked device value for `o2.rn = 4` |

The result grain is one row per `(subject_id, charttime)` after the final
`GROUP BY`. This pair is the SQL-defined natural key. `stay_id` is an output
attribute, not part of the key. The source `stay_id` can therefore affect the
output through `MAX`, but it does not define a partition, join, or group.

The device slots are not source rows: they are a ranked pivot of up to four
`226732` rows. Rows with ranks above 4 are not emitted into any output column.
The rank is determined first by latest `storetime`, then descending text
`value` with NULLs last. Flow rows are reduced to one row per normalized item
per subject/time before the final pivot.

## Semantically essential source inputs

These fields/discriminators can change inclusion, keys, grouping, row choice,
or a clinically meaningful output:

- `subject_id`: controls both window partitions, the FULL OUTER JOIN, and the
  final natural key; it scopes all output rows.
- `charttime`: controls both window partitions, the join, and final grouping;
  it is the temporal key for every output column.
- `itemid`: controls flow-row inclusion, merges `223834` and `227582`, selects
  `o2_flow` versus `o2_flow_additional`, and selects the `226732` device stream.
- `value`: non-NULL `value` controls inclusion in the flow branch; for item
  `226732`, its text is the clinically meaningful device output and also the
  secondary device-ranking discriminator.
- `valuenum`: supplies both numeric flow outputs and the secondary tie-break
  for flow rows. A non-NULL `value` is sufficient for flow-row inclusion even
  when `valuenum` is NULL, in which case the numeric output can remain NULL.
- `storetime`: primary recency discriminator in both `ROW_NUMBER()` windows;
  it determines which duplicate flow value survives and which device occupies
  each output slot.
- `stay_id`: does not control selection or grouping, but changes the final
  `MAX(stay_id)` output and can be ambiguous when a subject/time group spans
  more than one stay.
- The two `rn` values: `ce.rn` controls row inclusion (`ce.rn = 1`), while
  `o2.rn` controls device-slot assignment (`1` through `4`).

`valueuom` is selected in the flow staging CTEs but is not used in any filter,
window, join, aggregation, or final output; it is not semantically essential
to this derived table as written. `ce.value`, once used for the non-NULL flow
filter, is likewise not an output field; `o2.value` is essential because it is
the device output.

## Representability concerns for downstream probing

These are consequences of the source SQL and observed MIMIC-on-FHIR behavior,
not implementation decisions:

1. **The source natural key is temporal and aggregation-sensitive.** The
   chartevents FHIR ETL writes `charttime` as Observation
   `effectiveDateTime` after a `TIMESTAMPTZ` cast. `MIMIC_NOTES.md` records that
   New York DST-gap wall times are normalized by +1 hour and can collide with
   genuine 03:xx observations. Because this SQL partitions, joins, and groups
   by `charttime`, that transformation can change the keyed row set and the
   selected/pivoted values. Resource ids are opaque and must not be used to
   recover the pre-normalization time.
2. **Duplicate selection depends on `storetime`.** The upstream chartevents
   ETL writes source `storetime` as Observation `issued` (as shown in
   `mimic-fhir/sql/fhir_observation_chartevents.sql:10,68`), so this discriminator
   should be specifically checked by the FHIR prober. If it is absent or
   transformed, exact latest-row and device-rank behavior is not recoverable
   from the remaining fields alone.
3. **The two value branches are different.** Numeric flow rows use
   `valuenum`; item `226732` is categorical and its source `value` is the
   device label. `MIMIC_NOTES.md` confirms that categorical chartevents,
   including `226732`, are served in `Observation.valueString`, not as a
   CodeableConcept. A probe must preserve the distinction rather than read
   only Quantity values.
4. **The source/FHIR global NULL-value rule differs at the device CTE.** The
   canonical flow branch excludes NULL `value`, but `o2` does not. The upstream
   chartevents ETL globally excludes NULL `value` rows. Although right-only
   device rows are already removed by `WHERE ce.rn = 1`, NULL device rows can
   still participate in the source device ranking when joined to a flow time;
   their effect should be checked rather than silently assumed away.
5. **The join and partitions omit `stay_id`.** The SQL itself matches and
   deduplicates by `(subject_id, charttime, itemid)` rather than
   `(stay_id, charttime, itemid)`, and then emits `MAX(stay_id)`. Any FHIR-side
   grouping or join that adds `stay_id` to the natural key would not reproduce
   this SQL. Conversely, if the served data contains multiple ICU stays for a
   patient at the same charttime, the source's max-stay behavior must be
   retained.
6. **Exact code identity matters.** The chartevents FHIR coding system carries
   source itemids verbatim. The `227582` Bipap-flow item is intentionally
   merged into the `o2_flow` output alongside `223834`; it must not be treated
   as an omitted or translated code.

No clinical interpretation or terminal representability decision is made here;
the FHIR prober and equivalence judge must establish whether these source
inputs survive sufficiently for an exact port.
