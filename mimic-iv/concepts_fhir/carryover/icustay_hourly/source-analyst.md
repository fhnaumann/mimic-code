# Source analysis: `icustay_hourly`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/demographics/icustay_hourly.sql`.
- The target SQL has one CTE (`all_hours`) and one final `SELECT`.
- DAG node: `icustay_hourly`, path `demographics/icustay_hourly.sql`, level
  1, SHA-256
  `6e20f8fba635f25708b29b48f926c4bd68da691bfae66a04fba394593c8c1f28`.
- DAG dependency: `icustay_times`. The dependency is a
  `mimiciv_derived` concept and must be available to candidate SQL as the
  unqualified table/view name `icustay_times`; do not rederive it from FHIR
  resources in this concept.
- DAG dependent: `sofa`.
- The full oracle manifest gives the target output schema as `stay_id`
  (`INTEGER`), `hr` (`BIGINT`), and `endtime` (`TIMESTAMP`), with natural
  comparison key `(stay_id, endtime)` and 7,799,814 rows in the full oracle.

## Table and relation references

Every `FROM`/`JOIN` relation in the target SQL is:

1. `FROM \`physionet-data.mimiciv_derived.icustay_times\` it`
   - MIMIC schema: `mimiciv_derived`.
   - Table/concept: `icustay_times`.
   - Consumer alias: `it`.
   - Used by CTE `all_hours`.
   - Exact dependency columns read: `it.stay_id`, `it.intime_hr`, and
     `it.outtime_hr`. The dependency's `subject_id` and `hadm_id` are not
     read by this consumer.

2. `FROM all_hours`
   - This is the CTE relation defined above, not a physical table and not a
     `mimiciv_derived` dependency.

3. `CROSS JOIN UNNEST(all_hours.hrs) AS hr_unnested`
   - This is not a physical MIMIC table and has no schema/table name.
   - It expands the integer array generated in `all_hours`; there is no `ON`
     condition.

There are no direct `mimiciv_hosp` or `mimiciv_icu` table references in
`icustay_hourly.sql`, and no physical-table INNER or LEFT join. The raw
heart-rate and ICU-stay tables are upstream of `icustay_times`, not direct
inputs to this SQL.

## CTE and column analysis

### CTE `all_hours`

The CTE is:

```sql
SELECT
    it.stay_id,
    CASE
        WHEN DATETIME_TRUNC(it.intime_hr, HOUR) = it.intime_hr
            THEN it.intime_hr
        ELSE DATETIME_ADD(
            DATETIME_TRUNC(it.intime_hr, HOUR), INTERVAL 1 HOUR
        )
    END AS endtime,
    GENERATE_ARRAY(
        -24,
        CAST(CEIL(DATETIME_DIFF(it.outtime_hr, it.intime_hr, HOUR)) AS INTEGER)
    ) AS hrs
FROM `physionet-data.mimiciv_derived.icustay_times` it
```

Referenced and produced columns/types:

- `it.stay_id`: dependency ICU-stay identifier, inferred `INTEGER`; carried
  into CTE column `all_hours.stay_id` unchanged.
- `it.intime_hr`: dependency temporal column, manifest type `TIMESTAMP`;
  it is used as the first observed heart-rate time. It controls the hour
  alignment and is also the start argument to `DATETIME_DIFF`.
- `DATETIME_TRUNC(it.intime_hr, HOUR)`: temporal value truncated to the
  beginning of its clock hour. The equality test detects an already aligned
  input.
- CTE `all_hours.endtime`: temporal datetime/timestamp value. It is exactly
  `it.intime_hr` when already on an hour boundary; otherwise it is the
  beginning of the input's hour plus one hour. This is a ceiling-to-hour
  operation, not a floor.
- `it.outtime_hr`: dependency temporal column, manifest type `TIMESTAMP`;
  it is used only as the end argument to `DATETIME_DIFF`. It is not selected
  directly into the target output.
