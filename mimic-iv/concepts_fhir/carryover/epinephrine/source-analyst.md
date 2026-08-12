# Source analysis: epinephrine

## Scope and provenance

- Concept stem: `epinephrine`.
- Canonical SQL: `mimic-iv/concepts/medication/epinephrine.sql`.
- The SQL source SHA256 is
  `97c1c3cf8c549fb7546c85c7a66902911cc217fd39fd29b3a15070e83d6a2e5a`, matching
  the `epinephrine` node in
  `mimic-iv/concept_dag/concept_dag.json`.
- The DAG places this concept at level `0`, with no dependencies. Its listed
  dependents are `first_day_sofa`, `sofa`, and `vasoactive_agent`; these are
  consumers, not dependencies of this source query.
- The analysis is static. No relational or FHIR SQL was executed and no data
  presence/absence claim was inferred from a query run.

## SQL behavior

The query is a single final `SELECT` with no CTE. In source order it projects
`stay_id`, `linkorderid`, `rate AS vaso_rate`, `amount AS vaso_amount`,
`starttime`, and `endtime` from ICU `inputevents`, retaining only rows whose
`itemid` is exactly `221289` (the SQL comment labels that item as
`epinephrine`). It performs no value conversion, unit conversion, deduplication,
ordering, or aggregation.

The source comments say:

- `-- This query extracts dose+durations of epinephrine administration`
- `-- Local hospital dosage guidance: 0.2 mcg/kg/min (low) - 2 mcg/kg/min (high)`
- `-- all rows in mcg/kg/min`

Those comments are documentation only. The SQL does not filter on the stated
dosage range, does not filter on `rateuom`, and does not project a unit column or
perform a rate conversion.

## 1. Table references

| SQL clause | Source schema | Table | Alias | Role |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `mimiciv_icu` | `inputevents` | none | Sole source of all selected and filtered values |

The project-qualified BigQuery-style name in the canonical SQL resolves to the
raw MIMIC-IV ICU table `mimiciv_icu.inputevents` for the port. There are no
other `FROM` or `JOIN` clauses. `mimiciv_icu.d_items` is the dimension referenced
by the raw-schema foreign-key metadata for `inputevents.itemid`, but it is not
referenced or joined by this query.

## 2. Column inventory and inferred types

The source-schema types below follow the MIMIC-IV PostgreSQL DDL in
`mimic-iv/buildmimic/postgres/create.sql:449-474`; the output type names are also
confirmed by the epinephrine entry in
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.

### Columns referenced by the SQL

| Source column | Source type / nullability | Output name | Output type | Use |
|---|---|---|---|---|
| `stay_id` | `INTEGER`, nullable in `inputevents` | `stay_id` | `INTEGER` | Final projection; ICU-stay identifier |
| `linkorderid` | `INTEGER`, nullable | `linkorderid` | `INTEGER` | Final projection; input-event linkage value |
| `rate` | `FLOAT`, nullable | `vaso_rate` | `FLOAT` | Final projection; direct alias, no arithmetic |
| `amount` | `FLOAT`, nullable | `vaso_amount` | `FLOAT` | Final projection; direct alias, no arithmetic |
| `starttime` | `TIMESTAMP`, `NOT NULL` in the raw DDL | `starttime` | `TIMESTAMP` | Final projection; administration interval start |
| `endtime` | `TIMESTAMP`, `NOT NULL` in the raw DDL | `endtime` | `TIMESTAMP` | Final projection; administration interval end |
| `itemid` | `INTEGER`, `NOT NULL` | not projected | not applicable | Equality filter selecting the epinephrine stream |

There are no intermediate CTE columns. The final output schema and column order
are exactly:

```text
stay_id INTEGER
linkorderid INTEGER
vaso_rate FLOAT
vaso_amount FLOAT
starttime TIMESTAMP
endtime TIMESTAMP
```

`itemid` is intentionally absent from the output even though it defines the
stream. The query also does not project `subject_id`, `hadm_id`, `orderid`,
`rateuom`, `amountuom`, `patientweight`, or any other `inputevents` columns.

## 3. Filters

There is one `WHERE` predicate:

```sql
WHERE itemid = 221289 -- epinephrine
```

This is an exact equality filter. It has no time window, no `rate` or `amount`
constraint, no unit constraint, no NULL test, no exclusion list, and no other
code predicate. Because there is no `CASE`, cast, or arithmetic expression, the
selected `rate`, `amount`, `starttime`, and `endtime` values are passed through
unchanged.

The dosage values in the comments (`0.2` and `2`) are not SQL predicates and are
not part of the coded filter specification. The comment's unit text is likewise
not an executable filter.

