# Source analysis: `code_status`

## Authoritative source and DAG position

- Concept: `code_status`.
- Canonical SQL: `mimic-iv/concepts/treatment/code_status.sql`.
- The DAG maps `code_status` to `treatment/code_status.sql`, records build
  level `0`, SHA256
  `b8c92ff0d4c724ab2f5c069735aa5c0b5608842f1450da933190c5bc38ecca67`, and
  lists no dependencies or dependents.
- The SQL contains no reference to `mimiciv_derived`; it is a dependency-free
  Level-0 concept.

The canonical query has two event streams and combines them with `UNION ALL`:
ICU charted code-status observations (`t1`) and hospital provider order-entry
code-status records (`poe`). `UNION ALL` is significant: the query does not
deduplicate rows from either stream or between streams.

## Table references

Every source table reference is below. The canonical SQL uses the
`physionet-data.<schema>.<table>` BigQuery qualification; the logical schemas
are the MIMIC schemas shown here.

### `mimiciv_icu.chartevents` (alias omitted; CTE `t1`)

Referenced columns:

- `subject_id`: source `INTEGER`, selected to output; source DDL says NOT NULL.
- `hadm_id`: source `INTEGER`, selected to output; source DDL says NOT NULL.
- `stay_id`: source `INTEGER`, selected to output; source DDL says NOT NULL.
- `charttime`: source `TIMESTAMP`, selected as the chart-event time; source
  DDL says NOT NULL.
- `value`: source `VARCHAR(200)`, used by all four status `CASE` expressions;
  it is not emitted directly.
- `itemid`: source `INTEGER`, used by the `WHERE` filter; it is not emitted.

The source DDL also contains `caregiver_id`, `storetime`, `valuenum`,
`valueuom`, and `warning`, but none is referenced by this concept.

### `mimiciv_hosp.poe` (alias `p`; CTE `poe`)

Referenced columns:

- `p.subject_id`: source `INTEGER`, selected to output.
- `p.hadm_id`: source nullable `INTEGER`, selected to output and used in the
  ICU-stay join.
- `p.poe_id`: source `VARCHAR(25)`, used in the inner join to `poe_detail`.
- `p.ordertime`: source `TIMESTAMP`, selected as the provider-order time and
  later aliased to final `charttime`; used in both inclusive ICU-stay time
  predicates.
- `p.order_type`: source `VARCHAR(25)`, filtered in the CTE `poe`.
- `p.order_subtype`: source `VARCHAR(50)`, filtered in the CTE `poe`. The
  canonical SQL leaves this reference unqualified; it resolves to `p` because
  `poe_detail` has no `order_subtype` column.

The source DDL also has `poe_seq`, `transaction_type`,
`discontinue_of_poe_id`, `discontinued_by_poe_id`, `order_provider_id`, and
`order_status`; none is referenced.

### `mimiciv_hosp.poe_detail` (alias `pd`; CTE `poe`)

Referenced columns:

- `pd.poe_id`: source `VARCHAR(25)`, inner-join key.
- `pd.field_value`: source `TEXT`, used by the `fullcode`, `dnr`, and `dni`
  `CASE` expressions; it is not emitted directly.

`pd.field_name` and all other `poe_detail` columns are not referenced. In
particular, the query does not filter `field_name`, does not join on
`poe_seq`, and does not join on `subject_id`.

### `mimiciv_icu.icustays` (alias `ie`; CTE `poe`)

Referenced columns:

- `ie.hadm_id`: source `INTEGER`, part of the left-join condition; it is not
  output.
- `ie.intime`: source nullable `TIMESTAMP`, lower bound in the left-join
  condition.
- `ie.outtime`: source nullable `TIMESTAMP`, upper bound in the left-join
  condition.
- `ie.stay_id`: source `INTEGER`, selected as the POE branch's `stay_id`.

The source DDL's `subject_id`, care-unit columns, and `los` are not used.

## CTEs, selected columns, and inferred types

### CTE `t1`

