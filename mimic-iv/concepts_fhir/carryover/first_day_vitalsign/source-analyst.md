# Source analysis: `first_day_vitalsign`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_vitalsign.sql`
- DAG stem: `first_day_vitalsign`
- DAG level: `1`
- DAG dependency: `vitalsign`
- DAG dependents: `apsiii`, `first_day_sofa`, `lods`, `oasis`, `sirs`
- DAG SHA256: `f85ecb807cbd23090b41f02af2253cf2e46ba8d50e8734fb2577be3a4b9af700`
- The SHA256 of the canonical SQL was checked and matches the DAG metadata.

The target SQL has no CTEs. Its only derived-schema input is
`mimiciv_derived.vitalsign`; this dependency must be ported first. Under the
candidate-SQL preprocessing convention, that dependency is available as the
unqualified table/view stem `vitalsign`. Its values must be consumed as
provided; this concept must not rederive them from FHIR resources.

## Referenced tables and columns

### `mimiciv_icu.icustays` (`ie`)

The canonical SQL references:

- `ie.subject_id`: selected and grouped. MIMIC integer identifier; inferred
  BigQuery type `INT64`.
- `ie.stay_id`: selected, grouped, and used in the join. MIMIC integer ICU
  stay identifier; inferred `INT64`.
- `ie.intime`: used only to construct the two inclusive time bounds. Source
  datetime; inferred `DATETIME`.

### `mimiciv_derived.vitalsign` (`ce`; dependency `vitalsign`)

The consumer reads exactly these dependency columns:

- `ce.stay_id`: equality join key; integer/`INT64`.
- `ce.charttime`: temporal join predicate; datetime/`DATETIME`.
- `ce.heart_rate`, `ce.sbp`, `ce.dbp`, `ce.mbp`, `ce.resp_rate`, `ce.spo2`,
  `ce.glucose`: numeric nullable values consumed by the three aggregates for
  each measure; inferred `FLOAT64` in the BigQuery source dialect because
  the dependency computes them from `AVG(valuenum)`.
- `ce.temperature`: numeric nullable value consumed by the three temperature
  aggregates; inferred `NUMERIC` because `vitalsign.sql` casts and rounds its
  source average as `NUMERIC`.

`ce.subject_id`, and the dependency outputs `sbp_ni`, `dbp_ni`, `mbp_ni`, and
`temperature_site`, are not read by this consumer. The dependency's own
`subject_id` is therefore not a join or output input for this concept.

### Upstream provenance table for the dependency: `mimiciv_icu.chartevents`

`mimiciv_icu.chartevents` is not a direct `FROM`/`JOIN` table in the target
SQL; it is the source table of the required `vitalsign` dependency. The
dependency references `subject_id`, `stay_id`, `charttime`, `itemid`,
`valuenum`, and `value`. The first four participate in dependency grouping or
filtering; `valuenum` supplies the numeric conditional averages and `value`
supplies the unused `temperature_site` aggregate. Its source types are
integer/`INT64` for the identifiers and itemid, `DATETIME` for `charttime`,
`FLOAT64` for `valuenum`, and nullable text for `value`.

## Join and time window

There is one `LEFT JOIN`, preserving every `icustays` row:

```sql
LEFT JOIN `physionet-data.mimiciv_derived.vitalsign` ce
    ON ie.stay_id = ce.stay_id
        AND ce.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
        AND ce.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

The join has no subject-level equality predicate. A dependency row is eligible
when its `stay_id` equals the ICU stay and its `charttime` is in the closed
interval `[ie.intime - 6 hours, ie.intime + 1 day]`. Both boundaries are
inclusive. The SQL comment says “first 24 hours,” but the actual lower boundary
is six hours before `intime`, not `intime` itself.

There is no target `WHERE`, `HAVING`, `ORDER BY`, `DISTINCT`, or inner join.
The `LEFT JOIN` means a stay with no eligible dependency rows remains in the
result, with NULL aggregate values.

## Output columns and inferred types

The final grain is one row per `icustays` row, grouped by
`(ie.subject_id, ie.stay_id)`. `stay_id` is the natural ICU-stay key in the
source; the emitted grouping key is the pair `(subject_id, stay_id)`.

| Output column | Expression | Inferred source type |
|---|---|---|
| `subject_id` | `ie.subject_id` | `INT64` |
| `stay_id` | `ie.stay_id` | `INT64` |
| `heart_rate_min` | `MIN(ce.heart_rate)` | nullable `FLOAT64` |
| `heart_rate_max` | `MAX(ce.heart_rate)` | nullable `FLOAT64` |
| `heart_rate_mean` | `AVG(ce.heart_rate)` | nullable `FLOAT64` |
| `sbp_min` | `MIN(ce.sbp)` | nullable `FLOAT64` |
| `sbp_max` | `MAX(ce.sbp)` | nullable `FLOAT64` |
| `sbp_mean` | `AVG(ce.sbp)` | nullable `FLOAT64` |
| `dbp_min` | `MIN(ce.dbp)` | nullable `FLOAT64` |
| `dbp_max` | `MAX(ce.dbp)` | nullable `FLOAT64` |
| `dbp_mean` | `AVG(ce.dbp)` | nullable `FLOAT64` |
| `mbp_min` | `MIN(ce.mbp)` | nullable `FLOAT64` |
| `mbp_max` | `MAX(ce.mbp)` | nullable `FLOAT64` |
| `mbp_mean` | `AVG(ce.mbp)` | nullable `FLOAT64` |
| `resp_rate_min` | `MIN(ce.resp_rate)` | nullable `FLOAT64` |
| `resp_rate_max` | `MAX(ce.resp_rate)` | nullable `FLOAT64` |
| `resp_rate_mean` | `AVG(ce.resp_rate)` | nullable `FLOAT64` |
| `temperature_min` | `MIN(ce.temperature)` | nullable `NUMERIC` |
| `temperature_max` | `MAX(ce.temperature)` | nullable `NUMERIC` |
| `temperature_mean` | `AVG(ce.temperature)` | nullable `NUMERIC` |
| `spo2_min` | `MIN(ce.spo2)` | nullable `FLOAT64` |
| `spo2_max` | `MAX(ce.spo2)` | nullable `FLOAT64` |
| `spo2_mean` | `AVG(ce.spo2)` | nullable `FLOAT64` |
| `glucose_min` | `MIN(ce.glucose)` | nullable `FLOAT64` |
| `glucose_max` | `MAX(ce.glucose)` | nullable `FLOAT64` |
| `glucose_mean` | `AVG(ce.glucose)` | nullable `FLOAT64` |

There are 26 output columns: two identifiers and 24 aggregate columns. SQL
aggregates ignore NULL input values. Thus an eligible charttime row whose
particular measure is NULL does not contribute to that measure; a stay with
no non-NULL values for a measure receives NULL for all three corresponding
outputs.

## Aggregations and dependency aggregation

The target has one `GROUP BY`:

```sql
GROUP BY ie.subject_id, ie.stay_id
```

It applies `MIN`, `MAX`, and `AVG` to each of the eight dependency measures:
`heart_rate`, `sbp`, `dbp`, `mbp`, `resp_rate`, `temperature`, `spo2`, and
`glucose`. There are no target window functions.

The upstream `measurement/vitalsign.sql` dependency itself groups
`mimiciv_icu.chartevents` by `ce.subject_id, ce.stay_id, ce.charttime`, so the
target aggregates charttime-level vital-sign rows rather than raw chart-event
rows. The dependency uses conditional `AVG` for the eight consumed measures;
its temperature expression converts Fahrenheit and Celsius streams, casts the
average to `NUMERIC`, and rounds to two decimal places before this target's
aggregates. It also computes unused `sbp_ni`, `dbp_ni`, `mbp_ni`, and
`temperature_site` outputs.

## Filters and literal code specification

### Filters in `first_day_vitalsign.sql`

The target has no `WHERE` clause and no literal item/code filter. Its only row
inclusion predicates are the three `ON` predicates documented above.

### Exact active filters in the `vitalsign` dependency

These are upstream dependency filters, not additional predicates in the target
file, but they define which `mimiciv_icu.chartevents` values can reach the
dependency columns consumed here. All itemids below filter
`mimiciv_icu.chartevents.itemid`; no ICD code or other coding system is used.

The dependency's active preselection is copied verbatim:

```sql
WHERE ce.stay_id IS NOT NULL
    AND ce.itemid IN
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

The commented `226329` is not an active filter and is not part of the active
code set. It is recorded here because it is named in the source SQL.

The exact conditional itemid sets and value constraints, each on the same
`mimiciv_icu.chartevents` source, are:

| Verbatim itemid literal(s) | Exact value predicate | Dependency output fed |
|---|---|---|
| `IN (220045)` | `valuenum > 0` and `valuenum < 300` | `heart_rate` |
| `IN (220179, 220050, 225309)` | `valuenum > 0` and `valuenum < 400` | `sbp` |
| `IN (220180, 220051, 225310)` | `valuenum > 0` and `valuenum < 300` | `dbp` |
| `IN (220052, 220181, 225312)` | `valuenum > 0` and `valuenum < 300` | `mbp` |
| `= 220179` | `valuenum > 0` and `valuenum < 400` | `sbp_ni` (not consumed by this target) |
| `= 220180` | `valuenum > 0` and `valuenum < 300` | `dbp_ni` (not consumed by this target) |
| `= 220181` | `valuenum > 0` and `valuenum < 300` | `mbp_ni` (not consumed by this target) |
| `IN (220210, 224690)` | `valuenum > 0` and `valuenum < 70` | `resp_rate` |
| `IN (223761)` | `valuenum > 70` and `valuenum < 120` | `temperature` (Fahrenheit branch) |
| `IN (223762)` | `valuenum > 10` and `valuenum < 50` | `temperature` (Celsius branch) |
| `= 224642` | no `valuenum` predicate; `MAX(value)` | `temperature_site` (not consumed by this target) |
| `IN (220277)` | `valuenum > 0` and `valuenum <= 100` | `spo2` |
| `IN (225664, 220621, 226537)` | `valuenum > 0` | `glucose` |

The dependency source has two separate temperature branches. The exact
temperature SQL is:

```sql
WHEN itemid IN (223761)
    AND valuenum > 70
    AND valuenum < 120
    THEN (valuenum - 32) / 1.8
WHEN itemid IN (223762)
    AND valuenum > 10
    AND valuenum < 50
    THEN valuenum
```

Therefore the exact temperature literals feed `temperature` as follows:

- `IN (223761)`, `valuenum > 70`, `valuenum < 120`: Fahrenheit branch,
  converted by `(valuenum - 32) / 1.8`.
- `IN (223762)`, `valuenum > 10`, `valuenum < 50`: Celsius branch, used as
  recorded.

The dependency then applies `ROUND(CAST(AVG(...) AS NUMERIC), 2)` to those
temperature values. The `224642` itemid feeds only the unused
`temperature_site` output through `MAX(value)` and is not a target input.

## Semantically essential inputs and control flow

1. **`ie.stay_id`** controls the natural row association, the join to
   `vitalsign`, the output key, and grouping. Changing it can change both row
   inclusion and which measurements are aggregated.
2. **`ie.subject_id`** controls the grouping key and is emitted. It is not used
   in the join predicate, so the source SQL deliberately associates dependency
   rows by `stay_id`, not by a second subject check.
3. **`ie.intime`** controls both temporal boundaries. Any change changes the
   set of dependency charttime rows and therefore every affected aggregate.
4. **`ce.stay_id`** controls whether a dependency row belongs to the ICU stay.
5. **`ce.charttime`** controls whether each charttime-level dependency row is
   inside the closed six-hours-before through one-day-after window. It is also
   the grouping/time identity created by the dependency before this target's
   per-stay aggregation.
6. **The eight consumed dependency measures** (`heart_rate`, `sbp`, `dbp`,
   `mbp`, `resp_rate`, `temperature`, `spo2`, `glucose`) control the numerical
   values of their own `min`, `max`, and `mean` outputs, including whether an
   aggregate is NULL. Their upstream itemid and `valuenum` predicates are
   therefore semantically essential even though they are not repeated in the
   target SQL.
7. **Upstream `chartevents.itemid` and `valuenum`** determine which source
   observations feed each dependency measure and whether a value is accepted.
   The Fahrenheit/Celsius discriminator and conversion determine
   `temperature`; the three glucose itemids determine `glucose`.

No source field is used for a target window function, carry-forward, or
secondary grouping beyond the charttime-level grouping already performed by
`vitalsign`. No FHIR/resource identifier is parsed or inverted here; resource
and reference IDs remain opaque identities.

## Relevant MIMIC notes for the downstream handoff

- `MIMIC_NOTES.md` records that itemid-derived Observation codes preserve the
  source `itemid` verbatim and that ICU chartevents use the proprietary
  `mimic-chartevents-d-items` code system. This is relevant to probing the
  dependency's item streams; it is not a new code set.
- The notes identify ICU temperature as split between itemids `223761`
  (Fahrenheit) and `223762` (Celsius), with the same plausibility limits and
  conversion already present in `vitalsign.sql`.
- The notes identify blood glucose as the three ICU itemids `220621`, `225664`,
  and `226537`, matching the dependency SQL. They also identify additional
  non-blood glucose itemids that are not in this concept's code set.
- The notes document that chartevents effective times can be normalized by the
  upstream FHIR ETL through a timezone cast. Because this concept has a closed
  charttime window and per-stay `MIN`/`MAX`/`AVG`, the prober/implementer should
  check time-window membership and aggregate effects without attempting to
  invert a resource ID. This is a representational/data-behavior lead, not a
  change to the canonical source specification.
