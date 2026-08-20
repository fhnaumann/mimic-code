# Source analysis: `first_day_urine_output`

## Scope and authoritative sources

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_urine_output.sql`.
- DAG node: `mimic-iv/concept_dag/concept_dag.json`, node
  `first_day_urine_output`, path `firstday/first_day_urine_output.sql`,
  SHA256
  `2ddae1a9d4d0040bedbbb24b552576375f8aa4311e7c9b7ee2603227c5502f11`,
  level `1`.
- DAG dependency: exactly `urine_output`; the node's dependents are
  `apsiii`, `first_day_sofa`, `lods`, and `oasis`.
- DAG external raw-table entry: `mimiciv_icu.icustays` lists
  `first_day_urine_output`; the dependency's raw table is owned by the
  `urine_output` concept.
- Type checks: `mimic-iv/buildmimic/postgres/create.sql:415-425` for
  `icustays`; the full shape is in
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json:2125-2150`.
- Dataset notes/fragments reviewed: `MIMIC_NOTES.md`,
  `MIMIC_NOTES.d/urine_output.md`, `MIMIC_NOTES.d/first_day_bg.md`,
  `MIMIC_NOTES.d/rrt.md`, and `MIMIC_NOTES.d/icustay_times.md`.

## Query structure

The SQL is one grouped `SELECT`; it has no CTE:

```sql
SELECT
    ie.subject_id
    , ie.stay_id
    , SUM(urineoutput) AS urineoutput
FROM `physionet-data.mimiciv_icu.icustays` ie
LEFT JOIN `physionet-data.mimiciv_derived.urine_output` uo
    ON ie.stay_id = uo.stay_id
        AND uo.charttime >= ie.intime
        AND uo.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
GROUP BY ie.subject_id, ie.stay_id
```

The physical source names use the BigQuery project qualifier
`physionet-data`; the schemas/tables are `mimiciv_icu.icustays` and
`mimiciv_derived.urine_output`.

## Table references

| SQL reference | Schema/table | Alias | Role |
|---|---|---|---|
| `FROM physionet-data.mimiciv_icu.icustays` | `mimiciv_icu.icustays` | `ie` | One row per ICU stay backbone; supplies the subject, stay, and ICU admission time. |
| `LEFT JOIN physionet-data.mimiciv_derived.urine_output` | `mimiciv_derived.urine_output` | `uo` | Completed level-0 derived dependency; supplies time-stamped urine-output aggregates. |

There are no `mimiciv_hosp` tables and no other raw tables in this SQL.

## Columns and inferred types

The canonical SQL references the following columns. There are no intermediate
CTE columns.

| Reference | Inferred/source type | Use |
|---|---|---|
| `ie.subject_id` | `INTEGER` | Final `subject_id` and `GROUP BY` column. |
| `ie.stay_id` | `INTEGER` | Final `stay_id`, join key, and `GROUP BY` column. |
| `ie.intime` | `TIMESTAMP`/datetime | Inclusive lower boundary and input to the upper-bound expression. |
| `uo.stay_id` | `INTEGER` | Dependency-side join key. |
| `uo.charttime` | `TIMESTAMP`/datetime | Dependency-side event time used by both window predicates. |
| `uo.urineoutput` | Numeric, `DOUBLE` in the completed dependency/manifest | Input to the final `SUM`. |
| `DATETIME_ADD(ie.intime, INTERVAL '1' DAY)` | Datetime/timestamp | `intime + 24 hours`, the inclusive upper boundary. |
| `SUM(uo.urineoutput)` | `DOUBLE` in the full oracle manifest | Final `urineoutput` value. |

The source `icustays` DDL declares `subject_id`, `stay_id`, and `intime` as
non-null. The target does not reference `hadm_id`, `outtime`, care-unit fields,
or any other `icustays` column. It also does not reference any dependency
column other than `uo.stay_id`, `uo.charttime`, and `uo.urineoutput`.

## Dependency boundary

The source dependency is exactly `mimiciv_derived.urine_output`. For this port,
the completed dependency candidate must be consumed as the unqualified
candidate temp view named **`urine_output`** (aliased `uo`), not by reading
`mimiciv_icu.outputevents` and not by inlining or rederiving the dependency's
item/value transformation.

