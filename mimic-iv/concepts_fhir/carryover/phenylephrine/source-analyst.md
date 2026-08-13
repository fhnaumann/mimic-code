# Source analysis: `phenylephrine`

## Scope and source identity

- Concept stem: `phenylephrine`.
- Canonical SQL: `mimic-iv/concepts/medication/phenylephrine.sql`.
- The SQL file hashes to
  `173331e5ad8a011e4c9d24faae342ad3a1de5e645879210715885d099c6032a3`, exactly
  matching the `phenylephrine` node in
  `mimic-iv/concept_dag/concept_dag.json`.
- The DAG path is `medication/phenylephrine.sql`; the node is level `0` and has
  `dependencies: []`. There are no `mimiciv_derived` prerequisites. The DAG
  lists `vasoactive_agent` as a dependent/consumer; that is downstream and is
  not an input dependency of this concept.
- The query is one final `SELECT`. It has no CTE, subquery, or intermediate
  relation.

The executable source is:

```sql
SELECT
    stay_id, linkorderid
    , CASE WHEN rateuom = 'mcg/min' THEN rate / patientweight
        ELSE rate END AS vaso_rate
    , amount AS vaso_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid = 221749 -- phenylephrine
```

The comments describe dose guidance (`0.5 mcg/kg/min` low to `5 mcg/kg/min`
high) and state that one row is in `mcg/min` while the remainder are in
`mcg/kg/min`. Those comments are not additional predicates. The executable
`CASE` is the only rate conversion.

## 1. Table references

| SQL clause | Catalog/project | Schema | Table | Alias | Join role/condition |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `physionet-data` | `mimiciv_icu` | `inputevents` | none | Sole base table; no join |

The project-qualified BigQuery name resolves to the raw MIMIC-IV table
`mimiciv_icu.inputevents`. There are no `JOIN` clauses and no references to
`mimiciv_hosp`. The raw schema has an `itemid` foreign key to
`mimiciv_icu.d_items`, but that dimension table is not referenced by this SQL
and must not be added as a source join.

## 2. Column inventory and inferred types

Types and nullability below follow the MIMIC-IV `inputevents` schema in
`mimic-iv/buildmimic/postgres/create.sql:450-478` and
`mimic-iv/buildmimic/bigquery/schemas/icu/inputevents.json`.

| Source column | Source type/nullability | Use in SQL | Final output name | Inferred output type |
|---|---|---|---|---|
| `mimiciv_icu.inputevents.stay_id` | `INTEGER`, nullable | Selected unchanged | `stay_id` | `INTEGER` |
| `mimiciv_icu.inputevents.linkorderid` | `INTEGER`, nullable | Selected unchanged | `linkorderid` | `INTEGER` |
| `mimiciv_icu.inputevents.rateuom` | `VARCHAR`/`STRING`, nullable | Controls the `CASE` branch | not emitted | not applicable |
| `mimiciv_icu.inputevents.rate` | `FLOAT`/`FLOAT64`, nullable | Divided or passed through by the `CASE` | `vaso_rate` | `FLOAT` |
| `mimiciv_icu.inputevents.patientweight` | `FLOAT`/`FLOAT64`, nullable | Denominator in the `rateuom = 'mcg/min'` branch | not emitted | not applicable |
| `mimiciv_icu.inputevents.amount` | `FLOAT`/`FLOAT64`, nullable | Direct alias | `vaso_amount` | `FLOAT` |
| `mimiciv_icu.inputevents.starttime` | `TIMESTAMP`/`DATETIME`, required | Selected unchanged | `starttime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.endtime` | `TIMESTAMP`/`DATETIME`, required | Selected unchanged | `endtime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.itemid` | `INTEGER`/`INT64`, required | Equality filter only | not emitted | not applicable |

There are no intermediate CTE columns. The final output schema, in exact
column order, is:

```text
stay_id       INTEGER
linkorderid   INTEGER
vaso_rate     FLOAT
vaso_amount   FLOAT
starttime     TIMESTAMP
endtime       TIMESTAMP
```

The SQL does not select or reference `subject_id`, `hadm_id`, `caregiver_id`,
`storetime`, `amountuom`, `orderid`, `totalamount`, status/category fields, or
any other `inputevents` column.

`vaso_rate` is evaluated as:

```sql
CASE
    WHEN rateuom = 'mcg/min' THEN rate / patientweight
    ELSE rate
END AS vaso_rate
```

Thus an exact source `rateuom` value of `'mcg/min'` causes division by the
source `patientweight`; every other value, including NULL, takes the raw
`rate` branch. The SQL does not guard against a NULL or zero denominator. A
NULL `rate` remains eligible and normally produces a NULL `vaso_rate` in
either branch; a NULL `patientweight` produces a NULL result in the division
branch. `vaso_amount` is a direct copy of `amount`; `amountuom` is not
inspected or converted.