- `DATETIME_DIFF(it.outtime_hr, it.intime_hr, HOUR)`: integral hour-difference
  expression in the source dialect. `CEIL(...)` is applied and the result is
  cast to `INTEGER` for the array's upper bound.
- `all_hours.hrs`: integer array, inferred `ARRAY<INT64>`/array of BIGINT
  values. `GENERATE_ARRAY` includes both endpoints: literal lower bound `-24`
  and the calculated upper bound.

The dependency's `icustay_times` output itself is one row per `stay_id`; its
two time columns are generated upstream as MIN/MAX heart-rate observation
times. Only the three dependency columns listed above are inputs to this
CTE.

### Final output

The final query is:

```sql
SELECT
    stay_id,
    CAST(hr_unnested AS INT64) AS hr,
    DATETIME_ADD(endtime, INTERVAL CAST(hr_unnested AS INT64) HOUR) AS endtime
FROM all_hours
CROSS JOIN UNNEST(all_hours.hrs) AS hr_unnested
```

- `stay_id`: `INTEGER`; inherited from `all_hours.stay_id`.
- `hr_unnested`: integer array element, inferred `INT64`; one value for each
  generated hour offset.
- `hr`: explicitly cast to `INT64` in the source SQL; the oracle manifest
  materializes this as `BIGINT`. It is the signed hour offset relative to the
  aligned first heart-rate time.
- `endtime`: temporal timestamp/datetime result of adding `hr_unnested`
  hours to the CTE's aligned `endtime`; the oracle manifest type is
  `TIMESTAMP`.
- `all_hours.hrs` is an intermediate array and is not a final output column.
- `subject_id`, `hadm_id`, ICU admission/discharge columns, and raw
  observation values are not final or intermediate columns in this target
  SQL.

## Filters and literal code specification

- There is no `WHERE` clause in `icustay_hourly.sql`.
- There is no `HAVING` clause, value constraint, itemid filter, ICD filter,
  code exclusion, or explicit time-window predicate.
- The row-generation bounds are inclusion logic rather than a `WHERE`
  predicate: `GENERATE_ARRAY(-24, calculated_upper_bound)` includes the
  offset range from 24 hours before the aligned first observation through the
  inclusive calculated upper bound.

The literal coded-filter set for this target SQL is therefore empty: the SQL
does not name an `itemid`, `icd_code`, `icd_version`, or other coded filter.

For transitive provenance only, the upstream canonical SQL for the required
dependency `icustay_times` filters source table
`mimiciv_icu.chartevents` with the exact literal `ce.itemid = 220045`.
That exact set is `{220045}` on `mimiciv_icu.chartevents.itemid` and feeds
the dependency columns `intime_hr` and `outtime_hr`, which in turn control
this target's `hrs` range and generated `endtime` values. It is not a filter
written by `icustay_hourly.sql` and must not be re-applied by rederiving the
dependency in this concept.

## Joins

The target has one relational expansion:

```sql
CROSS JOIN UNNEST(all_hours.hrs) AS hr_unnested
```

- Join type: `CROSS JOIN`/array expansion.
- Left input: each `all_hours` row.
- Right input: the array `all_hours.hrs` belonging to that row.
- Join condition: none; there is no `ON` clause.
- Effect: one output row per array element, retaining the source
  `stay_id` and pairing each element with its hour offset.

There is no target INNER JOIN or LEFT JOIN. The LEFT JOIN that creates
`icustay_times` is upstream and is not part of this SQL's executable join
graph.

## Aggregations, temporal logic, and grain

- `icustay_hourly.sql` has no `GROUP BY`, aggregate function, window function,
  `DISTINCT`, `HAVING`, or value aggregation. `CEIL`, `DATETIME_DIFF`,
  `DATETIME_TRUNC`, `DATETIME_ADD`, `CAST`, `GENERATE_ARRAY`, and `UNNEST`
  are scalar/array operations, not aggregation over hourly observations.
- The dependency's upstream MIN/MAX heart-rate aggregation is the source of
  `intime_hr` and `outtime_hr`; this target consumes those already-aggregated
  endpoints.