```text
subject_id  <- chartevents.subject_id                         INTEGER
hadm_id     <- chartevents.hadm_id                            INTEGER
stay_id     <- chartevents.stay_id                            INTEGER
charttime   <- chartevents.charttime                          TIMESTAMP
fullcode    <- CASE on chartevents.value                      INTEGER (0/1)
cmo         <- CASE on chartevents.value                      INTEGER (0/1)
dni         <- CASE on chartevents.value                      INTEGER (0/1)
dnr         <- CASE on chartevents.value                      INTEGER (0/1)
```

The CTE emits one row per qualifying `chartevents` row. Each flag is always
the integer literal `1` or `0`; an unrecognized or NULL `value` therefore
produces zero for each flag rather than a NULL flag.

### CTE `poe`

```text
subject_id  <- p.subject_id                                   INTEGER
hadm_id     <- p.hadm_id                                      INTEGER
stay_id     <- ie.stay_id                                      INTEGER, nullable
ordertime   <- p.ordertime                                     TIMESTAMP
fullcode    <- CASE on pd.field_value                         INTEGER (0/1)
dnr         <- CASE on pd.field_value                         INTEGER (0/1)
dni         <- CASE on pd.field_value                         INTEGER (0/1)
```

The CTE does not create a `cmo` column. The final POE branch supplies the
integer constant `0` for `cmo`.

### Final output

The final output has exactly eight columns, in this order:

| output column | source/derivation | inferred/oracle type | nullability implication |
|---|---|---|---|
| `subject_id` | `t1.subject_id` or `poe.subject_id` | `INTEGER` | non-null from both source branches |
| `hadm_id` | `t1.hadm_id` or `poe.hadm_id` | `INTEGER` | nullable in the POE branch because `poe.hadm_id` is nullable |
| `stay_id` | `t1.stay_id` or `poe.stay_id` | `INTEGER` | nullable for POE rows without a matching ICU stay; chart-event source is non-null |
| `charttime` | `t1.charttime` or `poe.ordertime AS charttime` | `TIMESTAMP` | non-null according to the two source DDLs |
| `fullcode` | branch flag | `INTEGER` | 0 or 1, not NULL |
| `cmo` | `t1.cmo` or literal `0` in POE branch | `INTEGER` | 0 or 1, not NULL |
| `dni` | branch flag | `INTEGER` | 0 or 1, not NULL |
| `dnr` | branch flag | `INTEGER` | 0 or 1, not NULL |

The oracle manifest confirms this exact eight-column shape and types:
`subject_id`, `hadm_id`, and `stay_id` are `INTEGER`; `charttime` is
`TIMESTAMP`; all four flags are `INTEGER`.

## Filters and status predicates

### `t1` `WHERE` predicate

The only `t1` filter is:

```sql
WHERE itemid IN (223758)
```

It is applied to `mimiciv_icu.chartevents.itemid` before the status flags are
computed. There is no chart-time window, stay-time window, value-null test,
numeric constraint, or exclusion predicate.

### `poe` `WHERE` predicates

The POE CTE has exactly these predicates:

```sql
WHERE p.order_type = 'General Care'
  AND order_subtype = 'Code status'
```

The unqualified `order_subtype` resolves to `p.order_subtype`. These predicates
select hospital POE rows; they are not filters on `pd.field_name` or
`pd.field_value`.

The `CASE` expressions are value constraints rather than `WHERE` predicates.
They preserve every row admitted by the CTE and encode unmatched values as
zero.

## Literal code/status sets, verbatim

These are the exact literals named by the SQL. They are recorded per source
column and per output fed; no normalization, expansion, or label substitution
has been performed.

### ICU chart-status literals (`mimiciv_icu.chartevents.value`)

The item filter is on `mimiciv_icu.chartevents.itemid` and feeds CTE `t1`,
which feeds all final columns from the first `UNION ALL` branch:

```sql
itemid IN (223758)
```

The exact value sets used by `t1` are:

```sql
value IN ('Full code')
```

- Source column: `mimiciv_icu.chartevents.value`.
- Feeds: `t1.fullcode`, with match `1` and ELSE `0`.

