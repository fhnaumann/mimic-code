# Source analysis: `norepinephrine_equivalent_dose`

## Scope and source identity

- Concept stem: `norepinephrine_equivalent_dose`.
- Canonical SQL: `mimic-iv/concepts/medication/norepinephrine_equivalent_dose.sql`.
- The DAG entry resolves to `medication/norepinephrine_equivalent_dose.sql`,
  level `2`, with SHA256
  `b4c4840d06b079344194eb038bb295b009ddd2ad630b57c5a5dbbb03e7cef11c`.
  The SHA256 computed from the canonical file matches this DAG value.
- The only DAG dependency is `vasoactive_agent`. The DAG edge is
  `norepinephrine_equivalent_dose -> vasoactive_agent`.
- The target SQL is one final `SELECT`: it has no CTE, subquery, or intermediate
  relation of its own. The attempt workspace read for this analysis was
  `mimic-iv/concepts_fhir/concepts/medication/norepinephrine_equivalent_dose/attempt_0001/`.

This analysis describes the target SQL only. The dependency boundary is
load-bearing: candidate SQL should consume the completed dependency as the
unqualified table `vasoactive_agent`, not rederive it from FHIR resources or
from raw `inputevents`.

## 1. Table references

The sole physical table reference in the target SQL is:

| SQL line | Catalog-qualified reference | Schema | Table | Role |
|---|---|---|---|---|
| 28 | ``physionet-data.mimiciv_derived.vasoactive_agent`` | `mimiciv_derived` | `vasoactive_agent` | Sole `FROM` relation |

There are no direct `mimiciv_hosp` or `mimiciv_icu` table references. There are
no `JOIN` clauses. In the candidate execution environment this dependency is
available under the unqualified stem `vasoactive_agent`.

The dependency's own canonical SQL is an interval table built from the seven
upstream vasoactive/inotropic derived concepts. Those raw tables and their
filters are upstream of this concept, not direct table references in this SQL.

## 2. Columns and inferred types

There are no intermediate CTE columns. The target reads these columns from
`mimiciv_derived.vasoactive_agent`:

| Dependency column | Target use | Inferred type |
|---|---|---|
| `stay_id` | Selected unchanged; interval/stay identity | Integer-like MIMIC ICU stay identifier |
| `starttime` | Selected unchanged; interval start | Timestamp/datetime |
| `endtime` | Selected unchanged; interval end | Timestamp/datetime, inherited nullability |
| `norepinephrine` | `IS NOT NULL` inclusion predicate and dose summand | Nullable floating/numeric rate |
| `epinephrine` | `IS NOT NULL` inclusion predicate and dose summand | Nullable floating/numeric rate |
| `phenylephrine` | `IS NOT NULL` inclusion predicate and `/ 10` summand | Nullable floating/numeric rate |
| `dopamine` | `IS NOT NULL` inclusion predicate and `/ 100` summand | Nullable floating/numeric rate |
| `vasopressin` | `IS NOT NULL` inclusion predicate and `* 2.5 / 60` summand | Nullable floating/numeric rate |

The final output columns, in exact SQL order, are:

| Output column | Expression | Inferred type/nullability |
|---|---|---|
| `stay_id` | `stay_id` | Integer-like; no target predicate removes NULLs |
| `starttime` | `starttime` | Timestamp/datetime |
| `endtime` | `endtime` | Timestamp/datetime; this SQL does not independently filter NULL |
| `norepinephrine_equivalent_dose` | Rounded numeric expression below | `NUMERIC`/decimal, rounded to 4 decimal places; normally non-NULL for a retained row |

The executable calculation is:

```sql
ROUND(CAST(
    COALESCE(norepinephrine, 0)
    + COALESCE(epinephrine, 0)
    + COALESCE(phenylephrine / 10, 0)
    + COALESCE(dopamine / 100, 0)
    + COALESCE(vasopressin * 2.5 / 60, 0)
    AS NUMERIC), 4) AS norepinephrine_equivalent_dose
```

