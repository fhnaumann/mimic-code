# Source analysis: `vasopressin`

## Scope and provenance

- Concept stem: `vasopressin`.
- Canonical SQL: `mimic-iv/concepts/medication/vasopressin.sql`.
- The DAG node is `medication/vasopressin.sql`, level `0`, with the listed
  SHA256 `13a5e11dd3a4275ffc64dc4f588c04773f6439889fabb2791a2f23edbed2e43b`.
- DAG dependencies are `[]`. The listed dependent is `vasoactive_agent`; it
  consumes this concept and is not a prerequisite for it.
- This is a static source analysis. No relational SQL or FHIR query was run,
  and no claim about the served row count or code presence was inferred from a
  data query.

The executable query, preserving the source literals and expressions, is:

```sql
SELECT
    stay_id, linkorderid
    , CASE WHEN rateuom = 'units/min' THEN rate * 60.0
        ELSE rate END AS vaso_rate
    , amount AS vaso_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid = 222315 -- vasopressin
```

The header comments describe dose/duration extraction and give local guidance
of `1.2 units/hour (low) - 2.4 units/hour (high)`. The comments also state that
three rows use units/min and the rest use units/hour. These are documentation
only: the executable SQL does not filter on the guidance range, validate the
unit population, or add a duration calculation.

## 1. Table references

| SQL clause | Catalog/project | Schema | Table | Alias | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `physionet-data` | `mimiciv_icu` | `inputevents` | none | Sole source of all selected and filtered values |

The project-qualified name resolves to the raw MIMIC-IV ICU table
`mimiciv_icu.inputevents`. There are no other `FROM` clauses and no `JOIN`
clauses. In particular, the SQL does not join `mimiciv_icu.d_items`,
`mimiciv_icu.icustays`, an admissions table, a patient table, or a derived
table. The `inputevents.itemid` relationship to `d_items` in schema metadata
does not make `d_items` a query dependency.

## 2. Column inventory and inferred types

The canonical BigQuery schema describes the integer fields as `INT64`, numeric
fields as `FLOAT64`, and the source times as `DATETIME`. The repository
PostgreSQL DDL/manifest uses the corresponding normalized names `INTEGER`,
`FLOAT`, and `TIMESTAMP`; the output types below use those manifest names.

| Source column | Source type / nullability | SQL use | Final output name | Inferred output type |
|---|---|---|---|---|
| `mimiciv_icu.inputevents.stay_id` | `INT64` / `INTEGER`, nullable | selected unchanged | `stay_id` | `INTEGER` |
| `mimiciv_icu.inputevents.linkorderid` | `INT64` / `INTEGER`, nullable | selected unchanged | `linkorderid` | `INTEGER` |
| `mimiciv_icu.inputevents.rateuom` | `STRING` / `VARCHAR(20)`, nullable | `CASE` discriminator: `rateuom = 'units/min'` | not emitted | — |
| `mimiciv_icu.inputevents.rate` | `FLOAT64` / `FLOAT`, nullable | direct value or multiplied by `60.0` | `vaso_rate` | `FLOAT` |
| `mimiciv_icu.inputevents.amount` | `FLOAT64` / `FLOAT`, nullable | selected unchanged | `vaso_amount` | `FLOAT` |
| `mimiciv_icu.inputevents.starttime` | `DATETIME` / `TIMESTAMP`, required | selected unchanged | `starttime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.endtime` | `DATETIME` / `TIMESTAMP`, required | selected unchanged | `endtime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.itemid` | `INT64` / `INTEGER`, required | equality filter | not emitted | — |

There are no intermediate CTEs or intermediate relation columns. The exact
final column order is:

```text
stay_id       INTEGER
linkorderid   INTEGER
vaso_rate     FLOAT
vaso_amount   FLOAT
starttime     TIMESTAMP
endtime       TIMESTAMP
```

`vaso_rate` is a floating-point `CASE` result. When the exact unit string is
matched, `rate * 60.0` converts the numerical rate to units/hour; otherwise the
source `rate` value is returned unchanged. `vaso_amount`, `starttime`, and
`endtime` are direct projections. The output does not include `itemid`,
`rateuom`, or an amount-unit column, so the source unit discriminator is not
retained as an output field even though it controls `vaso_rate`.

Other `inputevents` fields such as `subject_id`, `hadm_id`, `orderid`,
`amountuom`, `patientweight`, order-category fields, status fields, and
`totalamount` are not selected or referenced by this SQL.

## 3. Filters and value transformations

