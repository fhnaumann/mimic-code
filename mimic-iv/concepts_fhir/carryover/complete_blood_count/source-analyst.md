# Source analysis: `complete_blood_count`

## Source and DAG identity

- Concept stem: `complete_blood_count`.
- Canonical SQL: `mimic-iv/concepts/measurement/complete_blood_count.sql`.
- The DAG node path is `measurement/complete_blood_count.sql`; its recorded
  SHA-256 is
  `8eb94ba8891e0effa66c7a62c76e648d9f42e8941f97f052c92a0823434bae92`.
  The hash was recomputed from the canonical SQL and matches the DAG.
- DAG level: 0.
- DAG dependencies: none (`dependencies: []`).
- The SQL contains no reference to `mimiciv_derived`, so there is no derived
  concept that must be ported first. The DAG lists `first_day_lab`, `sapsii`,
  and `sofa` as dependents, but they are not inputs to this concept.

## Query shape and table references

The query has no CTEs and no intermediate query blocks. Its only relational
source clause is:

```sql
FROM `physionet-data.mimiciv_hosp.labevents` le
```

This is the raw `mimiciv_hosp.labevents` table, aliased `le`. There are no
`JOIN` clauses and no `mimiciv_icu` tables. The `physionet-data` prefix is the
BigQuery project qualifier; the logical source schema is `mimiciv_hosp` and
the table is `labevents`.

## Source column inventory

The PostgreSQL build DDL gives the following source types. Unqualified
references to `itemid` and `valuenum` resolve to `le` because it is the only
source table.

| Source column | Source type | Use in SQL | Output consequence |
|---|---|---|---|
| `le.subject_id` | `INTEGER NOT NULL` | `MAX(subject_id)` | `subject_id` |
| `le.hadm_id` | `INTEGER` (nullable) | `MAX(hadm_id)` | `hadm_id` |
| `le.charttime` | `TIMESTAMP(0)` (nullable) | `MAX(charttime)` | `charttime` |
| `le.specimen_id` | `INTEGER NOT NULL` | selected directly and `GROUP BY le.specimen_id` | `specimen_id`, the grouping/natural key |
| `le.itemid` | `INTEGER NOT NULL` | item-code `IN` filter and ten conditional pivots | not output directly; selects the analyte column receiving `valuenum` |
| `le.valuenum` | `DOUBLE PRECISION` (nullable) | `CASE` payload and `IS NOT NULL` / `> 0` filters | numeric analyte values, each `DOUBLE` in the output |

No other `labevents` columns are referenced: in particular, `value`,
`valueuom`, `flag`, `comments`, `labevent_id`, and the other dimension columns
are not selected or filtered.

## Exact filters and literal code set

The complete `WHERE` clause is:

```sql
WHERE le.itemid IN
    (
        51221 -- hematocrit
        , 51222 -- hemoglobin
        , 51248 -- MCH
        , 51249 -- MCHC
        , 51250 -- MCV
        , 51265 -- platelets
        , 51279 -- RBC
        , 51277 -- RDW
        , 52159 -- RDW SD
        , 51301  -- WBC
    )
    AND valuenum IS NOT NULL
    -- lab values cannot be 0 and cannot be negative
    AND valuenum > 0
```

### Verbatim itemid specification

These are the exact literals, in the exact order named by the SQL. Every set
filters `mimiciv_hosp.labevents.itemid`; there is no `d_labitems` join. Each
literal feeds the output column shown below through a conditional `MAX`:

| Verbatim `itemid` literal | SQL label/comment | Output column fed |
|---:|---|---|
| `51221` | `hematocrit` | `hematocrit` |
| `51222` | `hemoglobin` | `hemoglobin` |
| `51248` | `MCH` | `mch` |
| `51249` | `MCHC` | `mchc` |
| `51250` | `MCV` | `mcv` |
| `51265` | `platelets` | `platelet` |
| `51279` | `RBC` | `rbc` |
| `51277` | `RDW` | `rdw` |
| `52159` | `RDW SD` | `rdwsd` |
| `51301` | `WBC` | `wbc` |

The code set is an itemid set, not an ICD set; the canonical SQL names no ICD
codes or other coded fields. The SQL itself does not name a FHIR coding
system. Per the repository coding policy and the curated lab notes, the
corresponding itemid-derived FHIR Observation stream uses the exact itemid as
the code under the MIMIC lab-item code system; no translation or label-based
substitution is part of this source query.

The non-code predicates are both value constraints and apply to every row
before grouping:

1. `valuenum IS NOT NULL` excludes rows without a relational numeric value.
2. `valuenum > 0` excludes zero and negative numeric values.

There is no time-window predicate, no admission-window predicate, no
`hadm_id`/`subject_id` restriction, and no separate code exclusion. The only
code restriction is the positive `itemid IN (...)` set above.

## Joins and dependencies

- Joins: none. Consequently, there are no join types or join conditions to
  preserve.
- `mimiciv_derived` dependencies: none.
- Dimension lookups: none. Although the itemids correspond to lab-item
  definitions, the canonical SQL reads only `labevents` and does not join
  `d_labitems` for labels or coding metadata.

## Aggregation and row formation

The query groups by:

```sql
GROUP BY le.specimen_id
```

It uses no window functions and no `MIN`, `AVG`, `ARRAY_AGG`, or other
aggregates besides `MAX`. The aggregate expressions are:

- `MAX(subject_id)` → `subject_id`;
- `MAX(hadm_id)` → `hadm_id`;
- `MAX(charttime)` → `charttime`;
- `MAX(CASE WHEN itemid = <literal> THEN valuenum ELSE NULL END)` for each
  of the ten itemids, producing the ten analyte columns in the literal-set
  table above.

Thus the SQL forms one row per `specimen_id` among filtered positive numeric
target-item rows. Each conditional aggregate is the maximum matching
`valuenum` for that specimen and itemid; if a specimen has no matching row for
one of the ten itemids, that analyte expression is `NULL`. The `MAX` expressions
for the identifiers and `charttime` similarly select the maximum non-null
value within the specimen group. There is no `ORDER BY`.

## Final output schema and natural key

The immutable full-oracle manifest records a keyed comparison with natural key
`specimen_id`, and the source `GROUP BY` uses that same column. The target
schema, in final select order, is:

| Output column | Type in oracle manifest | Expression |
|---|---|---|
| `subject_id` | `INTEGER` | `MAX(subject_id)` |
| `hadm_id` | `INTEGER` | `MAX(hadm_id)` |
| `charttime` | `TIMESTAMP` | `MAX(charttime)` |
| `specimen_id` | `INTEGER` | `le.specimen_id` |
| `hematocrit` | `DOUBLE` | conditional `MAX` for `itemid = 51221` |
| `hemoglobin` | `DOUBLE` | conditional `MAX` for `itemid = 51222` |
| `mch` | `DOUBLE` | conditional `MAX` for `itemid = 51248` |
| `mchc` | `DOUBLE` | conditional `MAX` for `itemid = 51249` |
| `mcv` | `DOUBLE` | conditional `MAX` for `itemid = 51250` |
| `platelet` | `DOUBLE` | conditional `MAX` for `itemid = 51265` |
| `rbc` | `DOUBLE` | conditional `MAX` for `itemid = 51279` |
| `rdw` | `DOUBLE` | conditional `MAX` for `itemid = 51277` |
| `rdwsd` | `DOUBLE` | conditional `MAX` for `itemid = 52159` |
| `wbc` | `DOUBLE` | conditional `MAX` for `itemid = 51301` |

The manifest reports `comparison: keyed_join`, key `specimen_id`, and a full
oracle row count of `3,362,503`. The natural-key fact is from the immutable
manifest's empirical key discovery; the SQL-level grouping fact is directly
visible in the canonical query.

## Notes consulted and their relevance

- `MIMIC_NOTES.md` confirms that lab Observation codes preserve the source
  itemid verbatim, that lab Observations have a specimen reference suitable
  for the specimen grouping spine, and that `d_labitems` has no v2.2 LOINC
  mapping. It also records incomplete lab Observation encounter references
  and comparator/text synthesis behavior; those are downstream FHIR-port
  concerns, not predicates in this source SQL.
- `MIMIC_NOTES.d/blood_differential.md` was treated as a provisional lead. It
  warns that FHIR may synthesize a Quantity from comparator text when source
  `valuenum` is NULL, which must not be confused with this SQL's explicit
  `valuenum IS NOT NULL` filter.
- `MIMIC_NOTES.d/chemistry.md` and `MIMIC_NOTES.d/coagulation.md` were treated
  as provisional leads for lab datetime and numeric-Quantity handling. They
  do not alter the canonical source filters or schema.
- `MIMIC_NOTES.d/cardiac_marker.md` was treated as a provisional lead for
  exact string/system filtering of itemid-derived FHIR codes. It does not add
  or remove any itemid from this SQL's literal set.
- No `complete_blood_count` fragment exists yet, and no notes fragment was
  modified.