## 4. Joins

There are no joins, so there are no INNER, LEFT, or other join conditions. The
inputevents foreign keys to patients, admissions, ICU stays, and `d_items` are
schema metadata only; the query does not use them to enrich or restrict rows.

## 5. `mimiciv_derived` dependencies

None. The SQL contains no reference to the `mimiciv_derived` schema, and the DAG
records `dependencies: []`. No other concept needs to be ported first for
`epinephrine` itself.

## 6. Aggregations and row/cardinality behavior

- No `GROUP BY`.
- No aggregate functions (`MIN`, `MAX`, `AVG`, `ARRAY_AGG`, etc.).
- No window functions.
- No `DISTINCT`, `ORDER BY`, or explicit deduplication.
- Cardinality is one output row for each raw `inputevents` row satisfying
  `itemid = 221289`; the filter is the only row-reducing operation.
- Multiple matching administration rows are therefore retained as separate
  rows if they exist in the source. NULL-valued projected source fields are not
  filtered out by this SQL (while the raw DDL declares `starttime` and `endtime`
  non-null).

The raw `inputevents` primary key is `(orderid, itemid)` according to
`mimic-iv/buildmimic/postgres/constraint.sql:162-167`. Since the filter fixes
`itemid`, `orderid` would identify a source row within this stream, but
`orderid` is not selected. `linkorderid` is nullable and is not declared as a
primary or unique key, so it must not be assumed to identify one row by itself.
The projected output consequently has no key declared by the SQL and can have
duplicate projected tuples even though the raw rows have a primary key.

For the immutable full oracle, the manifest records the empirically usable
comparison key as `["linkorderid", "starttime"]`, with `comparison: "keyed_join"`
and `row_count: 24470`. This is a target-data observation, not a key declaration
in the SQL; the comparator's key remains manifest-driven rather than inferred
from the query text.

## 7. Literal code specification (verbatim)

This is the complete coded-filter set named by the SQL. The literal is copied
without normalization or substitution.

| Code field | Exact operator/literal | Source table filtered | Feeds |
|---|---|---|---|
| `itemid` | `= 221289` | `mimiciv_icu.inputevents` | The final row set; every final output column (`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`) is fed only by rows passing this predicate |

The SQL comment `-- epinephrine` is a label for the literal and is not a second
code. No `icd_code`, `icd_version`, or other coded system is filtered. No
expected-absent/dead-filter classification was made because this static source
analysis did not probe the served data; `221289` is nevertheless the exact code
the prober and implementer must preserve.

## Coding-system facts and boundaries

The source uses the proprietary MIMIC ICU `itemid` coding dimension: the raw
schema declares `inputevents.itemid INTEGER` and a foreign key to
`mimiciv_icu.d_items.itemid`. The SQL itself names no FHIR URI, ICD coding
system, terminology service, or translated label. Under the repository coding
policy, the port must carry the exact source literal `221289`; mapping that
literal to a different code or expanding the set would change the source
specification. Determining the FHIR resource/path and its served coding-system
URI is downstream prober work and is not asserted here.

## Relevant read-only handoff notes (not source-SQL semantics)

The following are downstream leads from the repository notes and must be
verified by the FHIR prober rather than treated as facts established by this
source analysis:

- The shared coding policy says itemid-derived streams retain the itemid value
  verbatim and must be discriminated by coding system plus exact code, not by
  `meta.profile` (`MIMIC_NOTES.md`, itemid section).
- The provisional `dobutamine` and `dopamine` fragments report that ICU
  MedicationAdministration resources do not expose `inputevents.linkorderid`,
  that ICU inputevent `effective[x]` is conditional on whether `rate` is null,
  and that served dosage quantities have decimal scale six. These may affect
  how `linkorderid`, `starttime`, `endtime`, `vaso_rate`, and `vaso_amount` can
  be represented for epinephrine, but they do not alter the oracle SQL.
- The shared notes also warn that FHIR datetimes carry offsets and that
  upstream TIMESTAMPTZ conversion can irreversibly normalize DST-gap wall times;
  this is relevant to later exact timestamp comparison, not a filter or
  transformation performed by `epinephrine.sql`.

## Handoff summary

Implementer/prober must reproduce a six-column, non-aggregated ICU inputevent
stream filtered only by the verbatim itemid `221289`. Preserve one row per
matching source event and the direct aliases `rate -> vaso_rate` and
`amount -> vaso_amount`; do not introduce unit/range filters, joins, rate
conversion, or deduplication. There are no `mimiciv_derived` prerequisites.
