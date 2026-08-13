# Source analysis: `milrinone`

## Scope and source identity

- Concept stem: `milrinone`.
- Canonical SQL: `mimic-iv/concepts/medication/milrinone.sql`.
- DAG node: path `medication/milrinone.sql`, level `0`, SHA256
  `5ff338dcfd6d66733ae2a543bf6180a635518772bc9ea88591552df86a00794e`.
  The SHA256 was checked against the SQL file and the node in
  `mimic-iv/concept_dag/concept_dag.json`.
- DAG dependencies: none (`dependencies: []`). The node's listed dependent is
  `vasoactive_agent`; that is a downstream consumer and is not an input to this
  concept.
- The canonical SQL is one final `SELECT`. It has no CTE, subquery, or
  intermediate relation.

The executable query is:

```sql
SELECT
    stay_id, linkorderid
    , rate AS vaso_rate
    , amount AS vaso_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid = 221986 -- milrinone
```

The comments describe the extraction and local dosage guidance (`0.5
mcg/kg/min` usual), and the inline comment says all rows are in
`mcg/kg/min`. These comments are descriptive only. They are not executable
filters, unit conversions, or value constraints.

## 1. Table references

| SQL clause | Catalog/project | Schema | Table | Alias | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `physionet-data` | `mimiciv_icu` | `inputevents` | none | Sole source of selected and filtered values |

The project-qualified source name resolves to the raw MIMIC-IV ICU
`mimiciv_icu.inputevents` table. There are no other `FROM` or `JOIN` clauses.
No `mimiciv_hosp` table is referenced, and no dimension table such as
`mimiciv_icu.d_items` is joined. Any foreign-key relationships in the raw
schema are not used by this query.

## 2. Column inventory and inferred types

The source types below follow the MIMIC-IV PostgreSQL DDL in
`mimic-iv/buildmimic/postgres/create.sql:450-478`; the final output types and
column order are also recorded in
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.

| Source column | Source type / nullability | Use in SQL | Final output name | Final type |
|---|---|---|---|---|
| `mimiciv_icu.inputevents.stay_id` | `INTEGER`, nullable in the raw DDL | selected unchanged | `stay_id` | `INTEGER` |
| `mimiciv_icu.inputevents.linkorderid` | `INTEGER`, nullable | selected unchanged | `linkorderid` | `INTEGER` |
| `mimiciv_icu.inputevents.rate` | `FLOAT`, nullable | direct alias | `vaso_rate` | `FLOAT` |
| `mimiciv_icu.inputevents.amount` | `FLOAT`, nullable | direct alias | `vaso_amount` | `FLOAT` |
| `mimiciv_icu.inputevents.starttime` | `TIMESTAMP`, `NOT NULL` | selected unchanged | `starttime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.endtime` | `TIMESTAMP`, `NOT NULL` | selected unchanged | `endtime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.itemid` | `INTEGER`, `NOT NULL` | equality filter only | not emitted | — |

There are no intermediate CTE columns. The exact final schema and order are:

```text
stay_id INTEGER
linkorderid INTEGER
vaso_rate FLOAT
vaso_amount FLOAT
starttime TIMESTAMP
endtime TIMESTAMP
```

`itemid` selects the stream but is intentionally absent from the output.
`subject_id`, `hadm_id`, `caregiver_id`, `storetime`, `amountuom`, `rateuom`,
`orderid`, `patientweight`, order-category fields, status fields, and all other
`inputevents` columns are not selected or otherwise referenced by this SQL.

## 3. Filters and literal code specification

There is exactly one executable `WHERE` predicate:

```sql
WHERE itemid = 221986 -- milrinone
```

Complete literal code set, copied verbatim from the canonical SQL:

| Source table filtered | Source field/operator | Exact literal | Output column or CTE fed |
|---|---|---|---|
| `mimiciv_icu.inputevents` | `itemid =` | `221986` | The final result row set, and therefore all six final output columns; `itemid` itself is not emitted |

This is an ICU `inputevents.itemid` filter. The SQL names no `icd_code`,
`icd_version`, LOINC, RxNorm/NDC, or other explicit coding-system code. It has
no `IN`/`NOT IN` set, exclusion list, time window, rate constraint, amount
constraint, NULL predicate, status predicate, or unit predicate. Do not add
other milrinone itemids or replace `221986` with the comment label.

This static source analysis does not classify `221986` as present or absent in
served data; that is a FHIR/data-prober check. The literal must nevertheless be
preserved exactly, including its integer value.

## 4. Joins

There are no joins. Consequently there are no INNER/LEFT join types or join
conditions to preserve. Each qualifying raw `inputevents` row is returned
directly, without an encounter, patient, medication-dimension, or derived-table
join.