`dobutamine` and `milrinone` may exist as columns in the upstream
`vasoactive_agent` output, but this consumer does not read them. It also does
not read `linkorderid`, `vaso_amount`, raw `itemid`, units, or any other child
dependency field.

## 3. Filters and predicates

The only `WHERE` clause in the target is the following exact disjunction
(lines 29-33):

```sql
WHERE norepinephrine IS NOT NULL
    OR epinephrine IS NOT NULL
    OR phenylephrine IS NOT NULL
    OR dopamine IS NOT NULL
    OR vasopressin IS NOT NULL
```

It retains a dependency interval when at least one of those five pressor rate
columns is non-NULL. It excludes intervals whose only non-NULL dependency rates
are `dobutamine` and/or `milrinone`; those two columns are not tested.

There is no target:

- `itemid`, ICD, LOINC, medication-name, or other coded predicate;
- time window or stay restriction;
- rate, amount, unit, or value-range constraint;
- explicit `NULL` predicate on `stay_id`, `starttime`, or `endtime`; or
- code exclusion.

The `COALESCE(..., 0)` calls are value substitutions in the calculation, not
additional row filters. The upstream `vasoactive_agent` SQL has its own
interval-construction filter (`t.endtime IS NOT NULL`), but that is a predicate
of the dependency concept, not of this target SQL; this consumer must inherit
the dependency output rather than recreate that filter.

## 4. Joins

There are no joins of any type in `norepinephrine_equivalent_dose.sql`:

- no `INNER JOIN`;
- no `LEFT JOIN`; and
- no join condition.

The only relation is the dependency table in the `FROM` clause.

## 5. `mimiciv_derived` dependency contract

The DAG and SQL agree on one dependency:

1. `mimiciv_derived.vasoactive_agent` -> candidate table `vasoactive_agent`.

The exact columns consumed from that dependency are:

```text
stay_id
starttime
endtime
norepinephrine
epinephrine
phenylephrine
vasopressin
```

The first three columns are the inherited interval identity/timing columns.
The five rate columns are the only dependency values used in the inclusion
predicate and calculation. The dependency's `dobutamine` and `milrinone` rate
columns are not consumed as dose terms, although their upstream timing can
still affect the interval rows produced by `vasoactive_agent`.

The candidate must not inline the seven child medication concepts, recover raw
`inputevents` fields from MedicationAdministration resources, or rederive
`vasoactive_agent` from FHIR. In particular, the child concepts' itemid and
unit/patient-weight logic is upstream dependency behavior; this target consumes
the already-derived `vaso_rate` columns.

## 6. Aggregations, temporal construction, and natural grain

The target SQL has none of the following:

- `GROUP BY` or `HAVING`;
- scalar aggregates such as `MIN`, `MAX`, `AVG`, `SUM`, or `ARRAY_AGG`;
- window functions;
- `DISTINCT`, `ORDER BY`, or explicit deduplication.

`ROUND`, `CAST`, and `COALESCE` are scalar value operations, not aggregations.

The intended natural grain is one row per completed interval row supplied by
`vasoactive_agent`, conventionally identified by
`(stay_id, starttime, endtime)`, restricted to rows having at least one of the
five selected rate columns non-NULL. This is not raw `inputevents` row grain.
The upstream dependency constructs consecutive stay-level intervals from all
child-agent start/end boundaries and overlays child rates onto those intervals;
the target preserves that interval grain and does not split, merge, or
deduplicate it further. Any duplicate dependency rows would remain duplicated
because the target has no deduplication operation.

## 7. Casts, constants, and executable calculation semantics

### Executable casts and constants

