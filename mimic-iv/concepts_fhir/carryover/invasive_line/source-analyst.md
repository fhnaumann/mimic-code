# Source analysis: `invasive_line`

## Source and DAG identity

- Concept stem: `invasive_line`.
- Canonical SQL: `mimic-iv/concepts/treatment/invasive_line.sql`.
- The SQL is a single CTE (`mv`) followed by one final `SELECT`.
- DAG node: `invasive_line`, path `treatment/invasive_line.sql`, level `0`.
- DAG SHA-256: `61c8d3a30219a7d5e3380b3375b0ae595d524b280f1a69f24dcdb3e5a1fe2f7c`.
  The hash was checked against the canonical SQL on disk.
- DAG dependencies: none. The SQL has no reference to `mimiciv_derived` and
  the DAG lists no dependencies or dependents for this node. The
  `mimiciv_derived.invasive_line` table created by the build script is the
  materialized output, not an input dependency.

The immutable full-oracle manifest records five output columns, 93,378 rows,
and `comparison: full_tuple_multiset`. It declares no unique natural key
(`key: null`). The manifest output types are `INTEGER`, `VARCHAR`, `VARCHAR`,
`TIMESTAMP`, and `TIMESTAMP`, in output order below.

## 1. Physical table references

The source SQL uses BigQuery project-qualified names. Their MIMIC schema/table
identities are:

| SQL clause | Schema | Table | Alias | Used by |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.procedureevents\` mv` | `mimiciv_icu` | `procedureevents` | `mv` | CTE `mv` |
| `INNER JOIN \`physionet-data.mimiciv_icu.d_items\` di` | `mimiciv_icu` | `d_items` | `di` | CTE `mv` |
| `FROM mv` | CTE, not a physical table | `mv` | `mv` | final `SELECT` |

There are no `mimiciv_hosp` table references, no other raw tables, and no
`mimiciv_derived` table references.

The relevant MIMIC-IV DDL types are:

| Physical column | Source table | DDL type | Nullability and use |
|---|---|---|---|
| `stay_id` | `mimiciv_icu.procedureevents` | `INTEGER` | `NOT NULL`; CTE and final output |
| `itemid` | `mimiciv_icu.procedureevents` | `INTEGER` | `NOT NULL`; code filter and CTE `line_number` |
| `location` | `mimiciv_icu.procedureevents` | `VARCHAR(100)` | nullable; CTE `line_site`, then final site normalization |
| `starttime` | `mimiciv_icu.procedureevents` | `TIMESTAMP` | `NOT NULL`; CTE and final output |
| `endtime` | `mimiciv_icu.procedureevents` | `TIMESTAMP` | `NOT NULL`; CTE and final output |
| `itemid` | `mimiciv_icu.d_items` | `INTEGER` | primary key; join key and not selected independently |
| `label` | `mimiciv_icu.d_items` | `VARCHAR(100)` | `NOT NULL`; CTE `line_type` |

Other columns in either physical table are not referenced by this SQL. In
particular, `subject_id`, `hadm_id`, `caregiver_id`, `storetime`, `value`,
`valueuom`, `locationcategory`, `orderid`, `linkorderid`, order metadata, and
amount/rate fields from `procedureevents` are not selected or filtered.

## 2. CTE and column flow

### CTE `mv`

The CTE is:

```sql
SELECT
    stay_id,
    mv.itemid AS line_number,
    di.label AS line_type,
    mv.location AS line_site,
    starttime,
    endtime
FROM `physionet-data.mimiciv_icu.procedureevents` mv
INNER JOIN `physionet-data.mimiciv_icu.d_items` di
           ON mv.itemid = di.itemid
WHERE mv.itemid IN (...)
```

CTE columns and inferred types:

| CTE column | Expression | Type | Role |
|---|---|---|---|
| `stay_id` | `procedureevents.stay_id` | `INTEGER` | carried to final output |
| `line_number` | `mv.itemid` | `INTEGER` | intermediate item identifier; dropped by final `SELECT` |
| `line_type` | `di.label` | `VARCHAR(100)` / output `VARCHAR` | input to final type `CASE` |
| `line_site` | `mv.location` | `VARCHAR(100)` / output `VARCHAR` | input to final site `CASE` |
| `starttime` | `mv.starttime` | `TIMESTAMP` | carried to final output |
| `endtime` | `mv.endtime` | `TIMESTAMP` | carried to final output |

