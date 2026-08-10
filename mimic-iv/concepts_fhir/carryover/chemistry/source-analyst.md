# Source analysis: `chemistry`

## Source and DAG identity

- Concept stem: `chemistry`.
- Canonical SQL: `mimic-iv/concepts/measurement/chemistry.sql`.
- The DAG node gives path `measurement/chemistry.sql`, level `0`, SHA-256
  `b674ae2e12fe859c44850a5e8268f3a18ccb934fb9f0ab47112af0c346364d70`, and
  `dependencies: []`.
- The DAG lists `creatinine_baseline`, `first_day_lab`, `sapsii`, and `sofa` as
  dependents. Chemistry itself has no `mimiciv_derived` dependency.
- `uv run mimic_utils concept_dag --check` reported that the stored JSON and
  Markdown DAG artifacts match. The SHA-256 of the canonical SQL independently
  matched the DAG value.
- The SQL is one query (85 lines), with no CTE and no subquery.

## Table references

There is one table reference and no joins:

| SQL clause | Schema | Table | Alias |
|---|---|---|---|
| `FROM \`physionet-data.mimiciv_hosp.labevents\` le` | `mimiciv_hosp` | `labevents` | `le` |

The `physionet-data` prefix is a project/catalog qualifier; the MIMIC schema is
`mimiciv_hosp`. No `mimiciv_icu` or `mimiciv_derived` table is referenced. The
DAG's external-table entry also records only `mimiciv_hosp.labevents` for this
concept.

## Source columns and inferred types

The PostgreSQL source DDL (`mimic-iv/buildmimic/postgres/create.sql`) defines the
referenced `labevents` columns as follows. The unqualified `itemid` and
`valuenum` references in the query resolve to `le.itemid` and `le.valuenum`
because `le` is the only table.

| Source column | Inferred source type | How the SQL uses it |
|---|---|---|
| `le.subject_id` | `INTEGER NOT NULL` | `MAX` into output `subject_id` |
| `le.hadm_id` | `INTEGER` nullable | `MAX` into output `hadm_id` |
| `le.charttime` | `TIMESTAMP(0)` nullable | `MAX` into output `charttime` |
| `le.specimen_id` | `INTEGER NOT NULL` | Selected directly and used by `GROUP BY` |
| `le.itemid` | `INTEGER NOT NULL` | Active item-code filter, CASE discriminators, and the anion-gap exception |
| `le.valuenum` | `DOUBLE PRECISION` nullable | Non-null/positivity filter and numeric CASE values/upper bounds |

There are no references to `value`, `valueuom`, `comments`, `storetime`,
`labevent_id`, dimension-table columns, or any other `labevents` column.

## Final output columns and types

The final row shape is in this order:

| Output column | SQL expression | Inferred output type and nullability |
|---|---|---|
| `subject_id` | `MAX(subject_id)` | `INTEGER`; non-null for an eligible group because the source column is non-null |
| `hadm_id` | `MAX(hadm_id)` | `INTEGER`; nullable |
| `charttime` | `MAX(charttime)` | `TIMESTAMP(0)`; nullable |
| `specimen_id` | `le.specimen_id` | `INTEGER`; grouping key and non-null in the source DDL |
| `albumin` | `MAX(CASE WHEN itemid = 50862 AND valuenum <= 10 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `globulin` | `MAX(CASE WHEN itemid = 50930 AND valuenum <= 10 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `total_protein` | `MAX(CASE WHEN itemid = 50976 AND valuenum <= 20 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `aniongap` | `MAX(CASE WHEN itemid = 50868 AND valuenum <= 10000 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `bicarbonate` | `MAX(CASE WHEN itemid = 50882 AND valuenum <= 10000 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `bun` | `MAX(CASE WHEN itemid = 51006 AND valuenum <= 300 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `calcium` | `MAX(CASE WHEN itemid = 50893 AND valuenum <= 10000 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `chloride` | `MAX(CASE WHEN itemid = 50902 AND valuenum <= 10000 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `creatinine` | `MAX(CASE WHEN itemid = 50912 AND valuenum <= 150 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `glucose` | `MAX(CASE WHEN itemid = 50931 AND valuenum <= 10000 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `sodium` | `MAX(CASE WHEN itemid = 50983 AND valuenum <= 200 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |
| `potassium` | `MAX(CASE WHEN itemid = 50971 AND valuenum <= 30 THEN valuenum ELSE NULL END)` | `DOUBLE PRECISION`; nullable |

All analyte outputs are nullable because each is a conditional aggregate. A
row can remain in the result while a source value is converted to NULL by that
analyte's upper-bound test.

## Filters

The query has one active item-code set, a non-null value predicate, and a
positivity predicate:

1. `le.itemid IN (...)` restricts rows to the twelve active chemistry itemids
   copied below.
2. `valuenum IS NOT NULL` excludes rows without a numeric value.
3. `(valuenum > 0 OR itemid = 50868)` excludes zero and negative values for
   every selected item except anion gap (`50868`). For `50868`, any non-null
   value passes this lower-bound predicate, including zero and negative values.
4. Each CASE has an analyte-specific upper bound. These bounds affect the
   value placed in that output column, not row eligibility: an included row
   above a bound still contributes to its `specimen_id` group, but contributes
   NULL to that analyte's aggregate.

There is no time window, date filter, unit filter, text-value filter, admission
filter, code exclusion predicate, or explicit blood-gas predicate. The comments
state that point-of-care tests are excluded and blood gases are handled by
`bg.sql`; operationally, this query achieves that through its active itemid
list. The point-of-care entries shown commented out below are not SQL filters.

## Literal code specification

The active itemid filter is on `mimiciv_hosp.labevents.itemid`, and the exact
SQL list (including its source comments) is:

```sql
WHERE le.itemid IN
    (
        -- comment is: LABEL | CATEGORY | FLUID | NUMBER OF ROWS IN LABEVENTS
        50862 -- ALBUMIN | CHEMISTRY | BLOOD | 146697
        , 50930 -- Globulin
        , 50976 -- Total protein
        -- 52456, -- Anion gap, point of care test
        , 50868 -- ANION GAP | CHEMISTRY | BLOOD | 769895
        , 50882 -- BICARBONATE | CHEMISTRY | BLOOD | 780733
        , 50893 -- Calcium
        -- 52502, Creatinine, point of care
        , 50912 -- CREATININE | CHEMISTRY | BLOOD | 797476
        , 50902 -- CHLORIDE | CHEMISTRY | BLOOD | 795568
        , 50931 -- GLUCOSE | CHEMISTRY | BLOOD | 748981
        -- 52525, Glucose, point of care
        -- 52566, -- Potassium, point of care
        , 50971 -- POTASSIUM | CHEMISTRY | BLOOD | 845825
        -- 52579, -- Sodium, point of care
        , 50983 -- SODIUM | CHEMISTRY | BLOOD | 808489
        -- 52603, Urea, point of care
        , 51006  -- UREA NITROGEN | CHEMISTRY | BLOOD | 791925
    )
```

The effective code-to-output feeds, all from the same source column
`mimiciv_hosp.labevents.itemid`, are:

| Exact itemid literal | Output column fed by its CASE |
|---:|---|
| `50862` | `albumin` |
| `50930` | `globulin` |
| `50976` | `total_protein` |
| `50868` | `aniongap` |
| `50882` | `bicarbonate` |
| `51006` | `bun` |
| `50893` | `calcium` |
| `50902` | `chloride` |
| `50912` | `creatinine` |
| `50931` | `glucose` |
| `50983` | `sodium` |
| `50971` | `potassium` |

The exact coded predicates in the CASE expressions are:

```sql
itemid = 50862 AND valuenum <= 10       -- feeds albumin
itemid = 50930 AND valuenum <= 10       -- feeds globulin
itemid = 50976 AND valuenum <= 20       -- feeds total_protein
itemid = 50868 AND valuenum <= 10000    -- feeds aniongap
itemid = 50882 AND valuenum <= 10000    -- feeds bicarbonate
itemid = 51006 AND valuenum <= 300      -- feeds bun
itemid = 50893 AND valuenum <= 10000    -- feeds calcium
itemid = 50902 AND valuenum <= 10000    -- feeds chloride
itemid = 50912 AND valuenum <= 150      -- feeds creatinine
itemid = 50931 AND valuenum <= 10000    -- feeds glucose
itemid = 50983 AND valuenum <= 200      -- feeds sodium
itemid = 50971 AND valuenum <= 30       -- feeds potassium
```

The additional exact code predicate is the lower-bound exception in the
`WHERE` clause:

```sql
valuenum > 0 OR itemid = 50868
```

Here `50868` is the same exact `mimiciv_hosp.labevents.itemid` literal feeding
the `aniongap` output. The following literals occur only in SQL comments and
must not be added to the effective port filter: `52456`, `52502`, `52525`,
`52566`, `52579`, and `52603`. No ICD code, `icd_version`, LOINC code, or other
standard code is named by this SQL. No dead active itemid filter was identified
in this source; no data probe was performed to reclassify any active itemid as
present or absent.

For downstream FHIR representation, the read coding policy and curated notes
identify labevents itemids as verbatim string codes in
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`. That is the
corresponding itemid coding system, not a translation or an expansion of the
SQL's code set; the exact twelve numeric literals above remain the specification.

## Joins

There are no `JOIN` clauses, so there are no INNER or LEFT join conditions and
no join-induced row multiplication or loss in the canonical query.

## Aggregation, grouping, and natural-key implications

- `GROUP BY le.specimen_id` is the only grouping operation.
- The query uses `MAX` for `subject_id`, `hadm_id`, `charttime`, and every
  analyte CASE expression. There are no window functions, `MIN`, `AVG`,
  `ARRAY_AGG`, `DISTINCT`, or ordering operations.
- The result has at most one row per source `specimen_id` that has at least one
  selected itemid with non-null `valuenum` and that passes the global positivity
  predicate. It is a wide specimen-level pivot, not one row per `labevent_id`
  or per itemid.
- `specimen_id` is the SQL grouping key and the natural-key candidate. The SQL
  does not declare a uniqueness constraint for its result, and the port loop's
  natural key is discovered empirically rather than parsed from SQL. The source
  labevents primary key is `labevent_id`, but that key is not selected and is
  intentionally collapsed by this query.
- The grouping key does not include `subject_id`, `hadm_id`, or `charttime`.
  The query assumes those values are consistent within a specimen; if multiple
  values occur, `MAX` selects the maximum rather than preserving the source
  row-level alternatives. The same collapse applies when multiple qualifying
  rows for one itemid occur within a specimen: the maximum value satisfying
  that CASE's upper bound is emitted.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` records `Observation.specimen` to
  `Specimen.identifier` as the lab specimen spine. It also records that lab
  `Observation.encounter` is incomplete, so a downstream FHIR port that tries
  to populate this SQL's nullable `hadm_id` should use a LEFT join and must not
  drop observations merely because an Encounter reference is absent. The source
  SQL itself has no such join.

## Dependencies and relevant read-surface findings

- There is no `mimiciv_derived` reference, so no other concept must be ported
  before `chemistry` on account of this SQL. The only raw dependency is
  `mimiciv_hosp.labevents`.
- The curated notes state that lab Observation code values preserve the source
  itemid verbatim and that the specimen reference preserves `specimen_id`.
  They also state that lab Quantity aliases may need numeric casting in a FHIR
  implementation. These are representation implications, not changes to the
  source SQL or its code specification.
- The `cardiac_marker` and `blood_differential` fragments were read as
  provisional, concept-specific notes. Their warnings about filtering lab code
  strings with the lab code system and about text-derived Quantity values do not
  add any chemistry itemids or alter this source query; chemistry filters only
  non-null relational `valuenum` and does not use source text.