### Exact dependency read-set

The canonical consumer reads only:

| Dependency column | Consumer use |
|---|---|
| `uo.stay_id` | Equality join to `ie.stay_id`. |
| `uo.charttime` | Inclusive first-day temporal join window. |
| `uo.urineoutput` | Final `SUM`. |

The completed candidate `urine_output` also carries the opaque
`patient_key` and `icu_encounter_key` columns required by the full manifest.
Those are port key pass-throughs needed by the final output, not additional
source-SQL value inputs; they must not be reconstructed by parsing resource
IDs or by rederiving the dependency from FHIR resources.

## Joins and window boundaries

There is one **LEFT JOIN**:

```sql
ON ie.stay_id = uo.stay_id
   AND uo.charttime >= ie.intime
   AND uo.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

- The stay equality partitions dependency rows to the ICU stay.
- The lower boundary is inclusive: `uo.charttime >= ie.intime`.
- The upper boundary is inclusive: `uo.charttime <= ie.intime + 1 day`.
- The window is exactly the first 24 hours from `intime`; there is no
  `outtime` condition and no additional admission/stay filter.
- All three conditions are in the `ON` clause, not a `WHERE` clause. The
  `LEFT JOIN` therefore retains every `icustays` row even when no dependency
  row is in the window. With no `COALESCE`, `SUM` over an entirely unmatched
  stay is SQL-null rather than an explicitly supplied zero.

## Filters

The target SQL has **no `WHERE` clause** and no direct itemid, ICD, unit,
null, value-range, or code-exclusion predicate. Its only row-inclusion logic
is the three `LEFT JOIN ... ON` predicates above. In particular, the target
does not filter `itemid` itself; item-level selection belongs to the completed
`urine_output` dependency.

### Dependency-only code context (not a target filter)

For completeness, the dependency fragment/source analysis records that
`urine_output` itself filters `mimiciv_icu.outputevents.itemid` to the following
literal set. These literals are **not** to be copied into or rederived inside
`first_day_urine_output`; they are preserved here only as the exact upstream
dependency code specification:

```sql
226559 -- Foley
, 226560 -- Void
, 226561 -- Condom Cath
, 226584 -- Ileoconduit
, 226563 -- Suprapubic
, 226564 -- R Nephrostomy
, 226565 -- L Nephrostomy
, 226567 -- Straight Cath
, 226557 -- R Ureteral Stent
, 226558 -- L Ureteral Stent
, 227488 -- GU Irrigant Volume In
, 227489  -- GU Irrigant/Urine Volume Out
```

Each literal filters `mimiciv_icu.outputevents.itemid` for dependency CTE
`uo` and therefore feeds the dependency's grouped `urineoutput`. Literal
`227488` additionally selects the dependency CASE branch that negates a
positive irrigant-in value. No code literal is named by the target SQL itself,
and no target-level dead coded filter is present.

## Aggregation and grain

The final operation is:

```sql
SUM(uo.urineoutput) AS urineoutput
GROUP BY ie.subject_id, ie.stay_id
```

There are no window functions, `MIN`, `MAX`, `AVG`, `ARRAY_AGG`, `DISTINCT`,
or other aggregations. The output grain is one row per ICU stay, whose
manifest natural/comparison key is `stay_id`. `subject_id` is also grouped and
emitted, but is not the manifest key. All dependency rows satisfying the
stay/time predicates contribute to that stay's sum; no temporal carry-forward
or deduplication is performed by this query. The upstream dependency has
already grouped raw output events at `(stay_id, charttime)`; this target sums
those dependency rows across the first-day window.

## Required downstream candidate shape

The full oracle manifest entry for `first_day_urine_output` is:

| Column | Type | Comparison role |
|---|---|---|
| `subject_id` | `INTEGER` | Compared value; source `ie.subject_id`. |
| `stay_id` | `INTEGER` | Compared value and manifest natural key. |
| `urineoutput` | `DOUBLE` | Compared aggregate value. |
| `patient_key` | opaque resource key | Required `key_columns`; excluded from value comparison. |
| `icu_encounter_key` | opaque resource key | Required `key_columns`; excluded from value comparison. |

Manifest metadata: `comparison = keyed_join`, `key = [stay_id]`,
`key_columns = [icu_encounter_key, patient_key]`, `key_probes = 2`, and full
oracle row count `73181`. The candidate must emit all three value columns and
both required key columns. The key columns are not optional merely because
they are excluded from value comparison.

`subject_id` must be the integer MIMIC identifier recovered from the Patient
identifier value, and `stay_id` the integer MIMIC identifier recovered from
the ICU Encounter identifier value. The identifier values are FHIR strings,
so the downstream SQL needs integer output types. `patient_key` and
`icu_encounter_key` are the corresponding opaque, type-prefixed FHIR resource
keys used for equality joins and must be emitted verbatim/uncast. They are not
interchangeable with `Resource.id`, and no resource/reference ID may be
parsed, regenerated, hashed, hardcoded, or used to recover a source timestamp
or numeric identifier.

No `hadm_id`, `encounter_key`, `charttime`, `intime`, itemid, or raw
Observation identifier is part of this target's output shape.

## Semantically essential inputs

1. **`ie.stay_id`** controls the dependency partition, the output grouping,
   and the manifest natural key. Changing it can move measurements between
   stays, alter row existence, or alter `urineoutput`.
2. **`ie.subject_id`** is grouped and emitted as the patient identifier. It
   controls the patient value associated with the stay row and must remain
   paired with `stay_id`.
3. **`ie.intime`** controls both temporal boundaries. It determines which
   dependency rows are included in the first-day sum.
4. **`uo.stay_id`** controls the equality side of the LEFT JOIN and therefore
   which ICU stay can receive each dependency row.
5. **`uo.charttime`** controls inclusion at the two inclusive boundaries. It
   is not an output column, but changing it can add/drop a row from the sum or
   move it across stays' windows.
6. **`uo.urineoutput`** supplies the numeric contribution to the clinically
   meaningful aggregate. Every matched dependency row contributes, including
   duplicate times already represented by the completed dependency's grouped
   output.
7. **The exact 24-hour interval and LEFT JOIN/SUM semantics** are essential:
   the inclusive upper endpoint and preservation of unmatched ICU stays must
   not be silently changed to an exclusive bound, `INNER JOIN`, or
   `COALESCE(..., 0)`.
8. **Opaque key columns** `patient_key` and `icu_encounter_key` are essential
   for the required downstream resource joins, although they are excluded
   from value comparison. Preserve them by equality/pass-through only; they
   do not encode clinical values.

## Dataset-wide FHIR quirk to carry forward

The relevant stream-specific fragment is `MIMIC_NOTES.d/urine_output.md`:
outputevents Observations use `effectiveDateTime` only, and the upstream ETL
casts outputevents `charttime` through `TIMESTAMPTZ`, irreversibly normalizing
spring-forward DST-gap wall times. Because this concept uses dependency
`charttime` in an inclusive window and then aggregates by stay, a shifted time
can change first-day inclusion and/or the aggregate, not merely an ancillary
timestamp. The fragment reports the accepted `urine_output` full-data
divergence (393 shifted keys and 232 aggregation conflicts). Preserve the
MIMIC wall-clock value with the repository's `TIMESTAMP_NTZ` guidance; never
use an opaque resource ID to repair or infer the lost source time.

The reviewed `first_day_bg.md`, `rrt.md`, and `icustay_times.md` findings are
about labevents or chartevents and do not add a direct source filter or join to
this outputevents-based target.

## Summary

`first_day_urine_output` retains every ICU stay from `mimiciv_icu.icustays`,
LEFT JOINs the completed `urine_output` dependency on stay and the inclusive
`[intime, intime + 1 day]` window, and sums dependency `urineoutput` to one
row per `stay_id`. The exact target values are `(subject_id INTEGER,
stay_id INTEGER, urineoutput DOUBLE)`, with required opaque
`patient_key` and `icu_encounter_key` pass-through columns; the target itself
has no coded filter and must not inline the upstream itemid logic.
