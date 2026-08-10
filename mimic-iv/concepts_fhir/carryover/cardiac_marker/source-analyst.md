# Source analysis: `cardiac_marker`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/measurement/cardiac_marker.sql`.
- The SQL has no CTEs; the query is a single grouped `SELECT`.
- DAG metadata (`mimic-iv/concept_dag/concept_dag.json`) identifies the stem as
  `cardiac_marker`, path `measurement/cardiac_marker.sql`, level `0`, SHA-256
  `a8e02e5df6089cb4c26cf7c5779a999cf20b5708071f5ae113b570b5f1ac7b36`, with no
  dependencies or dependents.

## Table references

The only table reference is:

| SQL clause | Schema | Table | Alias | Join type |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_hosp.labevents\` le` | `mimiciv_hosp` | `labevents` | `le` | base table; no join |

There are no `JOIN` clauses and no references to `mimiciv_derived` tables.
The `physionet-data` prefix is a project/catalog qualifier; the MIMIC schema is
`mimiciv_hosp`.

The MIMIC-IV PostgreSQL DDL read for `mimiciv_hosp.labevents` declares the
referenced source columns as follows: `subject_id INTEGER NOT NULL`,
`hadm_id INTEGER`, `specimen_id INTEGER NOT NULL`, `itemid INTEGER NOT NULL`,
`charttime TIMESTAMP(0)`, and `valuenum DOUBLE PRECISION`.

## Referenced columns and output schema

There are no intermediate CTE columns. Every referenced source column is:

| Source column | Use | Source type / nullability from DDL |
|---|---|---|
| `le.subject_id` | `MAX` grouping-row representative | `INTEGER NOT NULL` |
| `le.hadm_id` | `MAX` grouping-row representative | `INTEGER`, nullable |
| `le.charttime` | `MAX` grouping-row representative | `TIMESTAMP(0)`, nullable |
| `le.specimen_id` | selected grouping key | `INTEGER NOT NULL` |
| `le.itemid` | coded filter and three `CASE` predicates | `INTEGER NOT NULL` |
| `le.valuenum` (unqualified as `valuenum` in the SQL) | non-null filter and `CASE` result | `DOUBLE PRECISION`, nullable |

The final output has one row per `le.specimen_id` and these columns, in this
order:

| Output column | SQL expression | Expected type |
|---|---|---|
| `subject_id` | `MAX(subject_id)` | `INTEGER` |
| `hadm_id` | `MAX(hadm_id)` | `INTEGER` (nullable) |
| `charttime` | `MAX(charttime)` | `TIMESTAMP(0)` (nullable) |
| `specimen_id` | `le.specimen_id` | `INTEGER` |
| `troponin_t` | `MAX(CASE WHEN itemid = 51003 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION` (nullable) |
| `ck_mb` | `MAX(CASE WHEN itemid = 50911 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION` (nullable) |
| `ntprobnp` | `MAX(CASE WHEN itemid = 50963 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION` (nullable) |

The `CASE` expressions are numeric because their non-null branch is
`valuenum`; the explicit `ELSE NULL` makes each pivoted analyte nullable. A
specimen can therefore produce a row with a null value for any analyte not
present in that specimen's filtered rows.

## Filters

The complete active `WHERE` logic is:

1. `le.itemid IN (...)`, restricting rows to the three active lab item IDs
   listed in the literal-code section below.
2. `valuenum IS NOT NULL` (resolved against `le.valuenum`), removing rows with
   no numeric value before the pivot and aggregation.

There is no time window, no `charttime` predicate, no value-range or unit
constraint, no `hadm_id`/patient constraint, and no code exclusion beyond the
positive itemid allow-list.

## Joins

There are no joins. The base table is read directly and all output columns are
derived from the same `labevents` row set.

## Grouping and aggregations

- `GROUP BY le.specimen_id` produces one output row per lab specimen ID.
- Aggregate expressions are:
  - `MAX(subject_id)` → output `subject_id`;
  - `MAX(hadm_id)` → output `hadm_id`;
  - `MAX(charttime)` → output `charttime`;
  - `MAX(CASE WHEN itemid = 51003 THEN valuenum ELSE NULL END)` →
    `troponin_t`;
  - `MAX(CASE WHEN itemid = 50911 THEN valuenum ELSE NULL END)` → `ck_mb`;
  - `MAX(CASE WHEN itemid = 50963 THEN valuenum ELSE NULL END)` → `ntprobnp`.
- There are no window functions, `MIN`, `AVG`, `SUM`, `ARRAY_AGG`, or other
  aggregations.
- The `MAX` operations make the selected ID/time and each analyte value the
  maximum among qualifying rows within a specimen group; they are not
  selecting the first row by time.

## Literal code set (verbatim)

The active coded predicate is on `mimiciv_hosp.labevents.itemid`. The literals
are reproduced exactly as written, including SQL ordering and comments:

```sql
WHERE le.itemid IN
    (
        -- 51002, -- Troponin I (troponin-I is not measured in MIMIC-IV)
        -- 52598, -- Troponin I, point of care, rare/poor quality
        51003 -- Troponin T
        , 50911  -- Creatinine Kinase, MB isoenzyme
        , 50963 -- N-terminal (NT)-pro hormone BNP (NT-proBNP) 
    )
```

Active code-to-output feeds:

| Exact literal | Source table and column filtered | Output expression / column fed |
|---|---|---|
| `51003` | `mimiciv_hosp.labevents.itemid` | `CASE` feeding `troponin_t`, then `MAX` |
| `50911` | `mimiciv_hosp.labevents.itemid` | `CASE` feeding `ck_mb`, then `MAX` |
| `50963` | `mimiciv_hosp.labevents.itemid` | `CASE` feeding `ntprobnp`, then `MAX` |

The SQL also contains commented-out code literals `51002` and `52598` in the
same `IN` list. They are not active predicate values, do not feed any output
column, and must not be treated as returned code streams. The comments label
them as Troponin I and point-of-care Troponin I respectively.

No ICD code, ICD version, CPT/HCPCS code, unit code, or other coded filter is
present. The SQL contains no explicit coding-system URI. The cross-concept
notes identify labevents item IDs as the `mimic-d-labitems` code-system stream;
the source specification itself is the exact numeric `itemid` set above.

## Dependencies

- No `mimiciv_derived` dependency.
- No dependency on another concept's derived output.
- Only raw source dependency: `mimiciv_hosp.labevents`.

## Notes checked

Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`. Relevant established notes
for this source are that lab Observation codes preserve the source itemid
verbatim, lab specimen references preserve `labevents.specimen_id` for the
grouping spine, and lab Observation encounter references are incomplete. These
notes do not alter the canonical SQL: this source query has no encounter join
and groups directly by `specimen_id`.