## 5. `mimiciv_derived` dependencies

The canonical SQL contains no reference to `mimiciv_derived`, and the DAG
records `dependencies: []`. No other concept must be ported before
`milrinone`. The reverse dependency is `vasoactive_agent`, which consumes this
concept and is not a source dependency here.

## 6. Aggregation, windows, and temporal behavior

- No `GROUP BY`, `HAVING`, or aggregate function (`MIN`, `MAX`, `AVG`, `SUM`,
  `ARRAY_AGG`, or similar).
- No window function, including no `LEAD`/`LAG`.
- No `DISTINCT`, `ORDER BY`, row limit, or deduplication.
- `rate` is passed through as `vaso_rate`; there is no unit conversion or
  arithmetic.
- `amount` is passed through as `vaso_amount`; there is no amount conversion.
- `starttime` and `endtime` are passed through as source timestamps. The SQL
  does not calculate duration, intersect intervals, fill gaps, or impose a
  time window.

The row grain is one output row per raw `mimiciv_icu.inputevents` row satisfying
`itemid = 221986`. Multiple matching administrations remain separate rows.
The SQL does not require `rate` or `amount` to be non-NULL; source NULLs in
those selected fields remain eligible. The raw DDL declares `starttime` and
`endtime` non-NULL, but the query itself adds no explicit NULL test.

## 7. Natural-key and cardinality implications

The raw `inputevents` primary key is `(orderid, itemid)` according to
`mimic-iv/buildmimic/postgres/constraint.sql:162-167`. Since the query fixes
`itemid` but omits `orderid`, it does not carry the declared raw row identity
into the result. `linkorderid` is nullable and is not declared unique, so it
must not be assumed to identify an administration by itself. The projected
output can therefore contain repeated values even though the source rows have
a primary key.

The immutable full-oracle manifest records the empirical comparison metadata:

- comparison mode: `keyed_join`;
- comparison key: `("stay_id", "starttime")`;
- `key_probes`: `4`;
- full-oracle row count: `9573`;
- output columns/types: the six-column schema above.

This `(stay_id, starttime)` key is a full-data comparator fact, not a key
declaration made by the canonical SQL and not a claim that `linkorderid` is
unique. Downstream comparison should follow the manifest rather than infer a
different key from the SQL. The key also means that preserving ICU-stay
identity and the exact source start timestamp is especially important for row
alignment; a timestamp transformation or collision can change apparent row
presence even when payload values are otherwise similar.

## 8. Semantically essential source inputs

The following source fields or discriminators can affect inclusion, identity,
temporal interpretation, or a clinically meaningful output. This is a source
semantics inventory, not a representability verdict.

| Input | Why it is essential | Branches/output controlled |
|---|---|---|
| `itemid` | The only row-inclusion discriminator. | `itemid = 221986` selects the entire milrinone stream and all six output columns. |
| `stay_id` | Associates an administration with its ICU stay and participates in the empirical comparison key. | Output `stay_id`; row identity/alignment at `(stay_id, starttime)`. |
| `starttime` | Defines the start of the administration interval and participates in the empirical comparison key. | Output `starttime`; temporal row identity/alignment. |
| `endtime` | Defines the end of the administration interval and therefore the duration represented by the source row. | Output `endtime`; downstream interval/duration interpretation. |
| `rate` | The administration rate is clinically meaningful and is directly selected. Its NULL/non-NULL state can also affect which effective[x] representation a likely FHIR ETL uses. | Output `vaso_rate`; likely `MedicationAdministration.dosage.rateQuantity.value`; likely effective representation branch downstream. |
| `amount` | The administered amount is clinically meaningful and is directly selected. | Output `vaso_amount`; likely `MedicationAdministration.dosage.dose.value`. |
| `linkorderid` | A source linkage/order-group value retained in the canonical output. It is not declared unique, but changing it changes the output tuple and can matter to consumers. | Output `linkorderid`; likely not serialized in the ICU MedicationAdministration stream, so its loss must be tested rather than reconstructed from an opaque resource id. |
| `orderid` | Not selected, but part of the raw primary key and therefore distinguishes raw input rows that can collapse to the same projected values. | Source row identity only; it does not feed a final output column or a SQL branch. |

The SQL does **not** reference `rateuom`, `amountuom`, `patientweight`,
`statusdescription`, or order-category fields. Their values cannot alter this
query's inclusion or derived values. The dosage-unit comment is not a
substitute for an executable unit discriminator.

There is no source-side conditional branch: all rows passing the itemid
predicate are treated identically by the SQL. The only likely branch mentioned
above (`rate` determining FHIR `effective[x]` shape) belongs to the downstream
ETL representation, not to `milrinone.sql`.

## 9. Likely FHIR resource streams and mapping leads