`line_number` is deliberately selected in the CTE because the comment says
Metavision separates lines using `itemid`, but it is not emitted by the final
query. The final output therefore has no itemid/line-number column.

### Final output expressions

The final `SELECT` emits, in order:

1. `stay_id`: the CTE `stay_id`, `INTEGER`.
2. `line_type`: a string `CASE` over CTE `line_type`, output `VARCHAR`.
3. `line_site`: a string `CASE` over CTE `line_site`, output `VARCHAR`.
4. `starttime`: the CTE timestamp, `TIMESTAMP`.
5. `endtime`: the CTE timestamp, `TIMESTAMP`.

The full output schema is therefore:

| Ordinal | Output column | Manifest type | Source/transform |
|---:|---|---|---|
| 1 | `stay_id` | `INTEGER` | `mv.stay_id` |
| 2 | `line_type` | `VARCHAR` | normalized `mv.line_type` (`di.label`), otherwise unchanged |
| 3 | `line_site` | `VARCHAR` | normalized `mv.line_site` (`procedureevents.location`), otherwise unchanged |
| 4 | `starttime` | `TIMESTAMP` | `mv.starttime` |
| 5 | `endtime` | `TIMESTAMP` | `mv.endtime` |

The source `location` is nullable, so `line_site` can remain NULL through the
`CASE` (`ELSE line_site`). `stay_id`, `starttime`, and `endtime` are non-null
in the raw `procedureevents` DDL. The inner dimension join and non-null
`d_items.label` make the CTE `line_type` non-null for retained rows; the
manifest records types, not nullability constraints.

## 3. Filters and literal code specification

There is exactly one executable `WHERE` clause predicate:

```sql
mv.itemid IN
(
    227719,
    225752,
    224269,
    224267,
    224270,
    224272,
    226124,
    228169,
    225202,
    228286,
    225204,
    224263,
    224560,
    224264,
    225203,
    224273,
    225789,
    225761,
    228201,
    228202,
    224268,
    225199,
    225315,
    225205
)
```

Exact literal itemid set, copied in SQL order with the source comments:

| Exact itemid literal | Source table/column filtered | SQL comment/label | Feeds |
|---:|---|---|---|
| `227719` | `mimiciv_icu.procedureevents.itemid` | `AVA Line` | retained CTE `mv` row, intermediate `line_number`, `di.label`-derived `line_type`, `line_site`, `starttime`, `endtime`; then final output |
| `225752` | `mimiciv_icu.procedureevents.itemid` | `Arterial Line` | same CTE and final output columns |
| `224269` | `mimiciv_icu.procedureevents.itemid` | `CCO PAC` | same CTE and final output columns |
| `224267` | `mimiciv_icu.procedureevents.itemid` | `Cordis/Introducer` | same CTE and final output columns |
| `224270` | `mimiciv_icu.procedureevents.itemid` | `Dialysis Catheter` | same CTE and final output columns |
| `224272` | `mimiciv_icu.procedureevents.itemid` | `IABP line` | same CTE and final output columns |
| `226124` | `mimiciv_icu.procedureevents.itemid` | `ICP Catheter` | same CTE and final output columns |
| `228169` | `mimiciv_icu.procedureevents.itemid` | `Impella Line` | same CTE and final output columns |
| `225202` | `mimiciv_icu.procedureevents.itemid` | `Indwelling Port (PortaCath)` | same CTE and final output columns |
| `228286` | `mimiciv_icu.procedureevents.itemid` | `Intraosseous Device` | same CTE and final output columns |
| `225204` | `mimiciv_icu.procedureevents.itemid` | `Midline` | same CTE and final output columns |
| `224263` | `mimiciv_icu.procedureevents.itemid` | `Multi Lumen` | same CTE and final output columns |
| `224560` | `mimiciv_icu.procedureevents.itemid` | `PA Catheter` | same CTE and final output columns |
| `224264` | `mimiciv_icu.procedureevents.itemid` | `PICC Line` | same CTE and final output columns |
| `225203` | `mimiciv_icu.procedureevents.itemid` | `Pheresis Catheter` | same CTE and final output columns |
| `224273` | `mimiciv_icu.procedureevents.itemid` | `Presep Catheter` | same CTE and final output columns |
| `225789` | `mimiciv_icu.procedureevents.itemid` | `Sheath` | same CTE and final output columns |
| `225761` | `mimiciv_icu.procedureevents.itemid` | `Sheath Insertion` | same CTE and final output columns |
| `228201` | `mimiciv_icu.procedureevents.itemid` | `Tandem Heart Access Line` | same CTE and final output columns |
| `228202` | `mimiciv_icu.procedureevents.itemid` | `Tandem Heart Return Line` | same CTE and final output columns |
| `224268` | `mimiciv_icu.procedureevents.itemid` | `Trauma line` | same CTE and final output columns |
| `225199` | `mimiciv_icu.procedureevents.itemid` | `Triple Introducer` | same CTE and final output columns |
| `225315` | `mimiciv_icu.procedureevents.itemid` | `Tunneled (Hickman) Line` | same CTE and final output columns |
| `225205` | `mimiciv_icu.procedureevents.itemid` | `RIC` | same CTE and final output columns |

