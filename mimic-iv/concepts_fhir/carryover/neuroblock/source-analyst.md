# Source analysis: `neuroblock`

## Scope and source identity

- Concept stem: `neuroblock`.
- Canonical SQL: `mimic-iv/concepts/medication/neuroblock.sql`.
- The canonical SQL SHA256 is
  `1e42f6d1f894f593eb315ab1f876ca4777892c65f89113a768c7e003db3ac19f`, matching
  the `neuroblock` node in `mimic-iv/concept_dag/concept_dag.json`.
- DAG level: `0`.
- DAG dependencies: none (`dependencies: []`). The node also has no listed
  dependents. There is therefore no `mimiciv_derived` concept prerequisite.
- This is one final `SELECT` over one raw table. It has no CTE, subquery, or
  intermediate relation.

The executable query is:

```sql
SELECT
    stay_id, orderid
    , rate AS drug_rate
    , amount AS drug_amount
    , starttime
    , endtime
FROM `physionet-data.mimiciv_icu.inputevents`
WHERE itemid IN
    (
        222062 -- Vecuronium (664 rows, 154 infusion rows)
        , 221555 -- Cisatracurium (9334 rows, 8970 infusion rows)
    )
    AND rate IS NOT NULL -- only continuous infusions
```

The comments describe the intended neuromuscular-blocking-agent stream and
source row counts; they are not additional executable predicates. The
`rate IS NOT NULL` predicate, rather than the comment alone, defines the
continuous-infusion restriction.

## 1. Table references

| SQL clause | Catalog/project | Schema | Table | Alias | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.inputevents\`` | `physionet-data` | `mimiciv_icu` | `inputevents` | none | Sole source of selected and filtered values |

There are no other `FROM` or `JOIN` clauses. The query does not reference
`mimiciv_hosp`, `mimiciv_derived`, `mimiciv_icu.d_items`, `icustays`, or any
other dimension or encounter table. Foreign keys in the raw schema are not
joins performed by this SQL.

## 2. Column inventory and inferred types

The source types below follow the MIMIC-IV PostgreSQL DDL in
`mimic-iv/buildmimic/postgres/create.sql:449-478`; the output shape is also
recorded by the immutable full oracle manifest.

| Source table.column | Source type / nullability | Use in SQL | Final output | Final type |
|---|---|---|---|---|
| `mimiciv_icu.inputevents.stay_id` | `INTEGER`, nullable in the raw DDL | selected unchanged | `stay_id` | `INTEGER` |
| `mimiciv_icu.inputevents.orderid` | `INTEGER NOT NULL` | selected unchanged | `orderid` | `INTEGER` |
| `mimiciv_icu.inputevents.rate` | `FLOAT`, nullable | selected as a direct alias and tested non-NULL | `drug_rate` | `FLOAT` |
| `mimiciv_icu.inputevents.amount` | `FLOAT`, nullable | selected as a direct alias | `drug_amount` | `FLOAT` |
| `mimiciv_icu.inputevents.starttime` | `TIMESTAMP NOT NULL` | selected unchanged | `starttime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.endtime` | `TIMESTAMP NOT NULL` | selected unchanged | `endtime` | `TIMESTAMP` |
| `mimiciv_icu.inputevents.itemid` | `INTEGER NOT NULL` | `IN` filter only; not projected | not emitted | — |

There are no intermediate CTE columns. The exact final column order is:

```text
stay_id INTEGER
orderid INTEGER
drug_rate FLOAT
drug_amount FLOAT
starttime TIMESTAMP
endtime TIMESTAMP
```

`rateuom`, `amountuom`, `patientweight`, `linkorderid`, `subject_id`,
`hadm_id`, `statusdescription`, `ordercategoryname`, `ordercategorydescription`,
`originalamount`, `originalrate`, and every other `inputevents` field are not
selected or otherwise referenced by the canonical SQL. In particular, the
query outputs `orderid`, not `linkorderid`.

The manifest at
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` records this target
as `comparison: keyed_join`, with natural/comparison key `orderid`,
`key_probes: 2`, and full-oracle row count `14174`. That key is empirical
comparison metadata; the SQL's row grain remains a qualifying raw input-event
row, and the raw table declares the primary key `(orderid, itemid)`.

## 3. Filters and literal code specification

The complete executable filter is:

```sql
WHERE itemid IN
    (
        222062 -- Vecuronium (664 rows, 154 infusion rows)
        , 221555 -- Cisatracurium (9334 rows, 8970 infusion rows)
    )
    AND rate IS NOT NULL -- only continuous infusions
