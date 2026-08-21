# Source analysis: `vasoactive_agent`

## Scope and source identity

- Concept stem: `vasoactive_agent`.
- Canonical SQL: `mimic-iv/concepts/medication/vasoactive_agent.sql`.
- DAG entry: `medication/vasoactive_agent.sql`, level 1, SHA256
  `7c8fd57ead83e4b8edf3867204b23fac3d06c141bc8ada8be8fa6513dab1b390`.
- DAG dependencies, in the recorded order: `dobutamine`, `dopamine`,
  `epinephrine`, `milrinone`, `norepinephrine`, `phenylephrine`, and
  `vasopressin`.
- DAG dependent: `norepinephrine_equivalent_dose`.

The target SQL is an interval overlay over seven already-derived medication
tables. It has no direct `mimiciv_hosp` or `mimiciv_icu` table reference. The
seven dependency SQL files each select from `mimiciv_icu.inputevents`; those
underlying source filters and transformations are recorded below because they
define the drug streams consumed by this concept. The dependency boundary must
remain intact: the target consumer reads the dependency outputs, not raw
`inputevents` values.

## 1. Table references

### Physical/derived tables referenced by `vasoactive_agent.sql`

The BigQuery spelling in the canonical file is
``physionet-data.mimiciv_derived.<stem>``. The schema/table references are:

| SQL location | Reference | Selected fields used there |
|---|---|---|
| `tm`, lines 12-13 | `mimiciv_derived.dobutamine` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 15-16 | `mimiciv_derived.dopamine` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 18-19 | `mimiciv_derived.epinephrine` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 21-22 | `mimiciv_derived.norepinephrine` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 24-25 | `mimiciv_derived.phenylephrine` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 27-28 | `mimiciv_derived.vasopressin` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 31-36 | `mimiciv_derived.milrinone` | `stay_id`, `starttime AS vasotime` |
| `tm`, lines 41-42 | `mimiciv_derived.dobutamine` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 43-44 | `mimiciv_derived.dopamine` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 45-46 | `mimiciv_derived.epinephrine` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 47-49 | `mimiciv_derived.norepinephrine` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 51-53 | `mimiciv_derived.phenylephrine` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 55-57 | `mimiciv_derived.vasopressin` | `stay_id`, `endtime AS vasotime` |
| `tm`, lines 59-65 | `mimiciv_derived.milrinone` | `stay_id`, `endtime AS vasotime` |

There is also `FROM tm` at line 79 and `FROM tm_lag t` at line 96; these are
CTE references rather than physical tables.

### Underlying source table of each dependency

Each of the seven dependency SQL files has one `FROM` clause against the same
raw table, spelled ``physionet-data.mimiciv_icu.inputevents`` and normalized
here as `mimiciv_icu.inputevents`:

- `dobutamine.sql:10`
- `dopamine.sql:10`
- `epinephrine.sql:10`
- `norepinephrine.sql:15`
- `phenylephrine.sql:11`
- `vasopressin.sql:15`
- `milrinone.sql:10`

None of those dependency files has a join. The target itself therefore has no
direct raw-table join either.

## 2. CTEs, columns, and inferred types

### `tm` CTE

`tm` is a `UNION DISTINCT` of fourteen branches: the seven dependency
`starttime` columns followed by the seven dependency `endtime` columns. Every
branch selects:

- `stay_id`: the ICU stay identifier; integer-like.
- `starttime` or `endtime`, renamed `vasotime`: timestamp/datetime.

The set operation deduplicates equal `(stay_id, vasotime)` pairs across all
drug streams and both endpoint types. There is no drug name or itemid column in
this CTE.

### `tm_lag` CTE

`tm_lag` selects:

- `stay_id`: integer-like, carried from `tm`.
- `vasotime AS starttime`: timestamp/datetime.
- `LEAD(vasotime, 1) ... AS endtime`: nullable timestamp/datetime; the next
  boundary within the same stay.

The generated `endtime` is nullable for the last ordered boundary in a
`stay_id` partition. The final query removes rows with a null generated
`endtime`.

### Final selected columns

The final output, in exact SQL order, is:

| Output column | Expression | Inferred type and nullability |
|---|---|---|
| `stay_id` | `t.stay_id` | integer-like; nullability is inherited from the source boundary rows |
| `starttime` | `t.starttime` | timestamp/datetime |
| `endtime` | `t.endtime` | timestamp/datetime; final `WHERE` excludes null |
| `dopamine` | `dop.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `epinephrine` | `epi.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `norepinephrine` | `nor.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `phenylephrine` | `phe.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `vasopressin` | `vas.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `dobutamine` | `dob.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |
| `milrinone` | `mil.vaso_rate` | floating numeric; nullable because of `LEFT JOIN` |

