# Source analysis: `first_day_rrt`

## Scope and source identity

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_rrt.sql`
- DAG node: `first_day_rrt`
- DAG path: `firstday/first_day_rrt.sql`
- DAG source SHA256: `24b7035b85822139f5b7ab952598ff2dcd35067040dd23c239e6db81ce43c859`
- DAG level: `1`
- DAG dependency: `rrt`
- DAG dependent: `meld`

The target SQL has no CTEs. It reads ICU stays and the completed derived
`rrt` concept, restricts the derived events to an ICU-stay-relative time
window, and aggregates to one row per ICU stay.

## 1. Table references

Every table reference in the target SQL is:

| SQL clause | Alias | Schema | Table | Join type | Purpose |
|---|---|---|---|---|---|
| `FROM` | `ie` | `mimiciv_icu` | `icustays` | base relation | ICU-stay population, identifiers, and `intime` |
| `LEFT JOIN` | `rrt` | `mimiciv_derived` | `rrt` | `LEFT` | RRT events/ranges already derived by the `rrt` concept |

There is no `mimiciv_hosp` table reference in `first_day_rrt.sql`.

The dependency SQL itself (`mimic-iv/concepts/treatment/rrt.sql`) reads these
raw ICU tables, which are recorded below only to document the dependency's
lineage; they must not be re-derived in the `first_day_rrt` port:

| Dependency CTE/branch | Schema | Table | Referenced fields |
|---|---|---|---|
| `ce` | `mimiciv_icu` | `chartevents` | `stay_id`, `charttime`, `itemid`, `value` |
| `mv_ranges` input branch | `mimiciv_icu` | `inputevents` | `stay_id`, `starttime`, `endtime`, `itemid`, `amount` |
| `mv_ranges` procedure branch | `mimiciv_icu` | `procedureevents` | `stay_id`, `starttime`, `endtime`, `itemid`, `value` |

## 2. Output columns and inferred types

The target has no intermediate CTE columns. Its final projection is:

| Output column | Expression | Inferred type | Nullability/meaning |
|---|---|---|---|
| `subject_id` | `ie.subject_id` | `INTEGER` | ICU patient identifier; also part of the grouping key |
| `stay_id` | `ie.stay_id` | `INTEGER` | ICU-stay identifier; also the join and grouping key |
| `dialysis_present` | `MAX(rrt.dialysis_present)` | `INTEGER` | Maximum dependency flag in the window; NULL when the left join has no matching dependency rows |
| `dialysis_active` | `MAX(rrt.dialysis_active)` | `INTEGER` | Maximum dependency flag in the window; NULL when there are no matching dependency rows |
| `dialysis_type` | `STRING_AGG(DISTINCT rrt.dialysis_type, ', ' ORDER BY rrt.dialysis_type)` | nullable string (`VARCHAR`/`TEXT`) | Distinct non-NULL dependency types, sorted by `dialysis_type` and joined with comma-space; NULL if no type is aggregated |

The source DDL defines `mimiciv_icu.icustays.subject_id` and `stay_id` as
`INTEGER`, and `intime` as `TIMESTAMP`. The `rrt` dependency produces
`stay_id` as an integer, `charttime` as a timestamp, the two dialysis flags
from integer `0`/`1` literals, and nullable string `dialysis_type`.

## 3. Natural grain

The output grain is one row per ICU stay, represented by the grouped key
`(subject_id, stay_id)`. `stay_id` is the practical natural identifier, while
the canonical SQL groups by both `ie.subject_id` and `ie.stay_id` and emits
both. The `LEFT JOIN` plus grouping preserves every `icustays` row even when
no RRT dependency row falls in the window; in that case both `MAX` results and
the string aggregate are NULL rather than the ICU stay being removed.

The dependency may contain multiple event/range rows for a stay and time.
Those rows are intentionally collapsed by the target's two `MAX` operations
and its `DISTINCT` ordered string aggregation. No one-row-per-event or
one-row-per-time assumption is valid at the target input boundary.

## 4. Filters and joins in the target SQL

### Filters

There is no `WHERE` clause, no itemid filter, no ICD/code filter, no value
constraint, and no `outtime` condition in `first_day_rrt.sql`.

The temporal predicates are part of the `LEFT JOIN` condition, not a WHERE
filter:

```sql
rrt.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
AND rrt.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

