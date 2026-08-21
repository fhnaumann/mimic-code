# Source analysis: `kdigo_uo`

## Scope and source verification

- Concept stem: `kdigo_uo`.
- Canonical SQL: `mimic-iv/concepts/organfailure/kdigo_uo.sql`.
- DAG node: `organfailure/kdigo_uo.sql`, level 1.
- DAG SHA256: `7b4e012a2dc3c1c50f080372edc003aec5f7d3388a3a4d788d4b3cd89c71d2d2`.
  The file hash was checked and the DAG check reported that the stored JSON and
  Markdown artifacts match the source.
- DAG dependencies: `urine_output`, `weight_durations`.
- DAG dependent: `kdigo_stages`.

The source SQL has two CTEs, `uo_stg1` and `uo_stg2`, followed by the final
select. The analysis below describes only the target SQL's direct relational
references. The dependency SQL was also read to document the dependency output
contract and to preserve its literal code sets without suggesting that the
`kdigo_uo` port rederive either dependency.

## Direct table references and joins

| SQL location | Type | Fully qualified table / CTE | Columns used by `kdigo_uo` |
|---|---|---|---|
| `uo_stg1` `FROM` | raw ICU table | `mimiciv_icu.icustays` (source is written as `physionet-data.mimiciv_icu.icustays`) | `stay_id`, `intime` |
| `uo_stg1` `INNER JOIN` | completed derived dependency | `mimiciv_derived.urine_output` (source is written as `physionet-data.mimiciv_derived.urine_output`) | `stay_id`, `charttime`, `urineoutput` |
| final select `LEFT JOIN` | completed derived dependency | `mimiciv_derived.weight_durations` (source is written as `physionet-data.mimiciv_derived.weight_durations`) | `stay_id`, `starttime`, `endtime`, `weight` |

There are no `mimiciv_hosp` tables in this SQL. `uo_stg1` joins
`icustays` to `urine_output` with an **INNER JOIN**:

```sql
ie.stay_id = uo.stay_id
```

The final query joins `uo_stg2 AS ur` to `weight_durations AS wd` with a
**LEFT JOIN**:

```sql
ur.stay_id = wd.stay_id
AND ur.charttime >= wd.starttime
AND ur.charttime < wd.endtime
```

The interval is half-open: `[starttime, endtime)`. The left join preserves a
urine-output row when no weight interval matches; `weight` and the rates that
divide by it then become NULL. The SQL has no deduplication or tie-breaking if
more than one weight interval satisfies the predicate, so its intended one-row
per-urine-time grain relies on the dependency's intervals not overlapping for a
stay.

For dependency execution, the candidate-side preprocessing exposes completed
dependency outputs under the unqualified stems `urine_output` and
`weight_durations`. The consumer must use those dependency tables and not
recreate them from raw FHIR resources.

### Dependency internals (context only, not direct `kdigo_uo` references)

The dependency SQLs show why the columns above have their meanings:

- `urine_output` is built from `mimiciv_icu.outputevents`, grouped by
  `(stay_id, charttime)`, and emits `(stay_id, charttime, urineoutput)`.
- `weight_durations` is built from `mimiciv_icu.chartevents` plus an INNER JOIN
  to `mimiciv_icu.icustays`, and emits interval rows
  `(stay_id, starttime, endtime, weight, weight_type)`.

Those raw dependency tables are not additional direct `FROM`/`JOIN` clauses in
`kdigo_uo.sql`.

## Column inventory and inferred types

The oracle manifest was checked for the final schema. It records the final
natural key `(stay_id, charttime)`, keyed comparison, and 3,321,748 oracle
rows. Types below use the manifest where available and the SQL expression type
where the column is intermediate.

### `uo_stg1`

