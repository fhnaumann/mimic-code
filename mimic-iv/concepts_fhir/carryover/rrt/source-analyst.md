# Source analysis: `rrt`

## Files read and authority

- Canonical SQL: `mimic-iv/concepts/treatment/rrt.sql`, lines 1-327.  The
  canonical SQL, rather than the generated dialect, is the source of truth.
- DAG: `mimic-iv/concept_dag/concept_dag.json`, lines 584-592, and the table
  reference in `mimic-iv/concept_dag/concept_dag.md`, lines 189-194.  The node
  is level 0, has no dependencies, and has `first_day_rrt` as a dependent.
- Full oracle manifest: `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`,
  lines 3138-3165.
- Raw-table definitions used for type inference:
  `mimic-iv/buildmimic/postgres/create.sql`, lines 369-383
  (`chartevents`), 449-478 (`inputevents`), and 494-513
  (`procedureevents`).
- Cross-concept notes read: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, especially
  lines 376-425 (FHIR datetime/DST behavior), 486-505 (Observation subtype
  discrimination), 521-531 (categorical chartevents values), and 673-715
  (verbatim itemid Observation codes and systems).
- Relevant fragments read as leads, not as established evidence:
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/crrt.md`, lines 1-15;
  `invasive_line.md`, lines 1-18; `icustay_times.md`, lines 1-3;
  `icp.md`, lines 1-19; `oxygen_delivery.md`, lines 1-7; and
  `MIMIC_NOTES.d/README.md`, lines 1-44.

The generated DuckDB form was also read for confirmation at
`mimic-iv/concepts_duckdb/treatment/rrt.sql`, lines 1-228.  It wraps the
result as `mimiciv_derived.rrt`, but that wrapper is not a dependency in the
canonical SQL or DAG.

## Purpose and query shape

The query emits dialysis/RRT observations at a `stay_id` and time, with three
derived values: presence, activity, and dialysis type.  It has three CTEs:

1. `ce` (lines 3-226) reads selected ICU chart events and classifies each
   non-null-valued row.
2. `mv_ranges` (lines 246-292) unions CRRT-related input-event intervals with
   dialysis procedure-event intervals.
3. `stg0` (lines 296-314) keeps chart rows marked present and appends the
   interval start rows.

The final SELECT (lines 316-327) overlays every `stg0` row with every matching
`mv_ranges` interval and uses `COALESCE` so an in-range interval value takes
precedence over the `stg0` value.

There are no `mimiciv_derived` references, no external concept dependencies,
no window functions, no `GROUP BY`, and no aggregate functions.  The query
does use `UNION DISTINCT` twice, which removes exact duplicate projected rows:
once between the two `mv_ranges` branches (lines 260-278), and once between
the chart and interval branches of `stg0` (lines 301-313).  The final range
join can still fan out when multiple intervals overlap a chart/start time.

## Table references

Executable `FROM`/`JOIN` references, using the logical MIMIC schema names, are:

| SQL lines | Type | Schema and table | Alias/role |
|---|---|---|---|
| 162 | FROM | `mimiciv_icu.chartevents` | `ce`, source for the `ce` CTE |
| 252 | FROM | `mimiciv_icu.inputevents` | first branch of `mv_ranges` |
| 279 | FROM | `mimiciv_icu.procedureevents` | second branch of `mv_ranges` |
| 323 | LEFT JOIN | the `mv_ranges` CTE | alias `mv`, interval overlay |

`outputevents` appears only in the commented TODO block at lines 232-244 and
is not executable.  `inputevents_cv` is mentioned only in a comment at line
230.  Neither is a table reference or DAG dependency for this query.

## Intermediate and final columns with inferred types

### `ce` CTE (lines 3-226)

Source fields referenced:

- `ce.stay_id`: `INTEGER`; selected to the CTE and carried to the output.
- `ce.charttime`: `TIMESTAMP`; selected to the CTE, becomes `stg0.charttime`,
  is used in the interval join, and is output as `charttime`.
- `ce.itemid`: `INTEGER`; used by the `WHERE` filter and all three CASE
  expressions.  It is not output.
- `ce.value`/unqualified `value`: `VARCHAR(200)` in `chartevents`; used for
  the non-NULL filter, for the `225965` active test, and as the mode value for
  item `227290`.  It is not output directly.

Derived columns:

- `dialysis_present`: `INTEGER` (CASE returns `1` or `0`).
- `dialysis_active`: `INTEGER` (CASE returns `1` or `0`).
- `dialysis_type`: nullable `VARCHAR`; it is the chart value for item `227290`,
  the literal `'Peritoneal'` for the PD item set, the literal `'IHD'` for
  item `226499`, or NULL.

The CTE row predicate is `ce.itemid IN (...) AND ce.value IS NOT NULL` (lines
163-225).  It does not use `valuenum`, `valueuom`, `storetime`, `subject_id`,
or `hadm_id`.

### `mv_ranges` CTE (lines 246-292)

Both branches select:

- `stay_id`: `INTEGER`.
- `starttime`, `endtime`: `TIMESTAMP`.
- `dialysis_present`: `INTEGER`, always literal `1`.
- `dialysis_active`: `INTEGER`; always `1` in the inputevents branch, and a
  CASE-derived `1`/`0` in the procedureevents branch.
- `dialysis_type`: nullable `VARCHAR`; inputevents always returns literal
  `'CRRT'`; procedureevents maps selected procedure itemids to the type
  literals or NULL.

Inputevents additionally references `itemid` (`INTEGER`) and `amount` (`FLOAT`)
for its filter.  Procedureevents additionally references `itemid` (`INTEGER`)
and `value` (`FLOAT`) for its filter and CASE expressions.  Other raw columns
are not referenced.

### `stg0` and final output (lines 296-327)

`stg0` projects `stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`),
`dialysis_present` (`INTEGER`), `dialysis_active` (`INTEGER`), and
`dialysis_type` (nullable `VARCHAR`) from the two union branches.  In its
second branch, `mv_ranges.starttime` is renamed to `charttime`.

The final output schema is, in order:

| Column | Type | Derivation |
|---|---|---|
| `stay_id` | `INTEGER` | `stg0.stay_id` |
| `charttime` | `TIMESTAMP` | unqualified `charttime` from `stg0` |
| `dialysis_present` | `INTEGER` | `COALESCE(mv.dialysis_present, stg0.dialysis_present)` |
| `dialysis_active` | `INTEGER` | `COALESCE(mv.dialysis_active, stg0.dialysis_active)` |
| `dialysis_type` | nullable `VARCHAR` | `COALESCE(mv.dialysis_type, stg0.dialysis_type)` |

This agrees with the oracle manifest at lines 3141-3159.  The oracle declares
`comparison: full_tuple_multiset`, `key: null`, and row count `2827715`
(lines 3161-3165).  Thus there is no declared unique natural key.  The
semantic coordinate is `(stay_id, charttime)`, but it must not be treated as a
unique key: duplicate chart rows can survive and overlapping range rows can
fan out in the final LEFT JOIN.  The port comparator must therefore use the
manifest's full-tuple multiset semantics.

## Filters and predicates

### Executable WHERE predicates

1. `ce` (lines 163-225): `ce.itemid IN (...)`; this restricts chart events to
   the exact 48-item set reproduced below.  It is combined with
   `ce.value IS NOT NULL`.
2. `mv_ranges` inputevents branch (lines 252-259):
   `itemid IN (227536, 225525)` in the exact SQL order shown below, and
   `amount > 0`.  The positive amount also excludes NULL in ordinary SQL
   three-valued logic, as the source comment notes.
3. `mv_ranges` procedureevents branch (lines 279-291): the exact eight-item
   `itemid IN (...)` set below and `value IS NOT NULL`.  There is no positivity
   constraint on procedure `value`; zero and negative non-NULL values pass.
4. `stg0` chart branch (lines 299-301): `dialysis_present = 1`.

There is no absolute time window, date filter, patient/hospital filter, or
value-range filter beyond `amount > 0` and the stated non-NULL predicates.

### Join predicate

The only executable table/CTE join is a `LEFT JOIN` at lines 323-326:

```sql
ON stg0.stay_id = mv.stay_id
   AND stg0.charttime >= mv.starttime
   AND stg0.charttime <= mv.endtime