```sql
value IN ('Comfort measures only')
```

- Source column: `mimiciv_icu.chartevents.value`.
- Feeds: `t1.cmo`, with match `1` and ELSE `0`.

```sql
value IN ('DNI (do not intubate)', 'DNR / DNI')
```

- Source column: `mimiciv_icu.chartevents.value`.
- Feeds: `t1.dni`, with match `1` and ELSE `0`.

```sql
value IN ('DNR (do not resuscitate)', 'DNR / DNI')
```

- Source column: `mimiciv_icu.chartevents.value`.
- Feeds: `t1.dnr`, with match `1` and ELSE `0`.

The SQL comment documents these five distinct ICU order values, verbatim:

```text
DNR / DNI
DNI (do not intubate)
Comfort measures only
Full code
DNR (do not resuscitate)
```

The value `DNR / DNI` intentionally feeds both `t1.dni` and `t1.dnr`.

### POE selector literals (`mimiciv_hosp.poe`)

```sql
p.order_type = 'General Care'
```

- Source column: `mimiciv_hosp.poe.order_type`.
- Feeds: the row-admission filter for CTE `poe`, and therefore all final POE
  branch columns.

```sql
order_subtype = 'Code status'
```

- Source column: `mimiciv_hosp.poe.order_subtype` (unqualified in the SQL but
  resolved to `p`).
- Feeds: the row-admission filter for CTE `poe`, and therefore all final POE
  branch columns.

### POE field-value literals (`mimiciv_hosp.poe_detail.field_value`)

For `poe.fullcode`:

```sql
pd.field_value = 'Resuscitate (Full code)'
pd.field_value = 'Full code  (attempt resuscitation)'
```

- Source column: `mimiciv_hosp.poe_detail.field_value`.
- Feeds: `poe.fullcode`, with either match `1` and ELSE `0`.
- The second literal contains two spaces between `code` and `(`; that spacing
  is part of the source literal.

For `poe.dnr`:

```sql
pd.field_value = 'DNAR (DO NOT attempt resuscitation for cardiac arrest) '
pd.field_value = 'Do not resuscitate (DNR/DNI)'
```

- Source column: `mimiciv_hosp.poe_detail.field_value`.
- Feeds: `poe.dnr`, with either match `1` and ELSE `0`.
- The first literal has one trailing space before its closing quote; it is
  copied exactly from the SQL.

For `poe.dni`:

```sql
pd.field_value = 'Do not resuscitate (DNR/DNI)'
```

- Source column: `mimiciv_hosp.poe_detail.field_value`.
- Feeds: `poe.dni`, with match `1` and ELSE `0`.

There is no POE `field_value` literal for comfort measures only. The SQL
comment explicitly says that provider order entry does not contain comfort
measures only orders, and the final POE branch hardcodes `cmo = 0`.

## Joins and row-multiplicity implications

### `poe` to `poe_detail`: INNER JOIN

```sql
INNER JOIN `physionet-data.mimiciv_hosp.poe_detail` pd
  ON p.poe_id = pd.poe_id
```

Only POE rows having at least one matching `poe_detail` row survive. The join
uses only `poe_id`; it does not include `poe_seq`, `subject_id`, or
`field_name`. If multiple detail rows share a `poe_id`, every matching detail
row participates and can produce a separate output row with flags determined
by that detail row's exact `field_value`.

### `poe` to `icustays`: LEFT JOIN

```sql
LEFT JOIN `physionet-data.mimiciv_icu.icustays` ie
  ON p.hadm_id = ie.hadm_id
 AND p.ordertime >= ie.intime
 AND p.ordertime <= ie.outtime
```

The `hadm_id` match and both time comparisons are inclusive. A POE row whose
order time is not within an ICU stay remains in the result with `stay_id =
NULL`. A NULL `p.hadm_id`, or NULL ICU `intime`/`outtime`, cannot satisfy the
join comparisons and likewise leaves the left-side row with no `stay_id`.
The query does not join POE to ICU on `subject_id`. If more than one ICU stay
for the admission satisfies the inclusive interval, the left join can fan out
the POE row; there is no tie-breaker or deduplication.

