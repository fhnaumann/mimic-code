# Source analysis: `urine_output`

## Scope and source of facts

- Canonical SQL: `mimic-iv/concepts/measurement/urine_output.sql` (38 lines).
- Source table type declarations checked in
  `mimic-iv/buildmimic/postgres/create.sql:480-492`.
- DAG node checked in `mimic-iv/concept_dag/concept_dag.json`: stem
  `urine_output`, path `measurement/urine_output.sql`, level `0`, no
  dependencies, and dependents `first_day_urine_output`, `kdigo_uo`, `sapsii`,
  and `urine_output_rate`.
- The full oracle manifest records the resulting output shape as
  `stay_id INTEGER`, `charttime TIMESTAMP`, and `urineoutput DOUBLE`, with
  empirical comparison key `(stay_id, charttime)`.

## Query structure

The SQL has one CTE, `uo`, followed by one grouped final `SELECT`.

### Table references

The only `FROM` clause is:

```sql
FROM `physionet-data.mimiciv_icu.outputevents` oe
```

This is the `mimiciv_icu.outputevents` table (the `physionet-data` project
qualifier is part of the canonical BigQuery-style name), aliased as `oe`.
There are no other `FROM` clauses and no `JOIN` clauses. The SQL references no
`mimiciv_derived` table.

The DAG's `external_tables` entry independently lists
`mimiciv_icu.outputevents` as an external/raw dependency of `urine_output`.

### Intermediate CTE: `uo`

The CTE selects one row for each source output-event row that survives the
itemid filter:

```sql
SELECT
    oe.stay_id
    , oe.charttime
    , CASE
        WHEN oe.itemid = 227488 AND oe.value > 0 THEN -1 * oe.value
        ELSE oe.value
      END AS urineoutput
```

Inferred source and CTE types:

| Field | Source/reference | Inferred type | Role |
|---|---|---|---|
| `oe.stay_id` / `uo.stay_id` | `mimiciv_icu.outputevents.stay_id` | `INTEGER` | ICU stay identity and later grouping/output key |
| `oe.charttime` / `uo.charttime` | `mimiciv_icu.outputevents.charttime` | `TIMESTAMP(3)` in the repository PostgreSQL DDL; timestamp/datetime semantically | Event time and later grouping/output key |
| `oe.itemid` | `mimiciv_icu.outputevents.itemid` | `INTEGER` | Item-code filter and GU-irrigant branch discriminator |
| `oe.value` | `mimiciv_icu.outputevents.value` | `FLOAT` | Measured volume and sign-transform input |
| `uo.urineoutput` | CASE expression over `oe.value` | floating-point numeric, source-value-compatible | Per-source-row volume passed to `SUM` |

The source DDL declares `stay_id`, `charttime`, `itemid`, and `value` as
non-null. The CTE does not select `subject_id`, `hadm_id`, `storetime`,
`caregiver_id`, or `valueuom`; none of those fields affect this SQL.

### Final output columns and types

The final query is:

```sql
SELECT
    stay_id
    , charttime
    , SUM(urineoutput) AS urineoutput
FROM uo
GROUP BY stay_id, charttime
```

The output columns, in order, are:

| Output column | Type | Derivation |
|---|---|---|
| `stay_id` | `INTEGER` | `uo.stay_id`, also a grouping column |
| `charttime` | `TIMESTAMP` | `uo.charttime`, also a grouping column |
| `urineoutput` | `DOUBLE` in the oracle manifest; floating-point aggregate of the `FLOAT` CTE expression | `SUM(uo.urineoutput)` |

## Filters and value transformation

The only `WHERE` predicate is the item-code inclusion filter. There is no time
window, unit filter, null filter, value-range filter, code exclusion, or other
predicate:

```sql
WHERE itemid IN
    (
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
    )
```

The unqualified `itemid` in the `WHERE` clause resolves to the only source
table's `oe.itemid`.

The CASE expression is not a row filter. It changes the per-row value only
when both conditions hold: the item is literal `227488` and `oe.value > 0`.
For that branch the value is negated (`-1 * oe.value`). For zero or negative
`227488` values, and for every other included itemid, the original `oe.value`
is retained.

