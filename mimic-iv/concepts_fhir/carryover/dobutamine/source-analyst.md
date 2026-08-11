# Source analysis: dobutamine

## Scope and source identity

- Concept stem: `dobutamine`.
- Canonical SQL: `mimic-iv/concepts/medication/dobutamine.sql`.
- DAG node: path `medication/dobutamine.sql`, level `0`, SHA256
  `7b74249ebca27705ed5e31de753189c60a27e002a50c29745ff0bffee6e27ad5`.
- DAG dependencies: none (`dependencies: []`). Its listed dependents are
  `first_day_sofa`, `sofa`, and `vasoactive_agent`; these are not inputs to this
  concept.
- The SQL is one SELECT, with no CTEs or intermediate relations.

The executable query is:

```sql
SELECT
    stay_id, linkorderid
    , rate AS vaso_rate
    , amount AS vaso_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid = 221653 -- dobutamine
```

The comments describe dose guidance and units, but are not executable logic.
In particular, the query does not inspect or normalize `rateuom`.

## Table references

| SQL clause | Schema | Table | Join type |
|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `mimiciv_icu` | `inputevents` | base table; no join |

There are no `mimiciv_hosp` tables and no references to
`mimiciv_derived`. The DAG dependency list and the SQL both confirm that no
other concept must be ported first.

## Columns and inferred types

The source column types below are from the MIMIC-IV PostgreSQL DDL
(`buildmimic/postgres/create.sql:450-478`); the output types agree with the
full oracle manifest.

| Source column | Source type/nullability | Use in SQL | Final output column/type |
|---|---|---|---|
| `stay_id` | `INTEGER`, nullable in the source DDL | selected unchanged | `stay_id INTEGER` |
| `linkorderid` | `INTEGER`, nullable | selected unchanged | `linkorderid INTEGER` |
| `rate` | `FLOAT`, nullable | selected by alias | `vaso_rate FLOAT` |
| `amount` | `FLOAT`, nullable | selected by alias | `vaso_amount FLOAT` |
| `starttime` | `TIMESTAMP NOT NULL` | selected unchanged | `starttime TIMESTAMP` |
| `endtime` | `TIMESTAMP NOT NULL` | selected unchanged | `endtime TIMESTAMP` |
| `itemid` | `INTEGER NOT NULL` | `WHERE` predicate only; not selected | no output column |

There are no casts, CASE expressions, arithmetic transformations, or other
referenced columns. The exact final column order is:
`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`.

## Filters and literal code specification

The only WHERE predicate is:

```sql
WHERE itemid = 221653 -- dobutamine
```

Literal code set, copied verbatim:

| Source table filtered | Field/operator | Exact literal | Feeds |
|---|---|---|---|
| `mimiciv_icu.inputevents` | `itemid =` | `221653` | The final result row set and therefore all six final output columns; the itemid itself is not emitted |

This is an ICU `inputevents.itemid` filter. The SQL contains no ICD code,
`icd_version`, LOINC code, FHIR system URI, name substring, `IN`/`NOT IN` set,
time window, rate/amount/value constraint, NULL predicate, unit predicate, or
code exclusion. Do not replace the literal with a drug-name label or add
other itemids.

## Joins, aggregation, and row semantics

- Joins: none; consequently there are no join conditions or INNER/LEFT join
  choices.
- Aggregation: none; no `GROUP BY`, `HAVING`, `MIN`/`MAX`/`AVG`, array
  aggregation, or other value aggregation.
- Windowing: none; there are no window functions or ordering clauses.
- Each qualifying `inputevents` row is emitted once. `rate` and `amount` are
  passed through without unit conversion; `starttime` and `endtime` are also
  passed through unchanged.

The source table DDL declares its primary key as `(orderid, itemid)`, but
`orderid` is not selected. `linkorderid` is selected and is nullable, so it is
not the source primary key and is not established as a unique output key by
the SQL. The immutable full oracle manifest records an empirical keyed
comparison for this concept with natural key `(stay_id, starttime)`, 8,513
rows, and these six output columns/types. Thus the downstream comparator should
key on `stay_id` plus `starttime`, not on `linkorderid` alone or on the omitted
`orderid`; this key is a full-data manifest fact, not a key declaration in the
canonical SQL.

## Medication/Observation notes checked

I read `MIMIC_NOTES.md`, `MIMIC_NOTES.d/README.md`, and every existing fragment
relevant to Observation or medication terms:

- `MIMIC_NOTES.d/complete_blood_count.md`
- `MIMIC_NOTES.d/blood_differential.md`
- `MIMIC_NOTES.d/coagulation.md`
- `MIMIC_NOTES.d/cardiac_marker.md`
- `MIMIC_NOTES.d/code_status.md`
- `MIMIC_NOTES.d/chemistry.md`

No existing fragment contains a dobutamine/inputevents-specific finding. The
relevant curated notes are downstream mapping context, not source-SQL code:

- `MedicationAdministration.effective[x]` can be represented as either
  `effective.ofType(dateTime)` or `effective.ofType(Period).start`; a FHIR port
  should carry both and coalesce them.
- Medication name codings may have a null `Coding.display` while
  `Coding.code` remains readable; filtering on display is unsafe. This does not
  alter the source specification, whose exact identity filter is numeric
  `inputevents.itemid = 221653`.
- The curated Observation itemid rule says itemid-derived Observation codes are
  copied verbatim, but this source is `inputevents`, not an Observation table;
  the SQL itself names no FHIR coding-system URI.
- The prescription `Medication`/`MedicationRequest` notes and the
  `code_status` fragment's POE/MedicationRequest finding concern different
  source streams and do not add a dobutamine source dependency or filter.

## Summary

`dobutamine` is a level-0, dependency-free extraction from the single raw table
`mimiciv_icu.inputevents`. It retains rows with the one exact itemid literal
`221653`, selects six columns (two aliases), performs no joins, filters beyond
the itemid, time restriction, unit conversion, or aggregation, and has an
empirical full-data comparison key of `(stay_id, starttime)`.