The source dependency queries expose `vaso_rate` without an explicit cast. The
rate arithmetic in `norepinephrine`, `phenylephrine`, and `vasopressin` uses
decimal literals and therefore remains numeric/floating; the plain-rate
streams pass through the raw `inputevents.rate` numeric type. No
`linkorderid` or `vaso_amount` appears in the target output.

### Exact dependency columns consumed by this concept

For each of the seven unqualified DAG dependency views, the target reads only:

- `stay_id`: used in `tm`, the `tm_lag` partition, every join, and the output.
- `starttime`: used as a boundary in `tm`, as the interval start in the output,
  and in every containment join.
- `endtime`: used as a boundary in `tm`, as the next interval end in the
  output, in the final null filter, and in every containment join.
- `vaso_rate`: projected into the corresponding final drug column.

The target does **not** read dependency `linkorderid` or `vaso_amount`. Those
columns exist in the child derived outputs but are outside this consumer's
dependency contract.

### Underlying `inputevents` columns selected or referenced by dependencies

The seven child SQL files select or reference these raw columns from
`mimiciv_icu.inputevents`:

- `itemid`: integer-like item discriminator used by each child `WHERE` clause.
- `stay_id`: integer-like ICU stay identifier, passed through to the child
  output and then consumed by this target.
- `linkorderid`: administrative/order linkage identifier, selected by each
  child but not consumed by this target.
- `rate`: numeric dose/rate value; selected directly or used in a child CASE
  expression to produce `vaso_rate`.
- `amount`: numeric amount value, selected as `vaso_amount` by each child but
  not consumed by this target.
- `starttime`, `endtime`: timestamp/datetime administration endpoints, passed
  through and consumed by this target.
- `rateuom`: string unit discriminator, referenced by the norepinephrine,
  phenylephrine, and vasopressin CASE expressions.
- `patientweight`: numeric weight field, referenced by the norepinephrine
  `patientweight = 1` branch and the phenylephrine `rate / patientweight`
  branch.

## 3. Filters and predicates

### Predicates in the target SQL

The only target `WHERE` predicate is:

- `vasoactive_agent.sql:127`: `t.endtime IS NOT NULL`. This removes the final
  boundary row of each `stay_id` partition after `LEAD` has produced a null
  next boundary.

There is no target time-window predicate, value-range predicate, code
exclusion, or direct itemid predicate. The interval containment expressions in
the joins are temporal predicates and are listed in the join section.

### Predicates in the seven dependency SQL files

Each child query filters `mimiciv_icu.inputevents` by one exact `itemid = ...`
literal. The complete code set is reproduced verbatim in the coding section.
The child queries do not filter on `starttime`, `endtime`, `rate`, or
`amount`.

Three child queries also use exact unit/value discriminators in `CASE`
expressions, not `WHERE` clauses:

- `norepinephrine.sql:8-11`: `rateuom = 'mg/kg/min'` and, in the first branch,
  `patientweight = 1`.
- `phenylephrine.sql:6-7`: `rateuom = 'mcg/min'`.
- `vasopressin.sql:10-11`: `rateuom = 'units/min'`.

These predicates determine the dependency `vaso_rate` values that the target
consumes. The target must consume those derived values rather than rederive
them.

The target's comments state that angiotensin II, methylene blue, and
isoprenaline/isoproterenol are not included because they are not documented in
MetaVision. These are comments only: no itemid literals or SQL exclusion
predicates for those drugs occur in the target.

## 4. Joins

After `tm_lag`, the final query performs seven `LEFT JOIN`s. Every join has the
same three-part containment condition; only the alias and dependency table
differ:

```sql
ON t.stay_id = <dep>.stay_id
   AND t.starttime >= <dep>.starttime
   AND t.endtime <= <dep>.endtime
```

The exact aliases/tables are:

| SQL lines | Type | Alias/table | Join condition |
|---|---|---|---|
| 97-100 | `LEFT JOIN` | `dob` / `mimiciv_derived.dobutamine` | `t.stay_id = dob.stay_id AND t.starttime >= dob.starttime AND t.endtime <= dob.endtime` |
| 101-104 | `LEFT JOIN` | `dop` / `mimiciv_derived.dopamine` | `t.stay_id = dop.stay_id AND t.starttime >= dop.starttime AND t.endtime <= dop.endtime` |
| 105-108 | `LEFT JOIN` | `epi` / `mimiciv_derived.epinephrine` | `t.stay_id = epi.stay_id AND t.starttime >= epi.starttime AND t.endtime <= epi.endtime` |
| 109-112 | `LEFT JOIN` | `nor` / `mimiciv_derived.norepinephrine` | `t.stay_id = nor.stay_id AND t.starttime >= nor.starttime AND t.endtime <= nor.endtime` |
| 113-116 | `LEFT JOIN` | `phe` / `mimiciv_derived.phenylephrine` | `t.stay_id = phe.stay_id AND t.starttime >= phe.starttime AND t.endtime <= phe.endtime` |
| 117-120 | `LEFT JOIN` | `vas` / `mimiciv_derived.vasopressin` | `t.stay_id = vas.stay_id AND t.starttime >= vas.starttime AND t.endtime <= vas.endtime` |
| 121-124 | `LEFT JOIN` | `mil` / `mimiciv_derived.milrinone` | `t.stay_id = mil.stay_id AND t.starttime >= mil.starttime AND t.endtime <= mil.endtime` |

There are no `INNER JOIN`s and no joins on `linkorderid`. Because the joins are
left-sided, a generated boundary interval remains in the output even when no
administration interval contains it; the corresponding drug rate is then
null. The SQL has no per-drug deduplication or tie-breaking if multiple child
rows satisfy a containment join.

## 5. `mimiciv_derived` dependencies

The DAG and the SQL agree on these seven dependencies:

1. `mimiciv_derived.dobutamine` → candidate stem `dobutamine`
2. `mimiciv_derived.dopamine` → candidate stem `dopamine`
3. `mimiciv_derived.epinephrine` → candidate stem `epinephrine`
4. `mimiciv_derived.milrinone` → candidate stem `milrinone`
5. `mimiciv_derived.norepinephrine` → candidate stem `norepinephrine`
6. `mimiciv_derived.phenylephrine` → candidate stem `phenylephrine`
7. `mimiciv_derived.vasopressin` → candidate stem `vasopressin`

Before this consumer runs, each completed dependency is available to candidate
SQL under its unqualified stem. The exact consumer contract is the four-column
set `stay_id`, `starttime`, `endtime`, `vaso_rate` for each dependency. The
consumer uses `vaso_rate` as the clinically named rate output and uses all
three identity/time fields to construct and overlay intervals. It does not
consume `linkorderid` or `vaso_amount`; do not reconstruct either from FHIR or
from raw resources for this target.

The child SQL source and transformations are:

- `dobutamine`: `stay_id`, `linkorderid`, `rate AS vaso_rate`,
  `amount AS vaso_amount`, `starttime`, `endtime` from `inputevents`, filtered
  to dobutamine itemid.
- `dopamine`: same output shape, filtered to dopamine itemid.
- `epinephrine`: same output shape, filtered to epinephrine itemid.
- `norepinephrine`: `vaso_rate` is a CASE-normalized rate based on
  `rateuom`/`patientweight`; `vaso_amount` is raw `amount`.
- `phenylephrine`: `vaso_rate` is `rate / patientweight` only for the
  `mcg/min` unit branch; otherwise raw `rate`.
- `vasopressin`: `vaso_rate` is `rate * 60.0` only for the `units/min` branch;
  otherwise raw `rate`.
- `milrinone`: same plain-rate output shape as dobutamine/dopamine/epinephrine.

## 6. Aggregations and temporal construction

- No `GROUP BY` appears.
- No scalar value aggregation (`MIN`, `MAX`, `AVG`, `SUM`, `ARRAY_AGG`, etc.)
  appears.
- `UNION DISTINCT` in `tm` is the only set-valued deduplication. It combines
  all starts and ends and removes duplicate `(stay_id, vasotime)` boundaries.
- `LEAD(vasotime, 1) OVER (PARTITION BY stay_id ORDER BY vasotime)` in
  `tm_lag` is the only window function. It pairs each ordered boundary with
  the following boundary in that ICU stay.

## 7. Literal code set, verbatim

The target SQL itself names no itemid. Its seven dependency SQL files name the
following exact itemid predicates. Every set filters the same source table,
`mimiciv_icu.inputevents`, and each selected dependency row contributes its
`stay_id`/`starttime`/`endtime` boundaries to `tm` and its `vaso_rate` to the
corresponding final output column.