| Column / expression | Origin or operation | Inferred type | Role |
|---|---|---|---|
| `stay_id` | `ie.stay_id` | `INTEGER` | ICU-stay identity; partition and final key |
| `charttime` | `uo.charttime` | `TIMESTAMP` | urine-output observation time; ordering, windows, final key |
| `seconds_since_admit` | `CAST(DATETIME_DIFF(charttime, intime, SECOND) AS INTEGER)` | `INTEGER` | numeric time axis for all `RANGE` windows |
| `hours_since_previous_row` | `COALESCE(DATETIME_DIFF(charttime, LAG(charttime) OVER (...), SECOND) / 3600.0, 1)` | `DOUBLE`/floating numeric | per-row documented-duration contribution to each window |
| `urineoutput` | `uo.urineoutput` | `DOUBLE` | urine volume contribution to sums and rates |
| `ie.intime` | `icustays.intime`, referenced in the expression but not selected | `TIMESTAMP` | admission anchor for `seconds_since_admit` |
| `LAG(charttime)` | prior `uo.charttime` within the stay ordered by `charttime` | nullable `TIMESTAMP` | computes the previous-row interval; first row is NULL before `COALESCE` |

The `LAG` window is `PARTITION BY ie.stay_id ORDER BY charttime`. There is no
additional tie-breaker in that window. The dependency's `(stay_id, charttime)`
grouping normally supplies one row per time.

### `uo_stg2`

The CTE retains `stay_id`, `charttime`, `hours_since_previous_row`, and
`urineoutput`, and uses `seconds_since_admit` from `uo_stg1` in every window
`ORDER BY`. It adds:

| Column / expression | Operation | Inferred type |
|---|---|---|
| `urineoutput_6hr` | `SUM(urineoutput)` over a 21,600-second `RANGE` | `DOUBLE` |
| `urineoutput_12hr` | `SUM(urineoutput)` over a 43,200-second `RANGE` | `DOUBLE` |
| `urineoutput_24hr` | `SUM(urineoutput)` over an 86,400-second `RANGE` | `DOUBLE` |
| `uo_tm_6hr` | `ROUND(CAST(SUM(hours_since_previous_row) AS NUMERIC), 6)` over a 21,600-second `RANGE` | `DECIMAL/NUMERIC`, final `DECIMAL(38,6)` |
| `uo_tm_12hr` | same duration sum over a 43,200-second `RANGE` | `DECIMAL/NUMERIC`, final `DECIMAL(38,6)` |
| `uo_tm_24hr` | same duration sum over an 86,400-second `RANGE` | `DECIMAL/NUMERIC`, final `DECIMAL(38,6)` |

### Final output columns

The final output order and oracle types are:

| Output column | Expression / source | Type |
|---|---|---|
| `stay_id` | `ur.stay_id` | `INTEGER` |
| `charttime` | `ur.charttime` | `TIMESTAMP` |
| `weight` | `wd.weight` | `DECIMAL(38,3)`, nullable because of the LEFT JOIN |
| `urineoutput_6hr` | `ur.urineoutput_6hr` | `DOUBLE` |
| `urineoutput_12hr` | `ur.urineoutput_12hr` | `DOUBLE` |
| `urineoutput_24hr` | `ur.urineoutput_24hr` | `DOUBLE` |
| `uo_rt_6hr` | gated and rounded `ur.urineoutput_6hr / wd.weight / uo_tm_6hr` | `DECIMAL(38,4)`, nullable |
| `uo_rt_12hr` | gated and rounded `ur.urineoutput_12hr / wd.weight / uo_tm_12hr` | `DECIMAL(38,4)`, nullable |
| `uo_rt_24hr` | gated and rounded `ur.urineoutput_24hr / wd.weight / uo_tm_24hr` | `DECIMAL(38,4)`, nullable |
| `uo_tm_6hr` | `ur.uo_tm_6hr` | `DECIMAL(38,6)` |
| `uo_tm_12hr` | `ur.uo_tm_12hr` | `DECIMAL(38,6)` |
| `uo_tm_24hr` | `ur.uo_tm_24hr` | `DECIMAL(38,6)` |

The canonical oracle contains no FHIR resource-key columns. The loop's oracle
manifest separately declares candidate-side key outputs
`icu_encounter_key` and `patient_key`; these are required for downstream
SQL-on-FHIR joins and are not source values selected by this canonical SQL.

## Filters and value conditions

### Direct `kdigo_uo` filters

There are **no `WHERE` clauses** in `kdigo_uo.sql`, and therefore no direct
itemid, ICD, time-window, code-exclusion, or value-range row filters. The INNER
JOIN to `icustays` is the only direct row-preserving condition before the final
LEFT JOIN. In particular, the SQL does not filter `seconds_since_admit` to a
positive or admission-bounded range.