```

### Inclusion and value predicates

1. `itemid IN (...)` retains only the two named ICU input-event itemids.
2. `rate IS NOT NULL` removes rows without a rate. It is a value/nullability
   constraint, not a code set. It also means every output `drug_rate` is
   non-NULL for a qualifying source row, although `drug_amount` is not subject
   to a corresponding predicate.

There is no time window, `starttime`/`endtime` bound, amount constraint, unit
constraint, status constraint, order-category constraint, `DISTINCT`, or code
exclusion. The SQL names no ICD code, `icd_version`, LOINC code, RxNorm/NDC
code, or explicit FHIR coding-system URI.

### Literal code set — verbatim

These are the exact literals in source order. They are not normalized,
expanded, deduplicated, or replaced by drug labels.

| Source table filtered | Source field/operator | Exact literal | Feeds |
|---|---|---|---|
| `mimiciv_icu.inputevents` | `itemid IN` | `222062` | The final qualifying row set, and therefore all six final output columns; `itemid` itself is not emitted |
| `mimiciv_icu.inputevents` | `itemid IN` | `221555` | The final qualifying row set, and therefore all six final output columns; `itemid` itself is not emitted |

The SQL comments label `222062` as Vecuronium and `221555` as Cisatracurium,
but those labels are documentation and are not substitutes for the numeric
code literals. No dead-filter/present-in-SQL-expected-absent classification was
made here because no served-data probe was run for these two itemids.

## 4. Joins

There are no joins. Consequently there are no INNER, LEFT, or other join
types and no join conditions. Each qualifying `inputevents` row is returned
directly without an encounter, patient, medication-dimension, or derived-table
join.

## 5. `mimiciv_derived` dependencies

None. The SQL contains no `mimiciv_derived` reference, and the DAG node has
`dependencies: []`. The raw source is only `mimiciv_icu.inputevents`.

## 6. Aggregation, windows, and row semantics

- No `GROUP BY` or `HAVING`.
- No aggregate functions (`MIN`, `MAX`, `AVG`, `SUM`, `ARRAY_AGG`, or others).
- No window functions.
- No `DISTINCT`, `ORDER BY`, row limit, or explicit deduplication.
- `rate` and `amount` are direct aliases; there is no arithmetic or unit
  conversion.
- `starttime` and `endtime` are direct source timestamps; the SQL does not
  calculate a duration or alter the interval.

The row grain is one row per raw
`mimiciv_icu.inputevents` row satisfying
`itemid IN (222062, 221555)` and `rate IS NOT NULL`. Thus the output is a
continuous/rate-bearing input-event administration stream for the two itemids,
not one row per stay, one row per drug, or one aggregated interval. Multiple
qualifying source events remain separate rows. `amount` may remain NULL because
the SQL does not filter it.

The raw input-event primary key is `(orderid, itemid)` according to
`mimic-iv/buildmimic/postgres/constraint.sql:162-167`. The selected `orderid`
is therefore a source identity component. `itemid` is not selected, although
the full-data manifest reports `orderid` alone as an empirically unique
comparison key for this filtered stream. Do not infer that the SQL generally
declares `orderid` as a standalone primary key outside this filtered result.

## 7. Semantically essential source inputs

These are the source fields/discriminators whose values can change inclusion,
identity, temporal interpretation, or a clinically meaningful output. This is
descriptive source analysis, not a terminal representability decision.

| Input | Why it is essential | Branches/output controlled |
|---|---|---|
| `itemid` | The only coded row-inclusion discriminator. | `222062` and `221555` select the neuromuscular-blocking-agent stream; the selected rows feed all six final columns. It also identifies which ICU medication coding is expected downstream. |
| `rate` | Its NULL state controls row inclusion, and its numeric value is clinically meaningful. | `rate IS NOT NULL` retains only continuous infusions; the non-NULL value feeds `drug_rate`. In the likely ICU MedicationAdministration ETL, non-NULL rate also selects the `effectivePeriod` representation. |
| `orderid` | It is selected and is the raw input-event identity component with `itemid`; the full manifest uses it as the empirical comparison key. | Final `orderid`; natural/comparison identity of each output row. |
| `stay_id` | It associates the event with an ICU stay and is selected. | Final `stay_id`; likely recovered through the ICU Encounter reference/identifier. |
| `amount` | It is the clinically meaningful administered amount selected by the query. | Final `drug_amount`; NULL values remain eligible. |
| `starttime` | It is the beginning of the selected administration interval. | Final `starttime`; likely `MedicationAdministration.effectivePeriod.start` for this rate-bearing stream. |
| `endtime` | It is the end of the selected administration interval. | Final `endtime`; likely `MedicationAdministration.effectivePeriod.end` for this rate-bearing stream. |

`rateuom` and `amountuom` may be useful FHIR support/context fields, but their
values cannot alter this SQL because they are neither selected nor filtered.
Likewise, `linkorderid`, `patientweight`, status fields, and order-category
fields are not source inputs to this query. The only source-side conditional
branch is the `rate IS NOT NULL` inclusion gate; any FHIR effective[x] branch
is a downstream ETL consequence of that selected rate state, not a CASE in the
canonical SQL.

## 8. Likely FHIR resource paths and downstream mapping leads

These are mapping leads for the downstream FHIR prober/implementer, not extra
source tables or SQL logic. The source SQL itself names only
`mimiciv_icu.inputevents` and the two itemids.

### Primary resource and code discriminator

The likely primary stream is ICU `MedicationAdministration`, generated from
`mimiciv_icu.inputevents` by
`mimic-fhir/sql/fhir_medication_administration_icu.sql`.

The likely source-code discriminator is the exact medication coding inside
`MedicationAdministration.medication`:

```text
MedicationAdministration.medication.ofType(CodeableConcept).coding
  .where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu')