There is exactly one `WHERE` predicate:

```sql
WHERE itemid = 222315 -- vasopressin
```

It is an exact equality filter on the ICU input-event item identifier. There is
no time window, `starttime`/`endtime` validity test, rate or amount range,
NULL predicate, status predicate, exclusion list, or unit predicate in the
`WHERE` clause.

The `CASE` has a separate value transformation/discriminator, not a row
filter:

```sql
CASE WHEN rateuom = 'units/min' THEN rate * 60.0
     ELSE rate END AS vaso_rate
```

The exact string comparison is case-sensitive as written by the SQL dialect.
Rows whose `rateuom` is anything other than the exact string `'units/min'`,
including a NULL or unexpected unit value, take the `ELSE rate` branch. A NULL
`rate` remains NULL in either branch. The SQL does not trim `rateuom`, inspect
`amountuom`, or verify that the non-minute rows are units/hour. The multiplier
`60.0` is a numeric transformation constant, not a code.

## 4. Joins

There are no joins. Therefore there are no INNER, LEFT, or other join types and
no join conditions to preserve. Each qualifying raw `inputevents` row is
projected directly without enrichment from a dimension, encounter, patient,
or derived table.

## 5. `mimiciv_derived` dependencies

None. The canonical SQL contains no reference to the `mimiciv_derived` schema,
and the DAG records `dependencies: []`. No concept must be ported first for
`vasopressin`. `vasoactive_agent` is a downstream consumer and is not a
dependency of this concept.

## 6. Aggregations, windows, ordering, and cardinality

- No `GROUP BY` or `HAVING`.
- No aggregate functions such as `MIN`, `MAX`, `AVG`, `SUM`, or `ARRAY_AGG`.
- No window functions.
- No `DISTINCT`, `ORDER BY`, row limit, or explicit deduplication.
- The only row-reducing operation is `itemid = 222315`.
- Cardinality is one output row per raw `mimiciv_icu.inputevents` row that
  satisfies that item filter. Multiple matching input-event rows remain
  separate, and NULL `rate`, `amount`, `stay_id`, or `linkorderid` values are
  not excluded by this SQL. The raw schema declares `starttime` and `endtime`
  required.

The raw table primary key is `(orderid, itemid)` according to
`mimic-iv/buildmimic/postgres/constraint.sql:162-167`. The query fixes
`itemid` but does not select `orderid`, so it does not carry the declared raw
row identity into the output. `linkorderid` is nullable and is not declared
unique. Consequently, the six projected columns do not have a key declared by
the SQL and projected duplicate tuples are possible even though source rows
have a primary key.

The immutable oracle manifest records empirical comparison metadata for this
concept: `comparison: "keyed_join"`, key `("stay_id", "starttime")`,
`key_probes: 4`, and `row_count: 25892`. This is comparator alignment metadata,
not a uniqueness declaration made by the canonical SQL. It makes preservation
of ICU-stay identity and the exact source `starttime` especially important for
row alignment; `linkorderid` is an output payload field, not the manifest key.

## 7. Literal code specification, verbatim

This is the complete coded-filter set named by the SQL. The literal is copied
without normalization, expansion, or substitution.

| Source field | Exact SQL predicate/literal | Source table filtered | Output column or relation fed |
|---|---|---|---|
| `itemid` | `= 222315` | `mimiciv_icu.inputevents` | The final row set; therefore all six final output columns (`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`) are fed only by rows passing this predicate. `itemid` itself is not emitted. |

The SQL names no `icd_code`, `icd_version`, LOINC, RxNorm/NDC, or other
explicit terminology code. The source coding field is the MIMIC-IV ICU
`inputevents.itemid` integer, whose schema dimension is `mimiciv_icu.d_items`;
the dimension is not joined by this SQL. This static analysis did not probe
served data, so it does not classify `222315` as present or expected-absent.
The exact SQL literal remains the port specification.

The following is an exact non-code branch literal and is recorded separately
so it is not mistaken for an item-code set:

| Source field | Exact comparison/literal | Source table | Feeds |
|---|---|---|---|
| `rateuom` | `= 'units/min'` | `mimiciv_icu.inputevents` | The `THEN rate * 60.0` branch of output column `vaso_rate`; it does not filter rows. |

The source comments' `vasopressin` label, `1.2`, `2.4`, and `units/hour` text
are not executable code literals or predicates and must not be turned into
additional filters.

## 8. Semantically essential source inputs