- For each dependency row, the first clock endpoint is
  `ceil_to_hour(intime_hr)`: an exact hour remains unchanged, and a
  non-boundary time advances to the next hour.
- The generated offsets are inclusive from `-24` through
  `CAST(CEIL(DATETIME_DIFF(outtime_hr, intime_hr, HOUR)) AS INTEGER)`.
- Each output endpoint is `aligned_intime_hr + hr hours`.
- The SQL comments say that downstream tables can use
  `(endtime - 1 hour, endtime]`; that is a comment describing a possible
  downstream interval join, not a predicate or join performed by this query.
- The executable bounds are based on first/last **heart-rate observation
  `charttime`** values carried by `icustay_times`, not on ICU Encounter
  periods, `icustays.intime`, or `icustays.outtime`. The target does not
  aggregate over FHIR ICU Encounter periods and does not directly read an
  Encounter or an observation resource; its temporal grid is observation-
  anchored through the derived dependency.
- Logical grain: one generated clock-hour row per dependency `stay_id` and
  integer `hr` offset. With the dependency's one-row-per-stay grain and
  one-hour increments, the source natural key is equivalently
  `(stay_id, hr)` or `(stay_id, endtime)`; the oracle manifest specifies
  `(stay_id, endtime)`.
- `hr` is a relative offset, not an absolute ICU hour number. `endtime` is
  the absolute temporal key used to identify the generated clock-hour row.

## Semantically essential inputs

The following values can change inclusion, row identity, timing, or a
clinically meaningful temporal output:

1. `icustay_times.stay_id`: preserves the ICU-stay identity and controls the
   output grouping/key. A different stay id changes every row's natural key.
2. `icustay_times.intime_hr`: controls the ceiling-to-hour anchor, every
   generated `endtime`, and the start of the upper-bound difference. It can
   change both row timestamps and the number/range of generated rows.
3. `icustay_times.outtime_hr`: controls the inclusive upper bound of the
   generated offset array and therefore row inclusion/count and the final
   endpoint. It is not emitted directly.
4. Presence/nullness of the dependency row and its two temporal values:
   `GENERATE_ARRAY` depends on both times, so an unavailable time endpoint
   prevents a valid hourly array from being produced rather than supplying a
   substitute ICU Encounter interval. This is row-inclusion-critical.
5. The literal `-24`, the `HOUR` granularity, inclusive array endpoints, and
   the ceiling rule are fixed source semantics that determine the temporal
   window and natural grain.
6. Transitive source discriminator: upstream
   `mimiciv_icu.chartevents.itemid = 220045` selects the heart-rate stream
   used to calculate `intime_hr`/`outtime_hr`. The exact dependency output,
   rather than a newly derived FHIR approximation, is the required input to
   this concept.

`subject_id` and `hadm_id` are present in the dependency output but are not
read here and do not affect target row inclusion, grouping, timing, or output
values.

## Relevant MIMIC-on-FHIR note and dataset-wide finding

The existing shared `mimic-iv/concepts_fhir/MIMIC_NOTES.md` datetime note is
relevant to any later FHIR mapping of the observation-derived temporal
inputs: FHIR datetimes carry offsets, and the note documents preserving the
de-identified wall-clock value with `TIMESTAMP_NTZ` plus the known upstream
New-York DST-gap normalization. That is existing shared knowledge, not a new
dataset-wide finding established by this source-only analysis. No new quirk
should be appended to `MIMIC_NOTES.d/icustay_hourly.md` on the basis of the
canonical SQL read alone.

## Summary

`icustay_hourly` is a dependent temporal-grid generator. It reads only
`stay_id`, `intime_hr`, and `outtime_hr` from the derived `icustay_times`
concept, ceilings the first heart-rate observation time to a clock hour,
generates inclusive offsets from -24 through the calculated last offset, and
emits `(stay_id, hr, endtime)` rows. Its time basis is the upstream
heart-rate observation stream, not ICU Encounter periods, and it has no
direct raw-table join, coded filter, or aggregation of its own.