This is an itemid code set on `mimiciv_icu.procedureevents`, not on
`mimiciv_icu.d_items`. The `d_items` table is joined to obtain the label for
each retained itemid. The SQL names no ICD code, ICD version, LOINC code, or
other coding system. No itemid is omitted from the table above, normalized,
expanded, or substituted. Source-only analysis does not establish any of
these executable itemids as a dead filter; all 24 remain part of the port's
code specification.

There are no additional executable filters:

- no `IS NULL`/`IS NOT NULL` predicate;
- no time window or stay/admission window;
- no `value`, `valueuom`, location, or status constraint;
- no code exclusion beyond the exact itemid `IN` list.

## 4. Joins

The CTE has one physical join:

```sql
FROM mimiciv_icu.procedureevents AS mv
INNER JOIN mimiciv_icu.d_items AS di
  ON mv.itemid = di.itemid
```

- Join type: `INNER JOIN`.
- Join condition: equality of `mimiciv_icu.procedureevents.itemid` and
  `mimiciv_icu.d_items.itemid`.
- Left input: filtered `procedureevents` rows.
- Right input: `d_items` dimension rows.
- Selected dimension field: `di.label AS line_type`.
- Effect: a filtered procedure row is retained only when its itemid has a
  matching `d_items` row. The source DDL defines `d_items.itemid` as a primary
  key, so this dimension join does not intentionally fan out a procedure row.
- No join uses `stay_id`, `subject_id`, `hadm_id`, time, or location.

The final `FROM mv` is a CTE reference and has no join predicate. There are no
LEFT, RIGHT, FULL, or implicit joins.

## 5. Value transformations (non-filter CASE literal sets)

The final query consolidates exact source label strings. These are executable
`CASE` value mappings, not additional `WHERE` code filters. Their spelling,
capitalization, punctuation, and output values are retained here verbatim.

### `line_type` mappings

| Exact input set in SQL | Exact output |
|---|---|
| `('Arterial Line', 'A-Line')` | `'Arterial'` |
| `('CCO PA Line', 'CCO PAC')` | `'Continuous Cardiac Output PA'` |
| `('Dialysis Catheter', 'Dialysis Line')` | `'Dialysis'` |
| `('Hickman', 'Tunneled (Hickman) Line')` | `'Hickman'` |
| `('IABP', 'IABP line')` | `'IABP'` |
| `('Multi Lumen', 'Multi-lumen')` | `'Multi Lumen'` |
| `('PA Catheter', 'PA line')` | `'PA'` |
| `('PICC Line', 'PICC line')` | `'PICC'` |
| `('Pre-Sep Catheter', 'Presep Catheter')` | `'Pre-Sep'` |
| `('Trauma Line', 'Trauma line')` | `'Trauma'` |
| `('Triple Introducer', 'TripleIntroducer')` | `'Triple Introducer'` |
| `('Portacath', 'Indwelling Port (PortaCath)')` | `'Portacath'` |

For every other `line_type`, the `ELSE line_type` branch preserves the
dimension label unchanged. The SQL comments list the following terms as not
merged; they are comments/documentation rather than executable predicates or
additional mappings: `AVA Line`, `Camino Bolt`, `Cordis/Introducer`, `ICP
Catheter`, `Impella Line`, `Intraosseous Device`, `Introducer`, `Lumbar Drain`,
`Midline`, `Other/Remarks`, `PacerIntroducer`, `PermaCath`, `Pheresis Catheter`,
`RIC`, `Sheath`, `Tandem Heart Access Line`, `Tandem Heart Return Line`, `Venous
Access`, and `Ventriculostomy`.

