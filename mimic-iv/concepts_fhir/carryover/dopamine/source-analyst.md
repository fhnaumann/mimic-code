# Source analysis: dopamine

## Scope and source identity

- Concept stem: `dopamine`.
- DAG path: `medication/dopamine.sql`.
- Canonical source: `mimic-iv/concepts/medication/dopamine.sql`.
- The canonical SQL SHA256 is
  `4809121abcd1bd3d827a3025b7427f959dc99a53bbbee7dbe109c957145ff74d`,
  matching the `dopamine` node in `mimic-iv/concept_dag/concept_dag.json`.
- The query comment says it extracts dopamine administration dose and duration;
  the comment's local dosage guidance (`2 mcg/kg/min` low to `10 mcg/kg/min`
  high) is descriptive only and is not a SQL predicate.
- The inline comment beside `rate` says `-- all rows in mcg/kg/min`; this is
  unit context only. The SQL neither selects nor filters `rateuom` (and does not
  select or filter `amountuom`).

## SQL structure

The SQL is a single final `SELECT` with no CTEs, subqueries, `DISTINCT`, or
intermediate relations:

```sql
SELECT
    stay_id, linkorderid
    , rate AS vaso_rate
    , amount AS vaso_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid = 221662 -- dopamine
```

### Table references

| SQL clause | Catalog/project | Schema | Table | Alias |
|---|---|---|---|---|
| `FROM` | `physionet-data` | `mimiciv_icu` | `inputevents` | none |

There are no other `FROM` or `JOIN` clauses. The source is the raw ICU
`mimiciv_icu.inputevents` table; no `mimiciv_hosp` table and no
`mimiciv_derived` table is referenced.

## Columns and inferred types

The source column types below are taken from the MIMIC-IV PostgreSQL DDL in
`mimic-iv/buildmimic/postgres/create.sql:450-478`. Aliases preserve the source
type.

| Source table | Source column | Use | Output name | Inferred/source type | Source nullability |
|---|---|---|---|---|---|
| `mimiciv_icu.inputevents` | `stay_id` | selected | `stay_id` | `INTEGER` | nullable |
| `mimiciv_icu.inputevents` | `linkorderid` | selected | `linkorderid` | `INTEGER` | nullable |
| `mimiciv_icu.inputevents` | `rate` | selected | `vaso_rate` | `FLOAT` | nullable |
| `mimiciv_icu.inputevents` | `amount` | selected | `vaso_amount` | `FLOAT` | nullable |
| `mimiciv_icu.inputevents` | `starttime` | selected | `starttime` | `TIMESTAMP` | `NOT NULL` |
| `mimiciv_icu.inputevents` | `endtime` | selected | `endtime` | `TIMESTAMP` | `NOT NULL` |
| `mimiciv_icu.inputevents` | `itemid` | filter only | not output | `INTEGER` | `NOT NULL` |

There are no intermediate CTE columns. The final output column order and names
are exactly:

1. `stay_id` (`INTEGER`)
2. `linkorderid` (`INTEGER`)
3. `vaso_rate` (`FLOAT`), from `rate`
4. `vaso_amount` (`FLOAT`), from `amount`
5. `starttime` (`TIMESTAMP`)
6. `endtime` (`TIMESTAMP`)

`subject_id`, `hadm_id`, `orderid`, `rateuom`, `amountuom`, and every other
`inputevents` column are not selected or referenced by this SQL.

## Filters and literal code specification

There is exactly one executable `WHERE` predicate:

```sql
itemid = 221662
```

- Source table filtered: `mimiciv_icu.inputevents`.
- Coded field: ICU input-event `itemid` (an integer source identifier).
- Exact literal code set, verbatim: `221662`.
- SQL comment/label: `-- dopamine`; this is not an additional code or filter.
- Output fed: the predicate controls the final result row set, and therefore
  determines which rows feed all six final output columns; there is no CTE.