| SQL expression | Effect |
|---|---|
| `COALESCE(norepinephrine, 0)` | Uses numeric zero when norepinephrine is NULL |
| `COALESCE(epinephrine, 0)` | Uses numeric zero when epinephrine is NULL |
| `COALESCE(phenylephrine / 10, 0)` | Divides phenylephrine by literal `10`, then replaces NULL with zero |
| `COALESCE(dopamine / 100, 0)` | Divides dopamine by literal `100`, then replaces NULL with zero |
| `COALESCE(vasopressin * 2.5 / 60, 0)` | Multiplies by literal `2.5`, divides by literal `60`, then replaces NULL with zero |
| `CAST(... AS NUMERIC)` | Casts the complete sum to `NUMERIC` |
| `ROUND(..., 4)` | Rounds the cast numeric sum to 4 decimal places; literal scale is `4` |

Norepinephrine and epinephrine enter the sum unchanged, i.e. with an implicit
coefficient of 1. The SQL comments state that the rate inputs are in
`mcg/kg/min` except vasopressin in `units/hour`; this explains the explicit
vasopressin conversion in the source, but the comments do not add a runtime
unit check.

The following are comments only and are **not executed**:

- `metaraminol/8` (the comment says metaraminol is not used in BIDMC);
- `angiotensin_ii*10` (the comment says angiotensin II is rarely used); and
- the prose equivalence ranges and comparison doses at the top of the file.

For completeness, the non-executable header constants are copied verbatim:

```text
-- Norepinephrine   - 1:1 - comparison dose of 0.1 ug/kg/min
-- Epinephrine      - 1:1 [0.7, 1.4] - 0.1 ug/kg/min
-- Dopamine         - 1:100 [75.2, 144.4] - 10 ug/kg/min
-- Metaraminol      - 1:8 [8.3] - 0.8 ug/kg/min
-- Phenylephrine    - 1:10 [1.1, 16.3] - 1 ug/kg/min
-- Vasopressin      - 1:0.4 [0.3, 0.4] - 0.04 units/min
-- Angiotensin II   - 1:0.1 [0.07, 0.13] - 0.01 ug/kg/min
```

Those comments do not add columns, row filters, or executable terms to the
calculation; the executable expression above is authoritative.

No other casts, constants, CASE branches, or value transformations occur.

## 8. Literal code set, verbatim

The target SQL names **no coded filter literals**. There is no `itemid`,
`icd_code`/`icd_version`, LOINC, medication-name, coding-system URI, or other
source code set to copy for this concept. The five `IS NOT NULL` predicates
are nullability tests on dependency rate columns, not coded filters. There are
therefore no dead coded filters to classify as expected-absent.

The numeric literals `10`, `100`, `2.5`, `60`, `0`, and `4` are calculation/
rounding constants, not source codes. The drug names in comments are labels and
do not create itemid filters. The itemid filters belong to the upstream child
concepts consumed by `vasoactive_agent`; they are not named by this canonical
SQL and must not be invented or reapplied in this consumer.

## 9. Semantically essential inputs and propagation

These are the direct dependency fields whose values can change row inclusion,
natural grain, temporal meaning, or the clinically meaningful derived value:

1. **`stay_id`** — is emitted and is part of the interval row identity. A
   different stay value changes the output key/context.
2. **`starttime`** — is emitted and is part of the interval identity and
   temporal interpretation. Although this target does not compare it in a
   predicate, changing it changes the output row's interval.
3. **`endtime`** — is emitted and is part of the interval identity and temporal
   interpretation. The target does not apply an endtime filter; nullability is
   inherited from the dependency.
4. **`norepinephrine`** — its NULL/non-NULL state controls inclusion; its value
   feeds the unchanged summand in `norepinephrine_equivalent_dose`.
5. **`epinephrine`** — its NULL/non-NULL state controls inclusion; its value
   feeds the unchanged summand.
6. **`phenylephrine`** — its NULL/non-NULL state controls inclusion; its value
   feeds the `/ 10` summand.
7. **`dopamine`** — its NULL/non-NULL state controls inclusion; its value feeds
   the `/ 100` summand.
