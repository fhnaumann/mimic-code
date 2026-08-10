# Source analysis: coagulation

## Source and DAG identity

- Concept: `coagulation`
- Canonical SQL: `mimic-iv/concepts/measurement/coagulation.sql`
- DAG path: `measurement/coagulation.sql`
- DAG level: `0`
- DAG source SHA256: `d6f9ba24d8872e3eaed92707522dd2f24a51f879dd77feebe25ee9c6b08225dc`
- DAG dependencies: none.
- DAG dependent recorded in `concept_dag.json`: `first_day_lab`.
- The SQL contains no `mimiciv_derived` reference, so no derived concept needs to be ported first for this source query.

The canonical query has no CTE. It reads one raw hospital table, filters it, pivots six selected lab itemids, and groups the result by laboratory specimen.

## Table references

| SQL reference | Schema | Table | Alias | Use |
|---|---|---|---|---|
| `` `physionet-data.mimiciv_hosp.labevents` le `` | `mimiciv_hosp` (with the BigQuery project prefix `physionet-data`) | `labevents` | `le` | Sole source table |

The source table is therefore `mimiciv_hosp.labevents`. There are no references to `mimiciv_icu`, `mimiciv_derived`, a dimension table, or any other table.

## Columns and inferred types

The only source columns selected or referenced are `subject_id`, `hadm_id`, `charttime`, `specimen_id`, `itemid`, and `valuenum`; the unqualified references bind to alias `le`.

| Final output column | SQL expression | Source column(s) | Inferred/output type |
|---|---|---|---|
| `subject_id` | `MAX(subject_id)` | `le.subject_id` | `INTEGER`; source is `INTEGER NOT NULL` |
| `hadm_id` | `MAX(hadm_id)` | `le.hadm_id` | `INTEGER`; source is nullable |
| `charttime` | `MAX(charttime)` | `le.charttime` | `TIMESTAMP`; source is `TIMESTAMP(0)` and nullable |
| `specimen_id` | `le.specimen_id` | `le.specimen_id` | `INTEGER`; source is `INTEGER NOT NULL` |
| `d_dimer` | `MAX(CASE WHEN itemid = 51196 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE`; `valuenum` is `DOUBLE PRECISION` |
| `fibrinogen` | `MAX(CASE WHEN itemid = 51214 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE` |
| `thrombin` | `MAX(CASE WHEN itemid = 51297 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE` |
| `inr` | `MAX(CASE WHEN itemid = 51237 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE` |
| `pt` | `MAX(CASE WHEN itemid = 51274 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE` |
| `ptt` | `MAX(CASE WHEN itemid = 51275 THEN valuenum ELSE NULL END)` | `le.itemid`, `le.valuenum` | `DOUBLE` |

The source DDL supporting these types is `mimic-iv/buildmimic/postgres/create.sql:166-183`: `subject_id INTEGER NOT NULL`, `hadm_id INTEGER`, `specimen_id INTEGER NOT NULL`, `itemid INTEGER NOT NULL`, `charttime TIMESTAMP(0)`, and `valuenum DOUBLE PRECISION`. The full oracle manifest independently records the output types as `INTEGER`, `INTEGER`, `TIMESTAMP`, `INTEGER`, and six `DOUBLE` columns.

`subject_id`, `hadm_id`, and `charttime` are aggregated independently with `MAX`; they are not carried from a designated source row. Each analyte output is nullable when that itemid has no qualifying non-null numeric row within the specimen group. The SQL does not select `value`, `valueuom`, `ref_range_lower`, `ref_range_upper`, `flag`, `priority`, `comments`, `storetime`, `labevent_id`, or any other labevents column.

## Filters

The query has exactly two executable `WHERE` predicates:

1. `le.itemid IN (...)`: retains only the active itemid set reproduced verbatim below.
2. `valuenum IS NOT NULL`: excludes every selected item row whose numeric value is NULL. There is no fallback to `value` or `comments` in the source SQL.

There is no time window, no subject/admission filter, no lower or upper numeric plausibility bound, no positivity constraint, and no separate code exclusion predicate.

### Literal code set, verbatim

This is the executable coded filter on source table `mimiciv_hosp.labevents`:

```sql
le.itemid IN
    (
        -- Bleeding Time, no data as of MIMIC-IV v0.4
        -- 51149, 52750, 52072, 52073
        51196 -- D-Dimer
        , 51214 -- Fibrinogen
        -- Reptilase Time, no data as of MIMIC-IV v0.4
        -- 51280, 52893,
        -- Reptilase Time Control, no data as of MIMIC-IV v0.4
        -- 51281, 52161,
        , 51297 -- thrombin
        , 51237 -- INR
        , 51274 -- PT
        , 51275 -- PTT
    )
```

Active itemid-to-output mapping, all filtering `mimiciv_hosp.labevents.itemid` and feeding the named final pivot column:

| Exact itemid literal | SQL label/comment | Final output column |
|---:|---|---|
| `51196` | `D-Dimer` | `d_dimer` |
| `51214` | `Fibrinogen` | `fibrinogen` |
| `51297` | `thrombin` | `thrombin` |
| `51237` | `INR` | `inr` |
| `51274` | `PT` | `pt` |
| `51275` | `PTT` | `ptt` |

The SQL also contains these comment-only historical itemid literals. They are not executable members of the `IN` predicate and feed no output column; they are retained here so they are not mistaken for omitted code specifications:

```text
51149, 52750, 52072, 52073       -- Bleeding Time, no data as of MIMIC-IV v0.4
51280, 52893                      -- Reptilase Time, no data as of MIMIC-IV v0.4
51281, 52161                      -- Reptilase Time Control, no data as of MIMIC-IV v0.4
```

No ICD code, LOINC literal, or explicit coding-system URI appears in this SQL. The coded source field is the numeric `labevents.itemid`. The coding policy and `MIMIC_NOTES.md` state that labevents itemids are proprietary item codes and are carried verbatim by the FHIR labevents stream; the SQL itself performs no translation or dimension lookup.

## Joins

There are no joins: no `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `FULL JOIN`, or implicit comma join appears in the query. Alias `le` is only the alias of the single `FROM` table.

## Aggregation and grouping

- One `GROUP BY`: `GROUP BY le.specimen_id`.
- Aggregates:
  - `MAX(subject_id)` → `subject_id`.
  - `MAX(hadm_id)` → `hadm_id`.
  - `MAX(charttime)` → `charttime`.
  - Six conditional `MAX` pivots over `valuenum` → `d_dimer`, `fibrinogen`, `thrombin`, `inr`, `pt`, and `ptt`.
- There are no window functions, `MIN`, `SUM`, `AVG`, `COUNT`, array aggregations, rounding, casts, arithmetic conversions, or post-aggregation filters.

The aggregation means one output row is produced for each `specimen_id` having at least one retained row. If a specimen has multiple qualifying rows for the same itemid, that analyte column receives the maximum `valuenum`. If the source data has multiple `subject_id`, `hadm_id`, or `charttime` values in one specimen group, each metadata field independently receives its maximum; the SQL does not enforce or select a single coherent source row.

## Natural-key implications

The SQL's grouping key and emitted identifier imply `specimen_id` as the one-row-per-lab-specimen natural key, not `(subject_id, hadm_id, charttime)` and not an individual `labevent_id`. `specimen_id` is non-null in the source DDL. The full oracle manifest confirms `comparison: keyed_join` with `key: ["specimen_id"]` for `coagulation`, with 1,543,003 oracle rows.

For a FHIR-side reproduction, the source identity is the lab specimen identifier. The relevant established dataset note says that lab `Observation.specimen` resolves to a `Specimen` whose lab identifier value preserves relational `labevents.specimen_id`; this is why grouping by patient and time would not be source-equivalent. This is a mapping implication for downstream stages, not an additional source-SQL join.

## Dependencies and relevant dataset notes

- No `mimiciv_derived` dependency exists; the DAG dependency list is empty.
- `MIMIC_NOTES.md` records that MIMIC-IV 2.2 `d_labitems` has no `loinc_code`, so no relational LOINC mapping should be inferred for these itemids. It also records that itemid-derived Observation codes preserve the exact itemid and that lab specimen identifiers preserve `specimen_id`.
- `MIMIC_NOTES.md` records incomplete lab Observation encounter references. This matters because the source directly outputs `labevents.hadm_id`; a downstream port must not treat absence of an FHIR encounter reference as evidence that the source row is absent. The source SQL itself does not join admissions or encounters.
- The relevant provisional fragment `MIMIC_NOTES.d/blood_differential.md` warns that FHIR `valueQuantity` may be synthesized from source text when `valuenum` is NULL. This coagulation SQL explicitly excludes `valuenum IS NULL`, so that source predicate must remain semantically distinct from a generic "any FHIR Quantity exists" test.
- The relevant provisional fragment `MIMIC_NOTES.d/cardiac_marker.md` warns to constrain the Observation coding system and exact code before integer casts because ED LOINC codes can coexist in the Observation table. The coagulation source set is labevents-only and has no ED code, but the warning is relevant to downstream filtering.
- No new dataset-wide quirk was established by source analysis; nothing should be appended to `MIMIC_NOTES.d/coagulation.md` on the basis of this stage alone.

## Source-analysis summary

`coagulation.sql` is a level-0, dependency-free pivot over `mimiciv_hosp.labevents`. It retains six exact numeric itemids and non-null `valuenum` rows, aggregates by non-null `specimen_id`, and emits ten columns: three independently maximized metadata fields, the specimen key, and six nullable DOUBLE analyte pivots. It has no joins, time windows, value bounds, code translations, CTEs, or window functions.