There are no additional predicates: no time window, no `starttime`/`endtime`
constraint, no rate or amount constraint, no null test, no order-status
constraint, no unit constraint, and no code exclusion. The SQL names no ICD
code, LOINC code, RxNorm/NDC code, or explicit coding-system URI. The only
literal code specification is the one `itemid` above; it must not be replaced
by the comment label or expanded with other dopamine-related itemids.

## Joins

There are no joins, so there are no join types or join conditions to preserve.
Each qualifying `inputevents` row is returned directly without an encounter,
patient, dimension-table, or derived-table join.

## Windows, aggregations, and ordering

- `GROUP BY`: none.
- Aggregate functions (`MIN`, `MAX`, `AVG`, `SUM`, `ARRAY_AGG`, etc.): none.
- Window functions: none.
- `ORDER BY`: none.
- Row limiting or deduplication: none.

The query is row-preserving for rows satisfying `itemid = 221662`; it does not
combine administrations or calculate dose/duration values despite the header
description. `vaso_rate` and `vaso_amount` are direct aliases, and
`starttime`/`endtime` are direct source timestamps.

## Natural-key implications

The full-oracle manifest
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` records this concept
as a `keyed_join` comparison with:

- natural/comparison key: `stay_id`, `starttime`;
- output schema: the six columns listed above, with types `INTEGER`, `INTEGER`,
  `FLOAT`, `FLOAT`, `TIMESTAMP`, `TIMESTAMP`;
- full-oracle row count: `16892`.

This is an empirical comparator key from the manifest, not a uniqueness claim
expressed by the SQL. The relational `inputevents` primary key is
`(orderid, itemid)` (`mimic-iv/buildmimic/postgres/constraint.sql:162-167`),
but `orderid` is omitted from the output and the fixed `itemid` is also not
selected. Consequently, the source table's declared row identity is not
carried through directly. `linkorderid`, `vaso_rate`, `vaso_amount`, and
`endtime` are payload columns rather than manifest key columns. The port must
retain the manifest's key shape for comparison and must not infer a different
key merely from the SQL.

Because `stay_id` and `linkorderid` are nullable in the source DDL, their
nullability is part of the source context; `starttime` and `endtime` are
declared non-null. The manifest's empirical key is nevertheless the one used
by the loop.

## DAG dependencies and downstream consumers

- DAG level: `0`.
- `dependencies`: `[]`.
- `mimiciv_derived` dependencies: none.
- DAG-listed dependents: `first_day_sofa`, `sofa`, and `vasoactive_agent`.

No other concept must be ported first for `dopamine`. The downstream concepts
may consume this six-column result, so preserving the output names, aliases,
types, row granularity, and itemid restriction is consequential for them.

## Mapping-relevant repository notes checked

I read `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`, the curated
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and all currently present fragments in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/`:
`README.md`, `complete_blood_count.md`, `coagulation.md`,
`cardiac_marker.md`, `blood_differential.md`, `code_status.md`, and
`chemistry.md`.

The fragments are specific to labevents/chartevents and do not add a
dopamine/inputevents source-SQL filter, join, or code. The curated notes do
contain general downstream mapping cautions relevant if the six source
columns are carried through FHIR: MIMIC IDs are emitted from
`identifier.value` as strings and need integer output typing; FHIR datetimes
carry offsets and should preserve MIMIC wall-clock values with
`TIMESTAMP_NTZ`; and `MedicationAdministration.effective[x]` can be
polymorphic, so both dateTime and Period-start representations may matter.
The medication-name/display and prescription notes concern FHIR medication
coding/prescription streams, not an additional source-SQL code for this
concept. These notes do not alter the canonical SQL facts above.

## Fact summary

`dopamine` is a dependency-free, single-table ICU input-event extraction. It
selects six direct values from `mimiciv_icu.inputevents` and retains every row
whose exact integer `itemid` is `221662`; it has no joins, time/value filters,
CTEs, windows, aggregations, or explicit FHIR/terminology coding system.