## 3. Filters and value constraints

The only executable `WHERE` predicate is:

```sql
WHERE itemid = 221749 -- phenylephrine
```

There is no time window, stay restriction, NULL predicate, rate or amount
constraint, dosage-range filter, unit exclusion, status exclusion, or other
code exclusion. All rows with the selected itemid are retained regardless of
the values of `rate`, `amount`, `rateuom`, and `patientweight`.

The `CASE` branch condition is not a row filter: it changes `vaso_rate` while
retaining the row.

## 4. Joins

There are no joins. Consequently there are no INNER/LEFT join types or join
conditions. Each qualifying raw `inputevents` row is projected directly,
without patient, admission, ICU-stay, `d_items`, or derived-table enrichment.

## 5. `mimiciv_derived` dependencies

None. The canonical SQL contains no `mimiciv_derived` reference, and the DAG
records `dependencies: []`; no other concept must be ported first. The
downstream `vasoactive_agent` SQL consumes `mimiciv_derived.phenylephrine` but
is not a dependency of this source extraction.

## 6. Aggregation, windows, and cardinality

- No `GROUP BY`, `HAVING`, or aggregate (`MIN`, `MAX`, `AVG`, `SUM`,
  `ARRAY_AGG`, etc.).
- No window function, including no `LEAD` or `LAG`.
- No `DISTINCT`, `ORDER BY`, row limit, or explicit deduplication.
- Grain is one output row per raw `mimiciv_icu.inputevents` row satisfying
  `itemid = 221749`.
- Multiple matching administration rows are retained separately. NULL values
  in nullable selected fields do not exclude a row.

The raw DDL declares the `inputevents` primary key as `(orderid, itemid)` in
`mimic-iv/buildmimic/postgres/constraint.sql:162-167`. Since this query fixes
`itemid` to `221749`, `orderid` is the implied unique raw-row identifier
within this filtered stream, but `orderid` is not projected. `linkorderid` is
nullable and is not declared unique. The canonical SQL therefore does not
declare a key for its six-column output, and the projected tuple can contain
duplicates even though raw source rows have a primary key.

The immutable full-oracle manifest records `phenylephrine` as
`comparison: "full_tuple_multiset"`, with `key: null`, `key_probes: 11`, and
`row_count: 193260`. This means the comparator aligns complete output tuples
with multiplicity rather than using a keyed join; it is comparator metadata,
not a source-SQL natural-key declaration. The source grain remains the
filtered raw inputevent row, with raw identity `(orderid, itemid)` and the
fixed-stream identifier `orderid` not carried into the output.

## 7. Literal code specification (verbatim)

The complete coded-filter set named by the canonical SQL is:

| Source table filtered | Source coded field/operator | Exact literal as written | Output column or CTE fed |
|---|---|---|---|
| `mimiciv_icu.inputevents` | `itemid =` | `221749` | The final row set, and therefore all six final output columns: `stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`; `itemid` itself is not emitted |

The SQL names no `icd_code`, `icd_version`, LOINC, RxNorm/NDC, or explicit
coding-system URI. Do not substitute the comment label `phenylephrine`, add
other itemids, or translate the integer literal. This static source analysis
does not probe served data, so no present-in-data or expected-absent-in-data
classification is asserted; `221749` is nevertheless the exact filter that
the prober and implementer must preserve.

