# Source analysis: `vitalsign`

## Source and DAG metadata

- Canonical SQL: `mimic-iv/concepts/measurement/vitalsign.sql`.
- DAG node: `vitalsign`, path `measurement/vitalsign.sql`, level `0`.
- DAG SHA-256: `9a618fb7f6bf74ed1571e08088b09d1f27a8ccf8b1054082a94270cde456ab0d`; the checked canonical SQL has this hash.
- Dependencies in `concept_dag.json`: none. Dependents are `first_day_vitalsign`, `sapsii`, and `sofa`.
- The SQL has no CTEs and no reference to `mimiciv_derived`.

## Table references

The only table reference is:

| SQL occurrence | Type | Schema | Table | Alias |
|---|---|---|---|---|
| `FROM` | source table | `mimiciv_icu` | `chartevents` | `ce` |

There are no `JOIN` clauses. Every unqualified `itemid` and `valuenum` in the expressions resolves to `ce.itemid` and `ce.valuenum`.

## Source columns and inferred types

The source columns referenced by the query are:

| Source expression | Inferred source type | Uses |
|---|---|---|
| `ce.subject_id` | integer | selected and grouped; output identifier |
| `ce.stay_id` | integer | `IS NOT NULL` filter, selected and grouped; output identifier |
| `ce.charttime` | timestamp / `TIMESTAMP WITHOUT TIME ZONE` wall-clock value | selected and grouped; output time |
| `ce.itemid` | integer | global item filter and all conditional measurement branches |
| `ce.valuenum` | floating-point numeric, conventionally `DOUBLE PRECISION` | numeric plausibility filters, Fahrenheit conversion, and numeric aggregates |
| `ce.value` | text / `VARCHAR` | `temperature_site` aggregate only |

The SQL does not reference `storetime`, `hadm_id`, `warning`, `error`, `resultstatus`, or any `d_items` column.

## Final output columns and inferred types

The result is one row per `GROUP BY` tuple `(subject_id, stay_id, charttime)`, in this order:

| Output column | SQL expression | Inferred type | Meaning of the expression |
|---|---|---|---|
| `subject_id` | `ce.subject_id` | integer | Group/output identifier |
| `stay_id` | `ce.stay_id` | integer | Group/output ICU stay identifier |
| `charttime` | `ce.charttime` | timestamp | Group/output charted time |
| `heart_rate` | `AVG(CASE WHEN itemid IN (220045) AND valuenum > 0 AND valuenum < 300 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid value for item `220045` |
| `sbp` | `AVG(CASE WHEN itemid IN (220179, 220050, 225309) AND valuenum > 0 AND valuenum < 400 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid value across the three SBP item streams |
| `dbp` | `AVG(CASE WHEN itemid IN (220180, 220051, 225310) AND valuenum > 0 AND valuenum < 300 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid value across the three DBP item streams |
| `mbp` | `AVG(CASE WHEN itemid IN (220052, 220181, 225312) AND valuenum > 0 AND valuenum < 300 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid value across the three MBP item streams |
| `sbp_ni` | `AVG(CASE WHEN itemid = 220179 AND valuenum > 0 AND valuenum < 400 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid non-invasive SBP value |
| `dbp_ni` | `AVG(CASE WHEN itemid = 220180 AND valuenum > 0 AND valuenum < 300 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid non-invasive DBP value |
| `mbp_ni` | `AVG(CASE WHEN itemid = 220181 AND valuenum > 0 AND valuenum < 300 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid non-invasive MBP value |
| `resp_rate` | `AVG(CASE WHEN itemid IN (220210, 224690) AND valuenum > 0 AND valuenum < 70 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid value across the two respiratory-rate item streams |
| `temperature` | `ROUND(CAST(AVG(CASE ... END) AS NUMERIC), 2)` | `NUMERIC`, rounded to two decimal places | Fahrenheit item `223761` is converted by `(valuenum - 32) / 1.8`; Celsius item `223762` is used unchanged |
| `temperature_site` | `MAX(CASE WHEN itemid = 224642 THEN value END)` | text / `VARCHAR` | Lexicographic maximum non-NULL source `value` among item `224642` rows in the group |
| `spo2` | `AVG(CASE WHEN itemid IN (220277) AND valuenum > 0 AND valuenum <= 100 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean valid peripheral oxygen saturation value |
| `glucose` | `AVG(CASE WHEN itemid IN (225664, 220621, 226537) AND valuenum > 0 THEN valuenum END)` | `DOUBLE PRECISION`-like floating numeric | Mean positive value across the three glucose item streams |

Every `CASE` has no `ELSE`, so nonmatching or invalid rows contribute `NULL`; `AVG` ignores those values and returns `NULL` when its branch has no valid input in a group. `temperature_site` likewise ignores NULL `value` values through `MAX`.

## WHERE filters and value constraints

The only `WHERE` clause has two predicates:

1. `ce.stay_id IS NOT NULL` — removes chartevents rows without an ICU stay.
2. `ce.itemid IN (...)` — restricts the source rows to the exact active itemid set copied below.

There are no time-window predicates, patient filters, code exclusions, `value IS NOT NULL` predicate, or explicit `valuenum IS NOT NULL` predicate. Numeric NULLs fail the comparison predicates in the conditional branches.

The conditional value constraints are:

- `heart_rate`: `valuenum > 0 AND valuenum < 300`.
- `sbp` and `sbp_ni`: `valuenum > 0 AND valuenum < 400`.
- `dbp`, `mbp`, `dbp_ni`, and `mbp_ni`: `valuenum > 0 AND valuenum < 300`.
- `resp_rate`: `valuenum > 0 AND valuenum < 70`.
- Fahrenheit `temperature` (`223761`): `valuenum > 70 AND valuenum < 120`.
- Celsius `temperature` (`223762`): `valuenum > 10 AND valuenum < 50`.
- `spo2`: `valuenum > 0 AND valuenum <= 100`.
- `glucose`: `valuenum > 0` with no upper bound.
- `temperature_site`: no value constraint; it uses source `value` for item `224642`.

All bounds are strict except the upper bound for `spo2`, which is inclusive.

## Joins and dependencies

- Joins: none, so there are no INNER or LEFT join conditions.
- `mimiciv_derived` dependencies: none.
- Other schemas/tables: none; the only source is `mimiciv_icu.chartevents`.

## Aggregations and grain

- `GROUP BY ce.subject_id, ce.stay_id, ce.charttime` creates the natural result grain/key `(subject_id, stay_id, charttime)`.
- There are no window functions and no intermediate CTE aggregations.
- Numeric values use `AVG` after each branch's itemid and plausibility test. Multiple source rows sharing a group key are combined; source row identity and item-level multiplicity are not emitted.
- `temperature` averages the converted Fahrenheit values and unchanged Celsius values together, then casts that average to `NUMERIC` and rounds it to two decimal places.
- `temperature_site` uses `MAX` over source text, not an average or a time ranking. If multiple item `224642` text values occur at one group key, the SQL returns the database's text maximum.

## Literal code specification (verbatim)

The query uses no ICD codes or other coding systems. All codes are integer `itemid` literals on `mimiciv_icu.chartevents`; the FHIR-side coding system lead in `MIMIC_NOTES.md` is the chartevents item system (`.../CodeSystem/mimic-chartevents-d-items`). The exact active global filter is:

```sql
ce.itemid IN
(
    220045 -- Heart Rate
    , 225309 -- ART BP Systolic
    , 225310 -- ART BP Diastolic
    , 225312 -- ART BP Mean
    , 220050 -- Arterial Blood Pressure systolic
    , 220051 -- Arterial Blood Pressure diastolic
    , 220052 -- Arterial Blood Pressure mean
    , 220179 -- Non Invasive Blood Pressure systolic
    , 220180 -- Non Invasive Blood Pressure diastolic
    , 220181 -- Non Invasive Blood Pressure mean
    , 220210 -- Respiratory Rate
    , 224690 -- Respiratory Rate (Total)
    , 220277 -- SPO2, peripheral
    -- GLUCOSE, both lab and fingerstick
    , 225664 -- Glucose finger stick
    , 220621 -- Glucose (serum)
    , 226537 -- Glucose (whole blood)
    -- TEMPERATURE
    -- 226329 -- Blood Temperature CCO (C)
    , 223762 -- "Temperature Celsius"
    , 223761  -- "Temperature Fahrenheit"
    , 224642 -- Temperature Site
)
```

The following branch code sets filter the same source table and feed the listed output columns. The parenthesized literals and ordering are preserved from each source expression:

```sql
itemid IN (220045)                         -- heart_rate
itemid IN (220179, 220050, 225309)         -- sbp
itemid IN (220180, 220051, 225310)         -- dbp
itemid IN (220052, 220181, 225312)         -- mbp
itemid = 220179                            -- sbp_ni
itemid = 220180                            -- dbp_ni
itemid = 220181                            -- mbp_ni
itemid IN (220210, 224690)                 -- resp_rate
itemid IN (223761)                         -- temperature, Fahrenheit branch
itemid IN (223762)                         -- temperature, Celsius branch
itemid = 224642                            -- temperature_site
itemid IN (220277)                         -- spo2
itemid IN (225664, 220621, 226537)         -- glucose
```

The literal `226329` appears only in a SQL comment (`-- 226329 -- Blood Temperature CCO (C)`) and is not an executed filter or output branch; it must not be treated as an active code in this port specification.

Code-to-output trace, including overlaps:

- `220045` → `heart_rate`.
- `220179` → `sbp` and `sbp_ni`.
- `220050`, `225309` → `sbp`.
- `220180` → `dbp` and `dbp_ni`.
- `220051`, `225310` → `dbp`.
- `220052` and `225312` → `mbp`; `220181` → `mbp` and `mbp_ni`.
- `220210`, `224690` → `resp_rate`.
- `223761` → Fahrenheit branch of `temperature`; `223762` → Celsius branch of `temperature`.
- `224642` → `temperature_site`.
- `220277` → `spo2`.
- `225664`, `220621`, `226537` → `glucose`.

## Semantically essential inputs

- `ce.stay_id`: its non-NULL status controls row inclusion; its value participates in the natural group key and is emitted as `stay_id`.
- `ce.subject_id`: participates in the group key and is emitted as `subject_id`; changing it can split or merge output rows.
- `ce.charttime`: participates in the group key and is emitted as `charttime`; changing it can split or merge every aggregate row. This SQL has no separate temporal window or carry-forward.
- `ce.itemid`: controls global source inclusion and selects the output branch. It determines whether a row contributes to heart rate, the combined or non-invasive blood-pressure columns, respiratory rate, one of the two temperature conversion branches, temperature site, SpO2, or glucose.
- `ce.valuenum`: controls numeric branch inclusion through the stated bounds and supplies the values consumed by all `AVG`s and the temperature conversion. A NULL or out-of-range value is excluded from the relevant aggregate but does not by itself remove the group if another selected item remains.
- `ce.value`: controls `temperature_site` for item `224642`; its lexical maximum is emitted. It is not used by the numeric branches.
- Source-row multiplicity at a shared `(subject_id, stay_id, charttime)` is essential to the aggregate result: repeated qualifying rows affect `AVG`, and repeated temperature-site strings can affect `MAX`. The SQL does not deduplicate before aggregation.

## Relevant notes/leads reviewed

The curated `MIMIC_NOTES.md` entries relevant to this chartevents pivot state that itemid-derived Observation codes preserve the source itemid verbatim, that the chartevents coding system is `mimic-chartevents-d-items`, that subtype discrimination should use base code bindings rather than `meta.profile`, and that chartevents `Observation.effectiveDateTime` can have an upstream New York DST spring-forward normalization. The relevant provisional fragments read were `crrt.md`, `gcs.md`, `height.md`, `icp.md`, `oxygen_delivery.md`, `rhythm.md`, `rrt.md`, `icustay_times.md`, `kdigo_creatinine.md`, and `coagulation.md` (plus the generic item-code lead in `cardiac_marker.md`). They suggest, but do not establish for this concept without a target-specific probe, that chartevents resources may retain repeated same-item observations, omit source rows under global ETL predicates, and materialize effective-time choice aliases with mixed Spark types. The later policy sections rejecting resource-id reconstruction were also noted; no resource id is part of this source SQL.

For the orchestrator's `MIMIC_NOTES.d/vitalsign.md`: no new dataset-wide fact was independently verified by this source-only stage. The orchestrator/prober should append a vitalsign-owned fragment after served-data/full-run verification if the target itemids demonstrate the already-provisional chartevents `value IS NOT NULL`/hard-coded-duplicate omissions, repeated same-item cardinality at one `(stay_id, charttime)`, or DST-normalized charttime effects on this grouped aggregate. The curated itemid-preservation and chartevents-DST entries should be treated as existing leads rather than duplicated as new claims.