Thus an RRT dependency row is eligible only when it has the same `stay_id`
and its `charttime` is in the inclusive interval from six hours before ICU
`intime` through one day after ICU `intime`, including both endpoints. The
window is therefore 30 hours wide, despite the concept's first-day name.
Because these predicates are on the right side of a LEFT JOIN, a NULL
`ie.intime` produces no qualifying RRT match but does not remove the ICU-stay
row.

The target does not itself add `rrt.dialysis_present = 1`; it aggregates all
rows supplied by the dependency that satisfy the stay/time join.

### Join

There is one `LEFT JOIN`:

```sql
FROM `physionet-data.mimiciv_icu.icustays` ie
LEFT JOIN `physionet-data.mimiciv_derived.rrt` rrt
  ON ie.stay_id = rrt.stay_id
 AND rrt.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
 AND rrt.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

The equality is the ICU-stay join. The two inclusive timestamp inequalities
are additional join predicates. There are no joins to Patient, Encounter,
hospital admissions, or dimension tables in this concept.

## 5. Aggregations

- `GROUP BY ie.subject_id, ie.stay_id` establishes the one-row-per-stay grain.
- `MAX(dialysis_present)` returns the highest dependency presence flag in the
  window.
- `MAX(dialysis_active)` returns the highest dependency active flag in the
  window.
- `STRING_AGG(DISTINCT dialysis_type, ', ' ORDER BY dialysis_type)` removes
  duplicate type values, orders the remaining values by the type expression,
  and concatenates them with the literal delimiter `', '`. There are no window
  functions or other value aggregations.

## 6. `mimiciv_derived` dependency contract

The target reads exactly one derived table: `mimiciv_derived.rrt`. The
candidate SQL for this concept must use the preprocessed dependency under its
unqualified stem, `FROM rrt`, and must consume these exact columns:

| Dependency column | Inferred type | Consumer use in `first_day_rrt` |
|---|---|---|
| `rrt.stay_id` | `INTEGER` | Equality join to `ie.stay_id` |
| `rrt.charttime` | `TIMESTAMP` | Inclusive six-hours-before through one-day-after `ie.intime` join window |
| `rrt.dialysis_present` | `INTEGER` (`0`/`1`) | `MAX` into output `dialysis_present` |
| `rrt.dialysis_active` | `INTEGER` (`0`/`1`) | `MAX` into output `dialysis_active` |
| `rrt.dialysis_type` | nullable string | `DISTINCT` ordered `STRING_AGG` into output `dialysis_type` |

`subject_id`, `charttime`, and all dialysis interpretations are not to be
reconstructed from FHIR resources for this consumer. In particular, the
`first_day_rrt` implementation must not inline the chartevents/inputevents/
procedureevents logic from `rrt.sql` or substitute an independent RRT
derivation.

### Dependency lineage and behavior

The upstream `rrt` SQL creates its `ce` CTE from selected
`mimiciv_icu.chartevents`, and its `mv_ranges` CTE from selected
`mimiciv_icu.inputevents` and `mimiciv_icu.procedureevents`. It combines
presence-bearing chart rows and range starts with `UNION DISTINCT`, then uses a
`LEFT JOIN` on `(stay_id, charttime between starttime and endtime)` to overlay
range flags/types with `COALESCE`. Its published columns are exactly the
five dependency columns listed above. It has no GROUP BY or window aggregate;
the target `first_day_rrt` performs the per-stay aggregation.

## 7. Literal code set and values

### Direct target code specification

`first_day_rrt.sql` names **no coded filter literals**. There are no
`itemid`, ICD, LOINC, or other code predicates in this SQL, so the direct code
set for this concept is empty. The target's non-code literals are:

| Literal | Location | Effect |
|---|---|---|
| `INTERVAL '6' HOUR` | `DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)` | Lower inclusive time bound |
| `INTERVAL '1' DAY` | `DATETIME_ADD(ie.intime, INTERVAL '1' DAY)` | Upper inclusive time bound |
| `', '` | `STRING_AGG(..., ', ' ...)` | Output delimiter for distinct dialysis types |

The target also uses the SQL aggregate keywords/literals `DISTINCT`,
`ORDER BY dialysis_type`, and numeric aggregation through `MAX`; these are
operations, not source code filters.

### Upstream `rrt` code contract (lineage only; do not inline)

The following is the active code/value specification named by the dependency
SQL. It is included so the dependency's exact literals are not lost during
mapping. These filters belong to the separate `rrt` concept; they are not
additional filters to author in `first_day_rrt`.

#### `mimiciv_icu.chartevents` (`ce` CTE)

The active `WHERE ce.itemid IN (...)` list, in source order, is:

```text
226118, 227357, 225725,
226499, 224154, 225810, 227639, 225183, 227438, 224191, 225806, 225807,
228004, 228005, 228006, 224144, 224145, 224149, 224150, 224151, 224152,
224153, 224404, 224406, 226457, 225959,
224135, 224139, 224146, 225323, 225740, 225776, 225951, 225952, 225953,
225954, 225956, 225958, 225961, 225963, 225965, 225976, 225977, 227124,
227290, 227638, 227640, 227753
```

This same source branch also applies the active predicate `ce.value IS NOT
NULL`. The selected chart rows feed `ce.charttime`, `ce.dialysis_present`,
`ce.dialysis_active`, and `ce.dialysis_type`, which ultimately feed the
dependency columns consumed by the target.

The `dialysis_present` CASE in `ce` assigns `1` for these exact itemid groups
from `mimiciv_icu.chartevents`:

```text
checkboxes: 226118, 227357, 225725
numeric:    226499, 224154, 225810, 225959, 227639, 225183, 227438,
            224191, 225806, 225807, 228004, 228005, 228006, 224144,
            224145, 224149, 224150, 224151, 224152, 224153, 224404,
            224406, 226457