The non-code branch literal is also exact and semantically important:
`rateuom = 'mcg/min'`. It is a unit discriminator, not part of the itemid
code set. The source-side raw coding context is the integer
`mimiciv_icu.inputevents.itemid`, backed by `mimiciv_icu.d_items.itemid` in
the schema. The ICU MedicationAdministration ETL read for downstream context
uses the FHIR system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu` and carries
the itemid as code text, but that URI is not named by the canonical source SQL
and is not an additional source filter.

## 8. Semantically essential source inputs

These fields can change inclusion, source-row identity, temporal meaning, or a
clinically meaningful output. This is a source-semantics inventory, not a
terminal representability decision.

1. **`itemid`** — the exact `221749` equality controls row inclusion and
   selects the phenylephrine stream. It feeds the final result set and hence
   all six output columns, although it is not emitted.
2. **`stay_id`** — carries ICU-stay identity into every output row and scopes
   the administration. It is also used by the downstream `vasoactive_agent`
   concept when constructing stay-level infusion intervals.
3. **`orderid`** — not selected or referenced in an expression, but it is part
   of the raw primary key `(orderid, itemid)` and distinguishes source rows
   that could otherwise project the same six values. It is therefore essential
   to the raw row grain, while not being an output column.
4. **`linkorderid`** — is explicitly retained in the final output. It does not
   control `WHERE` inclusion or the `CASE`, but changing it changes the
   canonical result tuple and preserves source order linkage for consumers.
5. **`starttime`** — is emitted unchanged and identifies the beginning of the
   administration interval; it controls temporal interpretation and any
   downstream interval alignment.
6. **`endtime`** — is emitted unchanged and identifies the end of the
   administration interval; it controls duration/interval interpretation and
   downstream interval alignment.
7. **`rate`** — supplies the clinically meaningful administration rate. It is
   divided in the exact-`mcg/min` branch or copied in the ELSE branch, feeding
   `vaso_rate`; its NULL state is retained rather than filtered.
8. **`rateuom`** — exact equality to `'mcg/min'` selects conversion, while all
   other values select the raw-rate branch. Exact spelling and whitespace
   matter because the source compares the untrimmed value.
9. **`patientweight`** — is the denominator of the `rate / patientweight`
   conversion when `rateuom = 'mcg/min'`. It is not output, but its value can
   change the clinically meaningful `vaso_rate`, including producing NULL when
   the denominator is NULL.
10. **`amount`** — is copied to `vaso_amount` and can be NULL; it does not
    control inclusion or the rate branch.

`subject_id`, `hadm_id`, `amountuom`, and the remaining unreferenced source
fields are not semantically essential to this canonical SQL: they do not
change row inclusion, the raw key, grouping, temporal fields, or any selected
derived value.

## 9. Downstream mapping leads from read-only notes

These observations do not change the source SQL and require downstream FHIR
probing; they are recorded here because they affect which essential inputs
may survive the port:

- The ICU `MedicationAdministration` ETL reads `inputevents` and writes the
  itemid code, amount, rate, effective timing, subject, and ICU encounter, but
  does not serialize `linkorderid` as an independent identifier. Its UUID uses
  `stay_id`, `orderid`, and `itemid` only as opaque identity. Resource IDs must
  not be parsed or inverted to recover source values.
- ICU MedicationAdministration `effective[x]` is conditional on raw `rate`:
  rate-bearing rows use `effectivePeriod` from source start/end, while
  rate-null rows use `effectiveDateTime` from source endtime. Because this
  source output always retains both `starttime` and `endtime`, both FHIR
  variants are relevant to later probing.
- Served ICU medication Quantity values may be decimal scale six, so later
  numeric comparison may need an explicit numeric cast/tolerance; this is not
  a source transformation.
- Served FHIR datetimes carry offsets, and the upstream ICU MedicationAdmin
  ETL casts naive MIMIC timestamps through `TIMESTAMPTZ`; DST-gap wall times
  can therefore be irreversibly normalized. This is a downstream ETL concern,
  not behavior of `phenylephrine.sql`.
- The shared coding policy requires preserving the exact source code
  `221749`; no terminology translation or code expansion is permitted.

## 10. Evidence and authority boundaries

Read for this analysis:

- `AGENTS.md`, including the coding policy, opaque-resource-ID rule, and
  essential-source-loss policy;
- `mimic-iv/concepts/medication/phenylephrine.sql`;
- the `phenylephrine` node and `mimiciv_icu.inputevents` reverse-table entry in
  `mimic-iv/concept_dag/concept_dag.json`;
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`;
- relevant ICU medication fragments
  `MIMIC_NOTES.d/norepinephrine.md`, `epinephrine.md`, `dopamine.md`,
  `dobutamine.md`, `milrinone.md`, and `neuroblock.md` (treated as downstream
  leads, not phenylephrine-specific evidence);
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` for grain/key and essential-loss
  rules;
- `mimic-iv/buildmimic/postgres/create.sql`,
  `mimic-iv/buildmimic/postgres/constraint.sql`, and
  `mimic-iv/buildmimic/bigquery/schemas/icu/inputevents.json` for source types
  and the raw primary key;
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for the immutable
  output schema and comparator metadata;
- the downstream consumer `mimic-iv/concepts/medication/vasoactive_agent.sql`
  to distinguish its dependency direction; and
- `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql`
  only for explicitly labeled FHIR representability context.

No SQL was run, no clinical interpretation was added, and no attempt
implementation file was authored.

## Summary

`phenylephrine` is a level-0, dependency-free, single-table ICU inputevent
extraction. It retains one row per `mimiciv_icu.inputevents` row with exact
`itemid = 221749`, emits six columns, converts only exact `rateuom =
'mcg/min'` rates by dividing by `patientweight`, has no joins/windows/
aggregations, and has raw source grain `(orderid, itemid)` (fixed-stream
identifier `orderid`) but no projected key; the full oracle consequently uses
a full-tuple multiset comparison.