8. **`vasopressin`** — its NULL/non-NULL state controls inclusion; its value
   feeds the `* 2.5 / 60` summand.

The upstream interval boundary population is also semantically important. In
`vasoactive_agent`, the start/end boundaries from all seven child streams,
including dobutamine and milrinone, determine the consecutive interval rows.
Thus an upstream child `starttime` or `endtime` can change this target's natural
grain and the interval to which a selected pressor rate is assigned, even when
that child's rate is not a term in this target's formula. This effect must be
preserved by the `vasoactive_agent` dependency; it is not a reason to read raw
FHIR resources in this consumer.

At the transitive dependency boundary, child `rate`, unit discriminator, and
where applicable `patientweight` values determine the upstream `vaso_rate`
values that arrive in the five direct rate columns. Child itemid filters
determine which administrations enter those streams. Those are semantically
essential to the upstream concepts, but their code literals and normalization
branches are not literals in this target SQL and belong to the completed
dependency outputs.

The target does not consume `dobutamine` or `milrinone` as dose terms,
`linkorderid`, `vaso_amount`, or any raw medication identifier. Those fields
cannot alter this target except insofar as upstream timing construction has
already incorporated their boundaries.

## Read-only FHIR/dataset leads

I read `MIMIC_NOTES.md` and the requested provisional fragments as leads only,
not as verdict evidence. The relevant leads for later probing are:

- ICU MedicationAdministration may omit source `inputevents.patientweight`,
  which matters to upstream weight-normalized rate branches; the target should
  use the dependency's already-derived rate rather than attempt a new
  normalization.
- ICU MedicationAdministration `effective[x]` is conditional on whether a
  rate is present, so both Period endpoints and dateTime representations may
  matter when probing upstream interval times.
- Served ICU Quantity values may have decimal scale six, which can affect the
  numerical comparison of upstream rates before this target's final `NUMERIC`
  cast and four-place rounding.
- `linkorderid` is not independently serialized, but it is not consumed by this
  target and is not part of the target's dependency contract.

No FHIR probe, SQL execution, or representability judgment was performed in
this source-analysis stage. No new dataset-wide quirk was established here,
so no additional entry should yet be appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/norepinephrine_equivalent_dose.md`.
The patientweight/effective-time/quantity-precision points above are leads to
verify during probing; if a later concept-specific run confirms a dataset-wide
behavior, append it then rather than treating these provisional fragments as
evidence.

## Files checked and authority boundary

- `mimic-iv/concepts/medication/norepinephrine_equivalent_dose.sql`.
- `mimic-iv/concepts/medication/vasoactive_agent.sql` for the dependency output
  contract and inherited interval grain; it was not reimplemented here.
- `mimic-iv/concept_dag/concept_dag.json` and the generated DAG markdown for
  the resolved path, dependency, level, edge, and hash.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- The requested provisional fragments:
  `norepinephrine.md`, `vasoactive_agent.md`, `phenylephrine.md`,
  `dobutamine.md`, `epinephrine.md`, `dopamine.md`, `vasopressin.md`,
  `milrinone.md`, and `neuroblock.md`.
- The empty target workspace
  `mimic-iv/concepts_fhir/concepts/medication/norepinephrine_equivalent_dose/attempt_0001/`.

No ViewDefinition or candidate SQL was authored.

## Summary

`norepinephrine_equivalent_dose` is a level-2, single-dependency interval
consumer. It reads `stay_id`, `starttime`, `endtime`, and five pressor rate
columns from `vasoactive_agent`, retains rows where at least one selected rate
is non-NULL, computes the exact source expression with coefficients `1`, `1`,
`1/10`, `1/100`, and `2.5/60`, casts the sum to `NUMERIC`, and rounds to four
decimal places. It has no raw-table references, joins, grouping, windows, or
coded literals of its own; all upstream medication code filtering and rate
normalization remain the responsibility of the completed dependency concepts.