### `line_site` mappings

| Exact input set in SQL | Exact output |
|---|---|
| `('Left Antecub', 'Left Antecube')` | `'Left Antecube'` |
| `('Left Axilla', 'Left Axilla.')` | `'Left Axilla'` |
| `('Left Brachial', 'Left Brachial.')` | `'Left Brachial'` |
| `('Left Femoral', 'Left Femoral.')` | `'Left Femoral'` |
| `('Right Antecub', 'Right Antecube')` | `'Right Antecube'` |
| `('Right Axilla', 'Right Axilla.')` | `'Right Axilla'` |
| `('Right Brachial', 'Right Brachial.')` | `'Right Brachial'` |
| `('Right Femoral', 'Right Femoral.')` | `'Right Femoral'` |

For every other `line_site`, including NULL, the `ELSE line_site` branch
preserves it. The SQL comments list these explicitly unmerged values:
`'Left Foot'`, `'Left IJ'`, `'Left Radial'`, `'Left Subclavian'`, `'Left Ulnar'`,
`'Left Upper Arm'`, `'Right Foot'`, `'Right IJ'`, `'Right Radial'`, `'Right Side
Head'`, `'Right Subclavian'`, `'Right Ulnar'`, `'Right Upper Arm'`,
`'Transthoracic'`, and `'Other/Remarks'`. These comments do not filter rows.

There is no arithmetic, cast, date truncation, time-zone operation, window
function, or value aggregation. `ORDER BY stay_id, starttime, line_type,
line_site` only requests presentation order and does not change the output
relation or deduplicate rows.

## 6. Aggregations and row-grain implications

- No `GROUP BY`.
- No aggregate functions (`MIN`, `MAX`, `AVG`, `SUM`, `ARRAY_AGG`, etc.).
- No window functions.
- No `DISTINCT`.
- No deduplication step.
- The logical row grain is one retained `procedureevents` row after the
  itemid filter and the one-to-one-by-dimension-key inner join, with the raw
  `itemid` converted to `di.label` and the two string normalizations applied.

The raw DDL declares `procedureevents.orderid` as its primary key, but
`orderid` is not selected. The intermediate `line_number` (the raw itemid) is
also dropped. Consequently, the emitted five-column tuple is not declared
unique by the SQL: separate procedure-event rows can have the same emitted
`(stay_id, line_type, line_site, starttime, endtime)` tuple. The full-oracle
manifest accordingly has no natural key and compares this concept as an
order-independent full-tuple multiset. Preserve duplicate tuple multiplicity;
do not add a key-based grouping or `DISTINCT`.

## 7. Dependencies and downstream mapping implications

- `mimiciv_derived` dependency: none.
- Raw dependencies: `mimiciv_icu.procedureevents` and
  `mimiciv_icu.d_items`.
- The code filter must use the exact 24 integer itemids listed above on the
  `procedureevents` stream.
- The final output intentionally lacks `subject_id`, `hadm_id`, `itemid`,
  `line_number`, `locationcategory`, `orderid`, and all procedure value/amount
  fields.
- The final type consolidations are label/site string substitutions only;
  labels not in an executable `CASE WHEN` set pass through unchanged.
- The output includes event interval endpoints directly as `starttime` and
  `endtime`, with no interval filtering or duration calculation.
- Because there is no natural key, downstream equivalence must use the
  manifest's full-tuple multiset semantics rather than inventing a key from
  `stay_id` or timestamps.

## Summary

`invasive_line` is a level-0, dependency-free ICU procedure concept. It inner
joins `mimiciv_icu.procedureevents` to `mimiciv_icu.d_items` on `itemid`, retains
exactly the 24 itemids named in the SQL, maps the dimension label and source
location through explicit string-normalization CASE expressions, and emits
`(stay_id, line_type, line_site, starttime, endtime)` as
`(INTEGER, VARCHAR, VARCHAR, TIMESTAMP, TIMESTAMP)` without aggregation or
deduplication; the full output has no unique natural key and is compared as a
tuple multiset.