There are no joins in `t1`, and the final query has no additional joins.

The final two `FROM` clauses are `FROM t1` and `FROM poe`, both references to
the CTEs described above. They are combined in the order shown by `UNION ALL`;
there is no physical table reference hidden in the final projection.

## Aggregation and ordering

- No `GROUP BY`.
- No aggregate functions (`MIN`, `MAX`, `AVG`, `ARRAY_AGG`, or similar).
- No window functions.
- No `DISTINCT`.
- No `ORDER BY`.
- The only conditional derivation is row-wise `CASE`; all output flags are
  integer 0/1 values.
- The final combination is `UNION ALL`, not `UNION`.

## Natural-key implications and oracle shape

The final projection omits source event identifiers such as any chart-event
row identifier, `poe_id`, `poe_seq`, `pd.field_name`, and the detail-row
identity. The apparent tuple `(subject_id, hadm_id, stay_id, charttime)` is
not a declared key and is not guaranteed unique: the two input streams can
contain repeated timestamps/statuses, `poe_detail` can multiply a POE row, and
the ICU interval join can multiply a POE row. The flag columns do not restore
event identity.

The immutable oracle manifest records the empirical comparison shape for
`code_status` as:

- `comparison: full_tuple_multiset`
- `key: null`
- `key_probes: 13`
- `row_count: 269072`

Therefore there is no natural key available for a keyed row join. Downstream
comparison must preserve complete output tuples and multiplicity. A candidate
must not invent a key from the projected identifiers and time.

## Dependencies and coding-system implications

- DAG dependencies: none.
- SQL references to `mimiciv_derived`: none.
- The source has one numeric itemid filter, `223758`, from
  `mimiciv_icu.chartevents`; it does not join `mimiciv_icu.d_items` and does
  not name a FHIR coding-system URI.
- The read-only dataset notes state that ICU `chartevents.itemid` streams are
  represented downstream with the proprietary itemid coding system
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, with
  the itemid carried verbatim as the coding code. Thus the source literal to
  retain for downstream probing/filtering is the exact string form of
  `223758`; no label or terminology translation is specified by this SQL.
- The POE branch is selected by `mimiciv_hosp.poe.order_type` and
  `order_subtype`, and its status flags come from exact free-text
  `poe_detail.field_value` strings, not from an ICD, LOINC, or itemid code
  set.

## Dataset-wide quirk assessment

No genuinely dataset-wide MIMIC-on-FHIR quirk was identified during this
source-only analysis that is absent from `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
The POE detail join shape, exact status strings, missing POE CMO branch, and
lack of a natural key are findings specific to this concept's canonical SQL
and oracle shape. No edit to `MIMIC_NOTES.md` or append to
`MIMIC_NOTES.d/code_status.md` is requested.

## Files read

- `AGENTS.md`.
- `mimic-iv/concepts/treatment/code_status.sql` (authoritative source).
- `mimic-iv/concept_dag/concept_dag.json` and
  `mimic-iv/concept_dag/concept_dag.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md` and the existing fragments
  `coagulation.md`, `cardiac_marker.md`, `blood_differential.md`, and
  `chemistry.md`; none is a `code_status` fragment.
- Relevant source DDL in `mimic-iv/buildmimic/postgres/create.sql` for
  `mimiciv_hosp.poe`, `mimiciv_hosp.poe_detail`,
  `mimiciv_icu.chartevents`, and `mimiciv_icu.icustays`.
- Generated dialect copy `mimic-iv/concepts_duckdb/treatment/code_status.sql`
  as a corroborating expansion of the same logical source query; it was not
  treated as authoritative.
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for the target
  output schema, row count, and no-key comparison mode.
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` and the current state file
  `mimic-iv/concepts_fhir/state/code_status/state.json` for comparison and
  attempt conventions.
- The current immutable attempt directory
  `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/` was
  inspected and was empty; no ViewDefinition, SQL, or attempt artifact was
  authored.