## Literal code specification

The SQL names one coded filter: `mimiciv_icu.outputevents.itemid IN (...)`.
The exact literal set, in source order and with source comments retained, is:

| Exact literal | Source table/field | Feeds |
|---|---|---|
| `226559` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226560` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226561` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226584` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226563` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226564` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226565` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226567` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226557` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `226558` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |
| `227488` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion and the CASE discriminator controlling `uo.urineoutput` sign |
| `227489` | `mimiciv_icu.outputevents.itemid` | `uo` row inclusion; final grouped `urineoutput` |

There are no ICD codes, other code systems, or additional literal coded sets.
No dead filter is identifiable from the canonical SQL alone; all twelve listed
itemids are present-in-SQL and must remain in the port specification.

## Joins and dependencies

- Joins: none. Consequently there are no INNER/LEFT join types or join
  conditions to reproduce.
- `mimiciv_derived` references: none.
- Upstream DAG dependencies: none; `urine_output` is a level-0 concept.
- Downstream DAG dependents (not inputs to this SQL):
  `first_day_urine_output`, `kdigo_uo`, `sapsii`, and `urine_output_rate`.

## Aggregation and grain

- The CTE preserves the filtered source-event grain: one CTE row per selected
  `outputevents` row.
- The final `GROUP BY stay_id, charttime` produces one row per `(stay_id,
  charttime)` pair.
- `SUM(urineoutput)` adds all selected and transformed source rows sharing
  that pair. There is no `DISTINCT`, window function, or other aggregation.
  Duplicate source events at the same pair therefore contribute separately.
- The output grain and the manifest's empirical keyed comparison key are both
  `(stay_id, charttime)`; this key is created by the aggregation rather than
  by retaining an individual source-event identifier.

## Semantically essential inputs

1. **`oe.stay_id`** — controls the ICU-stay partition and is part of the final
   natural row identity. A change can move a source measurement to another
   output row or change which rows exist for a stay.
2. **`oe.charttime`** — controls temporal grouping and is the other part of the
   final row identity. A change can split or merge output rows at different
   times.
3. **`oe.itemid`** — controls inclusion through the exact twelve-value `IN`
   predicate. It also selects the special `227488` CASE branch, so it affects
   both whether a row contributes and whether its contribution is negated.
4. **`oe.value`** — supplies the volume contribution. Its sign and magnitude
   determine the aggregate; for item `227488`, the discriminator `value > 0`
   determines whether the contribution is negated. It is not itself used to
   exclude rows.
5. **The grouping operation** — `SUM` over `(stay_id, charttime)` is clinically
   meaningful to the derived output and must preserve multiplicity of source
   events at the same key. There is no temporal carry-forward or time-window
   logic in this concept.

## Dataset-wide provisional leads for the orchestrator

The read-only `MIMIC_NOTES.md` entries relevant to a future FHIR mapping say
that itemid-derived `Observation` streams preserve the source itemid verbatim
in `Observation.code.coding.code`, and that `outputevents` uses the proprietary
system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`. They also warn that
`outputevents` and `datetimeevents` share this system, so a downstream mapping
should discriminate on system plus the exact code and not on `meta.profile`.
These are dataset-wide notes/provisional leads for the prober, not additional
source-SQL filters or a code translation. The general FHIR datetime note in
`MIMIC_NOTES.md` also says to preserve MIMIC wall-clock values with
`TIMESTAMP_NTZ` rather than converting the offset; the exact outputevents
effective-time behavior still requires concept-specific probing.

No `MIMIC_NOTES.d/urine_output.md` fragment existed when this analysis was
written, and no fragment was modified.

## Summary

`urine_output` is a level-0, raw-ICU concept with no derived-table dependency
and no joins. It filters `mimiciv_icu.outputevents` to twelve exact itemids,
negates positive GU-irrigant-in values for item `227488`, and sums the resulting
volumes at the `(stay_id, charttime)` grain into the three-column output
`(stay_id INTEGER, charttime TIMESTAMP, urineoutput DOUBLE)`.