text:       224135, 224139, 224146, 225323, 225740, 225776, 225951,
            225952, 225953, 225954, 225956, 225958, 225961, 225963,
            225965, 225976, 225977, 227124, 227290, 227638, 227640,
            227753
```

The `dialysis_active` CASE uses these exact coded/value branches from
`mimiciv_icu.chartevents`:

```text
ce.itemid = 225965 AND value = 'In use' -> 1
ce.itemid IN (226499, 224154, 225183, 227438, 224191, 225806, 225807,
              228004, 228005, 228006, 224144, 224145, 224153, 226457) -> 1
```

All other selected chart rows feed `dialysis_active = 0` through the CASE's
`ELSE 0`.

The `dialysis_type` CASE uses these exact branches from
`mimiciv_icu.chartevents`:

```text
ce.itemid = 227290 -> value
ce.itemid IN (225810, 225806, 225807, 225810, 227639, 225959, 225951,
              225952, 225961, 225953, 225963, 225965, 227638, 227640)
              -> 'Peritoneal'
ce.itemid = 226499 -> 'IHD'
ELSE -> NULL
```

The repeated `225810` above is retained exactly as written in the dependency
SQL; it has not been deduplicated in this specification. The `227290` branch
passes through the non-NULL source `ce.value`, rather than applying an
enumerated value filter. The comments in `rrt.sql` mention older itemids and
mode labels, but those commented-out lines are not executable filters and are
not part of the active code set.

#### `mimiciv_icu.inputevents` (`mv_ranges` input branch)

The active filter is copied here verbatim as a value list:

```sql
itemid IN (227536, 227525)
AND amount > 0
```

Source table: `mimiciv_icu.inputevents`. Both codes feed rows with
`dialysis_present = 1`, `dialysis_active = 1`, and `dialysis_type = 'CRRT'`
in `mv_ranges`; `starttime` becomes the dependency `charttime`, while
`endtime` controls the later interval overlay.

#### `mimiciv_icu.procedureevents` (`mv_ranges` procedure branch)

The active filter is copied here verbatim as a value list:

```sql
itemid IN (225441, 225802, 225803, 225805, 224270, 225809, 225955, 225436)
AND value IS NOT NULL
```

Source table: `mimiciv_icu.procedureevents`. Every listed code feeds
`dialysis_present = 1`. The active-flag discriminator is:

```sql
itemid NOT IN (224270, 225436) -> dialysis_active = 1
itemid IN (224270, 225436)    -> dialysis_active = 0
```

The type mapping is:

```text
225441 -> 'IHD'
225802 -> 'CRRT'
225803 -> 'CVVHD'
225805 -> 'Peritoneal'
225809 -> 'CVVHDF'
225955 -> 'SCUF'
224270 -> NULL
225436 -> NULL
```

These rows feed `mv_ranges.starttime` as dependency `charttime`; their
`endtime` values participate in the final inclusive range join in `rrt.sql`.

#### Dependency CTE filters/operations that are not code sets

- `ce` removes rows where `ce.value IS NULL`.
- `mv_ranges` uses `UNION DISTINCT` between its inputevents and
  procedureevents branches.
- `stg0` retains only rows where `dialysis_present = 1`.
- The final `rrt` overlay is a `LEFT JOIN` on equal `stay_id` and inclusive
  `stg0.charttime >= mv.starttime` / `stg0.charttime <= mv.endtime`, with
  `COALESCE` choosing range values when present.

## 8. Semantically essential inputs

These are the source/dependency fields whose values can change inclusion,
grain, temporal assignment, or a clinically meaningful output:

| Input | Controls | Trace to target behavior |
|---|---|---|
| `icustays.subject_id` | Output identity and grouping | Determines the emitted patient identifier and grouped row label |
| `icustays.stay_id` | Output identity, join, grouping | Determines which dependency rows can contribute and the natural stay row |
| `icustays.intime` | Temporal inclusion | Moves both inclusive bounds of the RRT window; changing it can add/remove every aggregate contribution |
| `rrt.stay_id` | Join inclusion | Must equal the ICU stay's `stay_id` for any dependency row to contribute |
| `rrt.charttime` | Temporal inclusion | Determines whether a dependency event/range-derived row is within `[-6 hours, +1 day]` relative to `intime` |
| `rrt.dialysis_present` | Presence output | Its maximum controls output `dialysis_present` |
| `rrt.dialysis_active` | Activity output | Its maximum controls output `dialysis_active` |
| `rrt.dialysis_type` | Type output | Its non-NULL value, distinctness, sort order, and string contents control output `dialysis_type` |
| NULL/non-NULL match state of `rrt` | Row-preserving and aggregate NULL semantics | The LEFT JOIN retains an ICU stay with NULL aggregate outputs when no qualifying RRT row exists |

Upstream of the dependency, the RRT fields are controlled by the selected
`chartevents.stay_id/charttime/itemid/value`, `inputevents.stay_id/starttime/
endtime/itemid/amount`, and `procedureevents.stay_id/starttime/endtime/itemid/
value` fields and their exact CASE discriminators listed above. Those inputs
are semantically essential to the already-completed `rrt` concept, but the
`first_day_rrt` consumer must read the resulting five dependency columns and
must not attempt to recover them independently.

## Dataset-wide quirks relevant to this consumer

No new dataset-wide quirk was established by this source-only analysis. The
read notes already record two relevant RRT/chartevents facts: repeated
same-item chartevents at one stay/time are retained, and the upstream FHIR ETL
can normalize spring-forward-gap chart times. They can affect the upstream
`rrt.charttime` stream and therefore this concept's time-window membership or
aggregates. These were read from `MIMIC_NOTES.md` and the provisional
`MIMIC_NOTES.d/rrt.md`/`crrt.md`; they were not independently probed here and
were not appended to `MIMIC_NOTES.d/first_day_rrt.md`.