```

Both interval endpoints are inclusive.  Unmatched `stg0` rows remain, with
the `COALESCE` expressions falling back to the `stg0` values.  If several
`mv_ranges` intervals match, the row is repeated once per match and each
match's non-NULL values can override the fallback independently.

## Literal code specification (verbatim)

The following are the source SQL's exact itemid/value literals.  They are
recorded without normalization or deduplication.  The source table and the
output/CTE branch controlled by each set are explicit.

### `mimiciv_icu.chartevents`: `ce.dialysis_present`

The checkbox set in the first CASE branch (lines 21-26) is:

```sql
226118
, 227357
, 225725
```

The numeric-data set in the second CASE branch (lines 28-58) is:

```sql
226499
, 224154
, 225810
, 225959
, 227639
, 225183
, 227438
, 224191
, 225806
, 225807
, 228004
, 228005
, 228006
, 224144
, 224145
, 224149
, 224150
, 224151
, 224152
, 224153
, 224404
, 224406
, 226457
```

The text-field set in the third CASE branch (lines 61-95) is:

```sql
224135
, 224139
, 224146
, 225323
, 225740
, 225776
, 225951
, 225952
, 225953
, 225954
, 225956
, 225958
, 225961
, 225963
, 225965
, 225976
, 225977
, 227124
, 227290
, 227638
, 227640
, 227753
```

The executable `ce` row filter (lines 163-224) is the following single
`itemid` set, in source order; it feeds all three `ce` output columns through
the CASE expressions and then feeds the `ce` branch of `stg0`:

```sql
226118
, 227357
, 225725
, 226499
, 224154
, 225810
, 227639
, 225183
, 227438
, 224191
, 225806
, 225807
, 228004
, 228005
, 228006
, 224144
, 224145
, 224149
, 224150
, 224151
, 224152
, 224153
, 224404
, 224406
, 226457
, 225959
, 224135
, 224139
, 224146
, 225323
, 225740
, 225776
, 225951
, 225952
, 225953
, 225954
, 225956
, 225958
, 225961
, 225963
, 225965
, 225976
, 225977
, 227124
, 227290
, 227638
, 227640
, 227753
```

The accompanying executable value filter is exactly `ce.value IS NOT NULL`
(line 225), feeding inclusion in `ce`; it is not a code set.

### `mimiciv_icu.chartevents`: `ce.dialysis_active`

The singleton discriminator (lines 99-100) is:

```sql
ce.itemid = 225965
AND value = 'In use'
```

It feeds `ce.dialysis_active = 1`.  The second active branch (lines 101-117)
uses this exact itemid set:

```sql
226499
, 224154
, 225183
, 227438
, 224191
, 225806
, 225807
, 228004
, 228005
, 228006
, 224144
, 224145
, 224153
, 226457
```

Those itemids feed `ce.dialysis_active = 1`; all other retained chart rows
feed `0`.

### `mimiciv_icu.chartevents`: `ce.dialysis_type`

The executable mode discriminator at lines 129-130 is:

```sql
ce.itemid = 227290 THEN value
```

The peritoneal set at lines 133-157 is copied verbatim, including the repeated
`225810`:

```sql
225810
, 225806
, 225807
, 225810
, 227639
, 225959
, 225951
, 225952
, 225961
, 225953
, 225963
, 225965
, 227638
, 227640
```

Every item in that set feeds the literal output value `'Peritoneal'`.
The singleton `ce.itemid = 226499` at lines 159-160 feeds the literal output
value `'IHD'`; the ELSE branch feeds NULL.  The `227290` branch feeds the raw
`chartevents.value` string, not a translated label.

### `mimiciv_icu.inputevents`: first `mv_ranges` branch

The executable filter at lines 253-259 is exactly:

```sql
itemid IN
(
    227536
    , 227525
)
AND amount > 0
```

Both itemids feed the fixed branch outputs `dialysis_present = 1`,
`dialysis_active = 1`, and `dialysis_type = 'CRRT'`, with the interval
`starttime`/`endtime`.

### `mimiciv_icu.procedureevents`: second `mv_ranges` branch

The executable filter at lines 280-291 is exactly:

```sql
itemid IN
(
    225441
    , 225802
    , 225803
    , 225805
    , 224270
    , 225809
    , 225955
    , 225436
)
AND value IS NOT NULL
```

The active discriminator at lines 264-266 is exactly:

```sql
WHEN itemid NOT IN (224270, 225436) THEN 1 ELSE 0
```

Thus `224270` and `225436` feed `dialysis_active = 0`; the other six
filtered itemids feed `1`.

The type mapping at lines 267-278 is:

```sql
WHEN itemid = 225441 THEN 'IHD'
WHEN itemid = 225802 THEN 'CRRT'
WHEN itemid = 225803 THEN 'CVVHD'
WHEN itemid = 225805 THEN 'Peritoneal'
WHEN itemid = 225809 THEN 'CVVHDF'
WHEN itemid = 225955 THEN 'SCUF'
ELSE NULL
```

All eight procedure itemids feed `dialysis_present = 1`; the two items not
matched by the type CASE (`224270` and `225436`) feed a NULL
`dialysis_type`.

### `stg0` and final output literals

`stg0` retains only `dialysis_present = 1` at lines 299-301.  The interval
branch carries the fixed/derived values from `mv_ranges` (lines 307-313).
The final output contains no further code filter; it applies the three
`COALESCE` expressions at lines 319-321.

### Comment-only, non-executable legacy/TODO code literals

These literals appear in comments and must not be treated as active filters or
source dependencies, but they are recorded to avoid confusing source
specification with active SQL:

- Lines 6-7: `ce.itemid in (152,148,149,146,147,151,150)` with
  `value is not null` (commented condition).
- Lines 8-9: `ce.itemid in (229,235,241,247,253,259,265,271)` with
  `value = 'Dialysis Line'` (commented condition).
- Lines 10-12: `ce.itemid = 466` with `value = 'Dialysis RN'`,
  `ce.itemid = 927` with `value = 'Dialysis Solutions'`, and
  `ce.itemid = 6250` with `value = 'dialys'` (commented conditions).
- Lines 14-16: `ce.itemid = 582` with
  `value in ('CAVH Start','CAVH D/C','CVVHD Start','CVVHD D/C',
  'Hemodialysis st','Hemodialysis end')` (commented condition).
- Lines 232-244: the commented `outputevents` branch would have used
  `itemid IN (40386)` and `value > 0`, with `dialysis_present = 1`,
  `dialysis_active = 0`, and NULL `dialysis_type`; it is not executed.

## Joins, unions, and temporal behavior

- `mv_ranges` uses `UNION DISTINCT`, not `UNION ALL`, between its inputevents
  and procedureevents interval rows.
- `stg0` uses `UNION DISTINCT`, not `UNION ALL`, between selected chart rows
  and interval-start rows.  This makes exact projected duplicates disappear,
  but does not aggregate or rank rows.
- The final `LEFT JOIN` overlays interval values for the same stay and an
  inclusive `[starttime, endtime]` charttime range.  This is the only temporal
  carry/overlay mechanism.  There is no window-based carry-forward and no
  `MIN`/`MAX`/`AVG` or other value aggregation.
- `COALESCE(mv.*, stg0.*)` gives an interval match precedence for each output
  field independently.  Since the interval branch's `dialysis_present` is
  always 1, a match makes presence 1; its active/type values can be 0/NULL or
  a mapped value depending on the matching interval.

## Semantically essential source inputs

- `chartevents.stay_id`: output identity coordinate and the equality side of
  the range join.  Losing it changes row identity and interval matching.
- `chartevents.charttime`: output time and the value tested against every
  interval's inclusive start/end.  It controls both row coordinate and the
  temporal overlay.
- `chartevents.itemid`: controls chart-row inclusion, the
  `dialysis_present` branch, active status, and type mapping/raw-mode branch.
  It is therefore essential to all three derived output columns.
- `chartevents.value`: non-NULL controls row inclusion; exact `'In use'`
  changes active status for item `225965`; and the raw value controls the
  output type for item `227290`.  It is a clinically meaningful discriminator
  even though it is not itself output for most rows.
- `inputevents.stay_id`, `starttime`, and `endtime`: define the interval's
  output start row, temporal coverage, and join coordinate.
- `inputevents.itemid`: controls inclusion in the CRRT interval branch; both
  retained itemids produce the CRRT/active branch values.
- `inputevents.amount`: the `> 0` predicate controls whether a CRRT interval
  exists at all.
- `procedureevents.stay_id`, `starttime`, and `endtime`: define the interval
  start row and inclusive temporal coverage.
- `procedureevents.itemid`: controls inclusion, whether the interval is active
  (`224270`/`225436` are inactive), and the mapped `dialysis_type`.
- `procedureevents.value`: non-NULL controls whether the procedure interval
  exists; its numeric magnitude is otherwise not output or used.
- The interval membership predicate (`stay_id` equality plus inclusive
  `charttime >= starttime` and `charttime <= endtime`) controls whether the
  final output uses interval values and can change output multiplicity through
  overlapping intervals.

No source field is used for grouping, window carry-forward, or an explicit
natural-key construction.  Exact-row deduplication is controlled by the
projected values in the two `UNION DISTINCT` operations.

## Dataset-wide quirk recommendation

No new dataset-wide fact can be established from reading source SQL alone, so
nothing should be appended to `MIMIC_NOTES.d/rrt.md` solely on the basis of
this source-analysis stage.  Existing established notes already cover the
most relevant cross-concept rules: itemid-derived Observation codes are
verbatim with the chartevents coding system (`MIMIC_NOTES.md:673-715`),
categorical chartevents values are in `value.ofType(string)`
(`MIMIC_NOTES.md:521-531`), and FHIR datetime values can carry the upstream
DST-gap normalization (`MIMIC_NOTES.md:376-425`).

The `crrt` fragment's report that repeated same-item chartevents can survive
at one `(stay_id, charttime)` (its lines 1-3) is a useful **provisional lead**
for the RRT FHIR probe, not evidence for this concept and not a new entry to
copy into the RRT fragment without RRT-specific served-data verification.
Likewise, its DST collision observations (lines 5-15) are leads; they must not
be solved by parsing or regenerating opaque FHIR resource IDs.  Any confirmed
RRT-wide data/IG behavior belongs in an append-only `##` section of
`MIMIC_NOTES.d/rrt.md` by the orchestrator after probing/full comparison;
concept-specific mapping or loss remains in the attempt evidence.