These are downstream mapping leads, not additional source tables or SQL logic;
the FHIR prober must confirm them against the served Delta data before a port is
implemented.

1. **Primary stream:** ICU `mimiciv_icu.inputevents` is likely represented by
   `MedicationAdministration` resources generated by the ICU medication
   administration ETL.
2. **Exact medication discriminator:** the source itemid is likely carried as
   a string code in
   `MedicationAdministration.medication.ofType(CodeableConcept).coding`,
   under the proprietary system
   `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`, with
   exact code string `"221986"`. The source specification remains the integer
   literal `221986`; no translation or label substitution is allowed.
3. **ICU stay identity:** `MedicationAdministration.context` likely references
   an ICU `Encounter`; `stay_id` is likely recovered from the Encounter
   identifier with system
   `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`, using its
   `identifier.value` rather than the opaque Encounter resource key. A Patient
   join is not required by the six-column source output.
4. **Rate and amount:** `rate` is likely exposed through
   `MedicationAdministration.dosage.rateQuantity.value`, and `amount` through
   `MedicationAdministration.dosage.dose.value`. The curated and sibling
   medication findings say served Quantity values may be decimal scale six and
   materialized aliases may be string-like; this is a downstream typing issue,
   not source SQL behavior.
5. **Effective interval:** for rate-bearing input events, the likely FHIR
   representation is `effectivePeriod.start/end` for `starttime`/`endtime`;
   when the source rate is NULL, sibling ICU medication findings indicate the
   ETL may instead provide `effectiveDateTime` from `endtime`. Because the
   canonical SQL retains both rate-bearing and rate-NULL rows, both effective
   choices and the rate NULL state should be investigated by the prober.
6. **`linkorderid` limitation:** relevant sibling medication fragments report
   that ICU `MedicationAdministration` does not serialize
   `inputevents.linkorderid` as an identifier. Treat that as a mapping lead to
   verify for milrinone. The resource UUID is opaque identity and must not be
   parsed, regenerated, brute-forced, or used to infer `linkorderid`.
7. **Datetime caution:** the source values are naive MIMIC wall-clock
   `TIMESTAMP`s. The shared notes and sibling medication findings warn that
   served FHIR datetimes carry offsets and that upstream `TIMESTAMPTZ` casting
   can irreversibly normalize a DST-gap wall time. A downstream port must
   preserve the source column shape and let the comparator/judge assess any
   proven upstream transformation; this is not a transformation performed by
   the canonical SQL.

The likely medication coding system is a FHIR-side representation detail; the
canonical SQL itself names only the MIMIC ICU `itemid` field and literal
`221986`. No FHIR ViewDefinition or derived SQL is authored here.

## 10. Notes and policy material read

I read:

- `AGENTS.md`, including the coding policy and opaque-resource-id rule;
- `mimic-iv/concept_dag/concept_dag.json` and the `milrinone` node;
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`;
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`;
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`;
- all existing concept fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`:
  `arb.md`, `blood_differential.md`, `cardiac_marker.md`,
  `chemistry.md`, `code_status.md`, `complete_blood_count.md`,
  `coagulation.md`, `crrt.md`, `dobutamine.md`, `dopamine.md`,
  `epinephrine.md`, `gcs.md`, `height.md`, `icp.md`, `icustay_detail.md`,
  `icustay_times.md`, `invasive_line.md`, and `kdigo_creatinine.md`;
- source-schema and oracle metadata in
  `mimic-iv/buildmimic/postgres/create.sql`,
  `mimic-iv/buildmimic/postgres/constraint.sql`, and
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`;
- sibling canonical medication SQL for `dobutamine`, `dopamine`,
  `epinephrine`, `phenylephrine`, `vasopressin`, and `vasoactive_agent` to
  distinguish this level-0 source extraction from its downstream consumer.

The concept-specific source facts above come from the canonical milrinone SQL,
the DAG node, the raw DDL, and the oracle manifest. The FHIR resource details
are explicitly labeled as likely mapping leads and must be probed; provisional
findings in other concept fragments are not treated as milrinone-specific
full-data evidence.

## Summary

`milrinone` is a level-0, dependency-free, non-aggregated extraction from the
single raw table `mimiciv_icu.inputevents`. It returns one row per source row
with the exact itemid filter `221986`, direct aliases `rate -> vaso_rate` and
`amount -> vaso_amount`, and direct `starttime`/`endtime` timestamps. It has no
joins, CTEs, windows, time/value/unit filters, or transformations. Its target
schema is six columns and the empirical full-data comparison key is
`(stay_id, starttime)`; `linkorderid` is retained by the oracle but may be
absent from the likely FHIR MedicationAdministration representation and must
not be recovered through opaque resource identity.