```

with exact FHIR string codes corresponding to the SQL literals:

```text
"222062"
"221555"
```

The ETL source read for this mapping writes `di_ITEMID` as the coding `code`
and uses `d_items` for display only. The canonical source specification remains
the integer `itemid` set above; no terminology translation, label substitution,
or `meta.profile` filter is justified. The two itemids should remain separate
exact code predicates even if their human-readable labels are used for
diagnostic display.

### ICU stay identity

The likely path from the administration to the ICU stay is:

```text
MedicationAdministration.context.getReferenceKey(Encounter)
```

joined by equality to an ICU `Encounter` resource key. The likely emitted
identifier path is:

```text
Encounter.identifier.where(
  system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
).value
```

The identifier value is a FHIR string and would need a final integer cast to
represent source `stay_id`. The Encounter/resource UUID is an opaque join key,
not the MIMIC `stay_id`. No Patient join is required by the six source output
columns, although the administration has a subject reference in the FHIR
resource.

### Dose, rate, and interval paths

Likely direct paths are:

| Source output | Likely FHIR path | Role |
|---|---|---|
| `drug_rate` from `rate` | `MedicationAdministration.dosage.rate` (Quantity), specifically `(dosage.rate).ofType(Quantity).value` | Numeric rate value; source predicate guarantees a rate-bearing row |
| `drug_amount` from `amount` | `MedicationAdministration.dosage.dose` (Quantity), specifically `(dosage.dose).ofType(Quantity).value` | Numeric amount value |
| `starttime` | `(effective).ofType(Period).start` | Source start for the rate-bearing branch |
| `endtime` | `(effective).ofType(Period).end` | Source end for the rate-bearing branch |

The ICU medication ETL read for this analysis uses `effectivePeriod` when
source `rate` is non-NULL and uses `effectiveDateTime` from only source
`endtime` when source `rate` is NULL. Because the canonical SQL filters
`rate IS NOT NULL`, the expected branch for every qualifying row is
`effectivePeriod`, not the dateTime-only branch. A prober should still verify
the served target and should not infer `starttime` from `effectiveDateTime` if
that branch is encountered elsewhere.

The same ETL casts naive source timestamps through `TIMESTAMPTZ` before writing
FHIR datetimes. The curated notes therefore require preserving served
wall-clock datetimes with `TIMESTAMP_NTZ` in downstream SQL, and warn that
DST-gap times may be irreversibly shifted by the upstream ETL. This is a
downstream representation issue, not a transformation in `neuroblock.sql`.

### `orderid` mapping limitation

The likely ICU `MedicationAdministration` representation does not serialize
`inputevents.orderid` or `linkorderid` as a normal FHIR identifier. The ETL
constructs an opaque resource UUID using `stay_id`, `orderid`, and `itemid`, but
the repository policy forbids parsing, regenerating, brute-forcing, or otherwise
using that UUID to recover `orderid`. The FHIR prober must establish whether an
independent served element carries `orderid`; absent such an element, this
source-selected output/key input is not represented and must not be estimated.
That possible loss is especially important because the full oracle manifest
uses `orderid` as the comparison key.

## 9. Notes and policy material checked

I read and used:

- `AGENTS.md`, including the exact-code policy, opaque-resource-id rule, and
  essential-input rule;
- `mimic-iv/concept_dag/concept_dag.json`, including the `neuroblock` node,
  level, dependency list, and source hash;
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`;
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`;
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`;
- relevant provisional medication fragments:
  `dobutamine.md`, `dopamine.md`, `epinephrine.md`, and `milrinone.md`;
- related provisional ICU/general fragments:
  `crrt.md`, `invasive_line.md`, `icustay_detail.md`, and
  `icustay_times.md`;
- `mimic-iv/buildmimic/postgres/create.sql` and
  `mimic-iv/buildmimic/postgres/constraint.sql` for source types and the
  `(orderid, itemid)` primary key;
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for the target
  output schema, empirical key, and row count;
- `mimic-fhir/sql/fhir_medication_administration_icu.sql` and
  `mimic-fhir/sql/fhir_encounter_icu.sql` as structural ETL mapping leads.

The existing fragments were treated as provisional leads, not as proof of
neuroblock-specific served-data counts. No relational SQL or FHIR query was
executed during this source analysis, and no code-presence/dead-filter claim
was made beyond the literals present in the canonical SQL.

## Summary

`neuroblock` is a level-0, dependency-free extraction at the raw
`mimiciv_icu.inputevents` row grain. It emits six direct values, retains only
itemids `222062` and `221555` with non-NULL `rate`, performs no joins or
aggregation, and uses `orderid` as the full-data empirical comparison key.
The likely FHIR stream is ICU `MedicationAdministration`, discriminated by the
exact `mimic-medication-icu` coding values, with ICU Encounter identifier
support for `stay_id`, Quantity paths for rate/amount, and
`effectivePeriod.start/end` for the selected rate-bearing intervals; the
representability of the selected `orderid` must be probed rather than recovered
from an opaque resource UUID.