This is a source-semantics inventory, not a terminal representability
decision. Each item below can affect inclusion, source identity, temporal
meaning, or a clinically meaningful output of the canonical query.

| Source input | Why it is essential | Branches/output controlled |
|---|---|---|
| `itemid` | The only row-inclusion discriminator. | Exact `itemid = 222315` selects the vasopressin stream and all six final output columns. |
| `rateuom` | Its exact value selects the only SQL transformation branch. | Exact `'units/min'` selects multiplication by `60.0`; every other value selects the unchanged `rate` branch for `vaso_rate`. |
| `rate` | The numerical administration rate is clinically meaningful and can be NULL. | Directly or after conversion feeds `vaso_rate`. |
| `amount` | The numerical administered amount is clinically meaningful and can be NULL. | Directly feeds `vaso_amount`. |
| `stay_id` | Associates the row with an ICU stay and is part of the empirical comparison key. | Output `stay_id`; row alignment at `(stay_id, starttime)`. |
| `starttime` | Defines the start of the administration interval and is part of the empirical comparison key. | Output `starttime`; temporal row identity/alignment. |
| `endtime` | Defines the interval end and therefore the duration represented by the source row. | Output `endtime`; downstream interval/duration interpretation. |
| `linkorderid` | Retained as a source linkage/order-group value in the canonical output. It is nullable and not unique. | Output `linkorderid`; it changes the output tuple but is not the SQL-defined or manifest key. |
| `orderid` | Not selected, but part of the raw primary key and can distinguish source rows that project to the same six-column values. | Raw row identity only; it controls neither a SQL branch nor a final output column. |

The SQL does not use `amountuom`, `patientweight`, `totalamount`,
`statusdescription`, or order-category fields. Their values cannot change this
query's row inclusion or computed values. `amountuom` would be contextual for
interpreting an amount in a downstream representation, but it is not a source
input to this canonical SQL.

There is no grouping, temporal carry-forward, interval merging, or other
derived dependency. The only derived clinically meaningful value is
`vaso_rate`, controlled by `rate` and `rateuom`; all other outputs are direct
source projections.

## 9. Relevant downstream/source context (leads, not additional SQL logic)

The raw ICU input-event schema and the ICU MedicationAdministration ETL were
read to identify mapping-relevant loss/branch points without changing the
source analysis:

- `mimic-iv/buildmimic/bigquery/schemas/icu/inputevents.json` and
  `mimic-iv/buildmimic/postgres/create.sql:450-478` establish the source types
  and nullability used above.
- `mimic-fhir/sql/fhir_medication_administration_icu.sql` reads one ICU
  `inputevents` row at a time, writes the source `itemid` as the medication
  code, carries `amount` and `rate` into dosage quantities, and chooses
  `effectivePeriod` from start/end when rate is non-NULL versus
  `effectiveDateTime` from endtime when rate is NULL. It does not select or
  serialize `linkorderid`; its joins to `d_items` and UUID namespace tables
  are ETL logic, not joins in `vasopressin.sql`.
- The applicable ICU-medication sibling fragments (`dobutamine.md`,
  `dopamine.md`, `epinephrine.md`, `milrinone.md`, `norepinephrine.md`, and
  `phenylephrine.md`) report the same mapping leads: possible loss of
  `linkorderid`, conditional effective-time shape, served quantity precision,
  and potential DST normalization. These are provisional downstream leads for
  the FHIR prober, not facts that alter the canonical source query.
- `MIMIC_NOTES.md` says itemid-derived Observation/medication streams retain
  source itemid values verbatim and warns about polymorphic effective fields,
  numeric Quantity aliases, and offset-bearing FHIR datetimes. It does not add
  a source filter or dependency to this concept.

The canonical SQL itself names no FHIR URI and performs no RxNorm or other
terminology translation. A downstream prober may verify the served medication
coding system, but must preserve the source literal `222315` rather than use a
label or an external mapping.

## Handoff summary

`vasopressin` is a level-0, dependency-free extraction from one raw table,
`mimiciv_icu.inputevents`. It returns one row per matching source input-event,
with the exact item filter `itemid = 222315`, converts only exact
`rateuom = 'units/min'` rates by `60.0`, and directly emits amount and interval
timestamps. It has no joins, derived-table dependencies, aggregations,
windows, time/value exclusions, or deduplication. The six output columns are
`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, and
`endtime`; the empirical full-oracle comparison key is `(stay_id, starttime)`
but the SQL itself declares no output key because raw `(orderid, itemid)`
identity is not projected.