| Exact SQL predicate | Source table filtered | Dependency CTE/table | Target CTE/output fed |
|---|---|---|---|
| `WHERE itemid = 221653` | `mimiciv_icu.inputevents` | `dobutamine` | `tm`; final `dobutamine` |
| `WHERE itemid = 221662` | `mimiciv_icu.inputevents` | `dopamine` | `tm`; final `dopamine` |
| `WHERE itemid = 221289` | `mimiciv_icu.inputevents` | `epinephrine` | `tm`; final `epinephrine` |
| `WHERE itemid = 221906` | `mimiciv_icu.inputevents` | `norepinephrine` | `tm`; final `norepinephrine` |
| `WHERE itemid = 221749` | `mimiciv_icu.inputevents` | `phenylephrine` | `tm`; final `phenylephrine` |
| `WHERE itemid = 222315` | `mimiciv_icu.inputevents` | `vasopressin` | `tm`; final `vasopressin` |
| `WHERE itemid = 221986` | `mimiciv_icu.inputevents` | `milrinone` | `tm`; final `milrinone` |

The exact non-itemid coded/value literals used as branch discriminators in the
dependency SQL are:

| Exact SQL condition/literal | Source table/field | Feeds |
|---|---|---|
| `rateuom = 'mg/kg/min'` | `mimiciv_icu.inputevents.rateuom` | `norepinephrine.vaso_rate` CASE branches |
| `patientweight = 1` | `mimiciv_icu.inputevents.patientweight` | first `norepinephrine.vaso_rate` CASE branch |
| `rateuom = 'mcg/min'` | `mimiciv_icu.inputevents.rateuom` | `phenylephrine.vaso_rate` normalized branch |
| `rateuom = 'units/min'` | `mimiciv_icu.inputevents.rateuom` | `vasopressin.vaso_rate` normalized branch |

There are no ICD codes, LOINC codes, medication-name strings, or coding-system
URIs in these canonical SQL files. The coded source field is the numeric
`inputevents.itemid`; the unit strings above are branch discriminators, not
additional row filters. The comments naming angiotensin II, methylene blue,
and isoprenaline/isoproterenol do not define a code set because no SQL itemid
for them is present.

## 8. Semantically essential inputs and propagation

The following inputs can change inclusion, grain, interval assignment, or a
clinically meaningful output:

1. **The seven child itemid filters** determine which raw `inputevents` enter
   each derived medication stream. They control both the boundary population
   in `tm` and the drug-specific rate columns in the final table.
2. **`stay_id` from every dependency** controls the `UNION DISTINCT` identity,
   `LEAD` partition, all seven containment joins, and the output patient/stay
   identity. It is part of the target's semantic row identity.
3. **Every dependency `starttime` and `endtime`** controls the boundary set,
   ordering, generated adjacent intervals, containment, final row timing, and
   whether an interval can receive each drug rate. A timestamp can therefore
   alter row inclusion, the natural grain, and rate assignment.
4. **The generated `t.endtime IS NOT NULL` condition** controls removal of the
   last boundary row per stay.
5. **Each dependency `vaso_rate`** controls the corresponding final clinical
   rate column. The upstream `rateuom` and `patientweight` discriminators and
   raw `rate` determine these values before this concept consumes them:
   `mg/kg/min`/`patientweight = 1` in norepinephrine, `mcg/min` in
   phenylephrine, and `units/min` in vasopressin are the branch conditions.

The target's natural semantic grain is one consecutive boundary interval per
`stay_id`, conventionally identified by `(stay_id, starttime, endtime)`, with
up to one rate column for each of the seven agents. This is not a source
`inputevents` row grain: `UNION DISTINCT` collapses equal boundaries regardless
of drug/order, and the left containment joins can match child administration
intervals. `linkorderid` is not part of the target grain or output, and
`vaso_amount` is not propagated.

## Files checked

- `mimic-iv/concepts/medication/vasoactive_agent.sql`.
- Its seven DAG dependency SQL files: `dobutamine.sql`, `dopamine.sql`,
  `epinephrine.sql`, `milrinone.sql`, `norepinephrine.sql`,
  `phenylephrine.sql`, and `vasopressin.sql`.
- `mimic-iv/concept_dag/concept_dag.json`, including the target node and all
  seven consumer/dependency edges.
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md` and the relevant provisional
  fragments `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `milrinone.md`,
  `norepinephrine.md`, `phenylephrine.md`, and `vasopressin.md`.
- Empty attempt workspace:
  `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/`.

This is source description only. No FHIR ViewDefinition or candidate SQL was
authored.