The final rate expressions have value gates, but these are CASE output
conditions, not row filters:

- `uo_rt_6hr` is calculated only when `uo_tm_6hr >= 6 AND uo_tm_6hr < 12`; otherwise it is NULL.
- `uo_rt_12hr` is calculated only when `uo_tm_12hr >= 12`; otherwise it is NULL.
- `uo_rt_24hr` is calculated only when `uo_tm_24hr >= 24`; otherwise it is NULL.

No explicit nonzero/non-null `weight` predicate exists. A missing or unusable
weight therefore does not remove the urine-output row through the LEFT JOIN;
it makes the corresponding division result NULL (subject to the execution
engine's normal arithmetic behavior).

### Literal code set

The direct `kdigo_uo.sql` source names **no coded literal at all**: it has no
`itemid`, `icd_code`, code-system, or other coded filter. There is consequently
no direct `kdigo_uo` code set to translate or expand.

For dependency provenance only, the source SQL of `urine_output` (which must be
consumed as a completed dependency) contains this exact `itemid` set on
`mimiciv_icu.outputevents`; the set feeds the dependency's `urineoutput` column,
not a raw-table filter that should be duplicated in `kdigo_uo`:

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

The same dependency has the exact value discriminator
`oe.itemid = 227488 AND oe.value > 0`, which maps that positive GU-irrigant-in
volume to `-1 * oe.value`; other selected itemids retain `oe.value`. This is a
dependency-owned transformation feeding `urineoutput`.

The source SQL of `weight_durations` (also a completed dependency) contains this
exact `itemid` set on `mimiciv_icu.chartevents`:

```sql
            226512 -- Admit Wt
            , 224639 -- Daily Weight
```

`226512` feeds the dependency's `weight_type = 'admit'` branch; `224639` feeds
the `ELSE 'daily'` branch. Both feed its rounded `weight`, and its temporal
interval columns. Its non-coded value predicates are
`c.valuenum IS NOT NULL`, `c.valuenum > 0`, and `c.valuenum < 1500`.
These dependency-owned filters are recorded verbatim for traceability; the
`kdigo_uo` consumer reads only `weight_durations` output columns.

No explicit coding-system URI is named in any of these canonical SQL files.
The coded fields are proprietary ICU `itemid` values in the dependency source.

## Joins, row grain, and natural key

The intended target row is one urine-output observation time for one ICU stay:

```text
(stay_id, charttime)
```

This is also the natural/comparison key recorded in the full oracle manifest.
The dependency `urine_output` creates this grain by `GROUP BY stay_id,
charttime`; `uo_stg1` preserves it through the one-to-one expected
`icustays.stay_id` lookup; `uo_stg2` preserves it while adding window values;
and the final interval join is expected to select one weight interval. If the
weight dependency supplied overlapping matching intervals, the literal LEFT
JOIN would fan out the row rather than resolve the overlap.

The final candidate additionally needs the manifest's
`icu_encounter_key` and `patient_key` resource identities, but those are
comparison/consumer keys and not part of the canonical oracle row key.

## Window functions and aggregations

There is no `GROUP BY`, `DISTINCT`, ordinary aggregate query, `MIN`, `MAX`,
`AVG`, or `ARRAY_AGG` in `kdigo_uo.sql` itself. It uses:

1. `LAG(charttime) OVER (PARTITION BY ie.stay_id ORDER BY charttime)` in
   `uo_stg1`.
2. Three `SUM(urineoutput) OVER (...)` windows in `uo_stg2`.
3. Three `SUM(hours_since_previous_row) OVER (...)` windows in `uo_stg2`, each
   cast to NUMERIC and rounded to six decimal places.

All six `SUM` windows partition by `stay_id`, order by integer
`seconds_since_admit`, and use an inclusive `RANGE BETWEEN N PRECEDING AND
CURRENT ROW`:

| Output family | Range in seconds | Nominal duration |
|---|---:|---:|
| `urineoutput_6hr`, `uo_tm_6hr` | `21600` | 6 hours |
| `urineoutput_12hr`, `uo_tm_12hr` | `43200` | 12 hours |
| `urineoutput_24hr`, `uo_tm_24hr` | `86400` | 24 hours |

Because the ordering expression is numeric, rows at the current timestamp and
the exact lower boundary are included. `RANGE` includes all rows in the
numeric time interval, rather than a fixed number of preceding rows.

## Temporal rules

1. `seconds_since_admit` is the integer difference between each urine-output
   `charttime` and that stay's `icustays.intime`, in seconds. It is the sole
   time axis used by the six rolling windows.
2. `hours_since_previous_row` is the elapsed hours from the prior charted
   urine-output row in the same stay. The first row has no prior row and is
   assigned exactly `1` by `COALESCE`, not an elapsed time from admission.
3. Each `uo_tm_Nhr` sums the per-row `hours_since_previous_row` values for rows
   whose `seconds_since_admit` fall in the corresponding inclusive numeric
   range. It is a documentation-duration sum, not a direct subtraction of the
   current time and the earliest time in the window, and it is not explicitly
   clamped to the nominal N-hour length.
4. The final weight is selected by a half-open temporal interval on the same
   stay: `starttime <= charttime < endtime`.
5. The rate formulas divide the rolling urine volume by the matched weight and
   by the duration sum, then round to four decimal places. The duration gates
   above decide whether each rate is a number or NULL.

## Semantically essential inputs and dependency tracing

These are inputs whose values can change inclusion, row identity, window
membership, temporal association, or a clinically meaningful derived output:

| Essential input | Controls | Branches / outputs affected |
|---|---|---|
| `icustays.stay_id` and `urine_output.stay_id` | INNER JOIN membership, stay partition, natural key | Every output row; all LAG/SUM windows; final weight join |
| `urine_output.charttime` | Row identity, LAG ordering, output key, numeric time position, final interval lookup | `seconds_since_admit`, `hours_since_previous_row`, all six rolling sums/time sums, `weight`, all rates, final `charttime` |
| `icustays.intime` | Admission-relative numeric time axis | `seconds_since_admit`, membership in every 6/12/24-hour RANGE, hence all rolling volumes, duration sums, gates, and rates |
| `urine_output.urineoutput` | Volume aggregation and numerator | `urineoutput_6hr`, `urineoutput_12hr`, `urineoutput_24hr`, and all three `uo_rt_*` values |
| Previous `charttime` within each stay | Per-row elapsed/documented-duration contribution | `hours_since_previous_row` and all `uo_tm_*` sums; therefore each rate's NULL/value gate and denominator |
| First-row condition per stay | Whether `LAG` is NULL and the default `1` is used | `hours_since_previous_row`, all `uo_tm_*`, and rate availability for windows containing that row |
| `weight_durations.stay_id`, `starttime`, `endtime` | Whether and which weight interval matches | `weight` and whether a row's rates have a usable denominator; overlapping matches can alter row multiplicity |
| `weight_durations.weight` | Rate denominator | `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr`; NULL weight propagates to the rate calculation |
| `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr` | CASE thresholds and rate denominators | Each corresponding `uo_rt_*` branch and output |
| Dependency-owned itemid/value logic | Which output events enter `urine_output` and the sign of GU-irrigant input | The consumed `urineoutput` stream and therefore every downstream window and rate |
| Dependency-owned weight itemids and value bounds | Which charted weights and intervals enter `weight_durations` | Matched `weight`, interval coverage, and all rate outputs |

No source discriminator is used to choose an alternative clinical stage or
diagnosis branch. The only target branches are the three duration-gated CASE
expressions, and the only target row-preserving filter is the INNER JOIN to
`icustays`.

## Files and notes read

- `mimic-iv/concepts/organfailure/kdigo_uo.sql` (canonical source).
- `mimic-iv/concept_dag/concept_dag.json` (path, hash, level, dependencies).
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` (dependency boundary, key/schema,
  essential-loss and comparison rules).
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` (shared FHIR/ETL and opaque-key rules).
- Relevant provisional fragments:
  `MIMIC_NOTES.d/urine_output.md`,
  `MIMIC_NOTES.d/weight_durations.md`, and
  `MIMIC_NOTES.d/first_day_urine_output.md`.
- Dependency canonical SQL:
  `mimic-iv/concepts/measurement/urine_output.sql` and
  `mimic-iv/concepts/demographics/weight_durations.sql`.
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for the final
  schema and empirical comparison key.

This is source-side description only. No ViewDefinition or candidate SQL was
authored.
