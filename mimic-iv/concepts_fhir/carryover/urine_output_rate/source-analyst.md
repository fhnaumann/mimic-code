# Source analysis: `urine_output_rate`

## Scope and source records read

- Canonical SQL: `mimic-iv/concepts/measurement/urine_output_rate.sql`.
- DAG metadata: `mimic-iv/concept_dag/concept_dag.json`. The node is stem
  `urine_output_rate`, path `measurement/urine_output_rate.sql`, level 1,
  recorded SHA256
  `2a94ace1b31094d311b32ae3256eeba0ed6ff000fb57fe30b9917de89db5d7ff`, with
  dependencies `urine_output` and `weight_durations`, and dependent `sofa`.
- The dependency nodes are level 0 and are completed. Their canonical output
  shapes were checked in the dependency carryover analyses and the full oracle
  manifest. This consumer must preserve those dependency boundaries.
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` was read for dependency-view,
  comparison-key, required-resource-key, and representability rules.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` was read. Relevant provisional
  fragments read as leads, not as source-SQL changes, were
  `MIMIC_NOTES.d/urine_output.md`,
  `MIMIC_NOTES.d/first_day_urine_output.md`, and
  `MIMIC_NOTES.d/weight_durations.md`.
- The source DDL at
  `mimic-iv/buildmimic/postgres/create.sql:369-425` was checked for raw ICU
  column types. The full oracle manifest entry at
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json:3836-3902` records
  the target output types, comparison key, required FHIR resource-key columns,
  and row count.

## Query shape and table references

The query has three CTEs (`tm`, `uo_tm`, `ur_stg`) and a final `SELECT`. The
only physical schemas referenced directly are `mimiciv_icu` and
`mimiciv_derived`; no `mimiciv_hosp` table is referenced.

| SQL location | Clause | Schema/table or relation | Alias | Role |
|---|---|---|---|---|
| `tm:6-15` | `FROM` | `mimiciv_icu.icustays` | `ie` | ICU-stay spine; supplies `stay_id`, `intime`, and `outtime`. |
| `tm:10-14` | `INNER JOIN` | `mimiciv_icu.chartevents` | `ce` | Supplies the qualifying item `220045` chart times used to create the heart-rate time anchor. |
| `uo_tm:28-31` | `FROM` | CTE `tm` | `tm` | Supplies qualifying stays and `intime_hr`. |
| `uo_tm:29-30` | `INNER JOIN` | `mimiciv_derived.urine_output` | `uo` | Completed dependency supplying the already-filtered and grouped urine-output stream. |
| `ur_stg:74-82` | `FROM` | CTE `uo_tm` | `io` | Anchor row for each urine-output time. |
| `ur_stg:76-81` | `LEFT JOIN` | CTE `uo_tm` (self-join) | `iosum` | Matches preceding/equal urine-output rows within the canonical 23-hour interval. |
| final `:117-122` | `FROM` | CTE `ur_stg` | `ur` | Aggregated urine-output/rate staging rows. |
| final `:118-122` | `LEFT JOIN` | `mimiciv_derived.weight_durations` | `wd` | Completed dependency supplying the weight interval and denominator. |

The CTE self-references are not additional physical tables. The two
`mimiciv_derived` references are hard dependency boundaries, not invitations to
rebuild their source FHIR mappings in this concept.

## Columns and inferred types

### Raw physical and dependency columns referenced

The PostgreSQL DDL types are used for raw ICU fields; the dependency output
types are the completed dependency/manifest types.

| Source/relation column | Inferred type | Uses in this SQL |
|---|---|---|
| `mimiciv_icu.icustays.stay_id` (`ie.stay_id`) | `INTEGER` | Join to `ce`, `GROUP BY` in `tm`, and `tm.stay_id`. |
| `mimiciv_icu.icustays.intime` | `TIMESTAMP`, nullable in the DDL | Lower bound of the one-month-expanded heart-rate window. |
| `mimiciv_icu.icustays.outtime` | `TIMESTAMP`, nullable in the DDL | Upper bound of that expanded window. |
| `mimiciv_icu.chartevents.stay_id` (`ce.stay_id`) | `INTEGER` | Inner-join key to `ie`. |
| `mimiciv_icu.chartevents.charttime` | `TIMESTAMP` | Heart-rate anchor `MIN`/`MAX` and the two time-window predicates. |
| `mimiciv_icu.chartevents.itemid` | `INTEGER` | Exact coded inclusion filter `220045`. No chart-event value column is read. |
| `urine_output.stay_id` (`uo.stay_id`) | `INTEGER` | Inner join to `tm`, partitioning, and output/grouping identity. |
| `urine_output.charttime` (`uo.charttime`) | `TIMESTAMP` | `LAG` ordering, self-join window bounds, `DATETIME_DIFF`, and final output key. |
| `urine_output.urineoutput` (`uo.urineoutput`) | `DOUBLE` | Per-measurement urine volume used by all urine-volume sums. |
| `weight_durations.stay_id` (`wd.stay_id`) | `INTEGER` | Weight-interval join key. |
| `weight_durations.starttime` (`wd.starttime`) | `TIMESTAMP` | Strict lower bound of the weight interval join. |
| `weight_durations.endtime` (`wd.endtime`) | `TIMESTAMP` | Inclusive upper bound of the weight interval join. |
| `weight_durations.weight` (`wd.weight`) | `DECIMAL(38,3)` | Positive-weight join predicate, final `weight` output, and rate denominator. |

`weight_durations.weight_type` exists in the dependency output but is not read
by this consumer. No source `subject_id`, `hadm_id`, `value`, `valuenum`,
`valueuom`, `storetime`, or heart-rate numeric value is referenced.

### CTE columns

`tm`:

- `stay_id`: `INTEGER`, `ie.stay_id`, grouped by stay.
- `intime_hr`: timestamp/datetime, `MIN(ce.charttime)` for the qualifying
  heart-rate rows. It is consumed as the first-row baseline in `uo_tm`.
- `outtime_hr`: timestamp/datetime, `MAX(ce.charttime)`. It is selected by the
  canonical SQL but is not referenced by any later CTE or final output; it is a
  dead intermediate column after `tm`.

`uo_tm`:

- `stay_id`: `INTEGER`, from `tm`.
- `tm_since_last_uo`: integer/bigint minute count from `DATETIME_DIFF`. For the
  first row in a stay it is `charttime - intime_hr` in minutes; otherwise it is
  the difference from the previous `charttime` in the window.
- `charttime`: timestamp/datetime, from the dependency `uo`.
- `urineoutput`: `DOUBLE`, from the dependency `uo`.

`ur_stg` (one grouped staging row per `io.stay_id, io.charttime` in the
canonical result):

- `stay_id`: `INTEGER`.
- `charttime`: `TIMESTAMP`.
- `uo`: `DOUBLE`, `SUM(DISTINCT io.urineoutput)`.
- `urineoutput_6hr`, `urineoutput_12hr`, `urineoutput_24hr`: floating-point
  aggregate outputs, `DOUBLE` in the target manifest.
- `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr`: numeric/decimal time totals. Each
  sums minute gaps, divides by `60.0`, casts to `NUMERIC`, and rounds to six
  decimal places in this CTE. The final output rounds each again to two
  decimal places.

### Final output columns and exact manifest types

The final output has 13 columns, in this order:

| Output column | Manifest type | Expression/role |
|---|---|---|
| `stay_id` | `INTEGER` | `ur.stay_id`. |
| `charttime` | `TIMESTAMP` | `ur.charttime`; output temporal identity. |
| `weight` | `DECIMAL(38,3)` | `wd.weight`; NULL when the left join finds no positive covering interval. |
| `uo` | `DOUBLE` | Current-row `SUM(DISTINCT io.urineoutput)` staging value. |
| `urineoutput_6hr` | `DOUBLE` | Conditional preceding urine-volume sum. |
| `urineoutput_12hr` | `DOUBLE` | Conditional preceding urine-volume sum. |
| `urineoutput_24hr` | `DOUBLE` | Sum of all rows admitted by the 24-hour self-join. |
| `uo_mlkghr_6hr` | `DECIMAL(38,4)` | NULL unless `uo_tm_6hr >= 6`; otherwise rounded `urineoutput_6hr / weight / uo_tm_6hr`. |
| `uo_mlkghr_12hr` | `DECIMAL(38,4)` | NULL unless `uo_tm_12hr >= 12`; otherwise rounded `urineoutput_12hr / weight / uo_tm_12hr`. |
| `uo_mlkghr_24hr` | `DECIMAL(38,4)` | NULL unless `uo_tm_24hr >= 24`; otherwise rounded `urineoutput_24hr / weight / uo_tm_24hr`. |
| `uo_tm_6hr` | `DECIMAL(38,2)` | `uo_tm_6hr` cast to `NUMERIC`, then rounded to two decimals. |
| `uo_tm_12hr` | `DECIMAL(38,2)` | `uo_tm_12hr` cast to `NUMERIC`, then rounded to two decimals. |
| `uo_tm_24hr` | `DECIMAL(38,2)` | `uo_tm_24hr` cast to `NUMERIC`, then rounded to two decimals. |

The manifest records comparison `key = (stay_id, charttime)`,
`key_columns = (icu_encounter_key, patient_key)`, and 3,321,747 oracle rows.
The two `key_columns` are required candidate-side opaque FHIR resource keys
under the loop contract; they are not columns selected by the canonical oracle
SQL and are not part of the source natural grain.

## Filters, predicates, and literal code specification

There is no `WHERE` clause in this SQL. All row-selection predicates occur in
`ON` clauses or in the conditional aggregations.

### Heart-rate eligibility in `tm`

The `INNER JOIN` condition is:

```sql
ON ie.stay_id = ce.stay_id
    AND ce.itemid = 220045
    AND ce.charttime > DATETIME_SUB(ie.intime, INTERVAL '1' MONTH)
    AND ce.charttime < DATETIME_ADD(ie.outtime, INTERVAL '1' MONTH)
```

The time bounds are strict (`>` and `<`). A stay has a `tm` row only if at
least one chart event with item `220045` falls in that expanded interval. The
query does not use the heart-rate value itself.

### Urine-output and 24-hour self-join predicates

The `tm`/`urine_output` inner join is exactly `tm.stay_id = uo.stay_id`; it has
no additional urine-time or volume predicate.

The `ur_stg` left self-join is exactly:

```sql
ON io.stay_id = iosum.stay_id
    AND io.charttime >= iosum.charttime
    AND io.charttime <= DATETIME_ADD(iosum.charttime, INTERVAL '23' HOUR)
```

Thus `iosum` supplies the same or earlier measurement, with an inclusive
23-hour offset from `iosum.charttime` to `io.charttime` (the canonical comment
describes this as the preceding 24-hour period). The six-hour conditional sums
retain rows where `DATETIME_DIFF(io.charttime, iosum.charttime, HOUR) <= 5`;
the 12-hour conditional sums use `<= 11`. There is no explicit lower bound in
those conditional expressions beyond the self-join's preceding-time predicate.
The `ELSE NULL` branches are part of the aggregate behavior.

### Weight interval predicates

The final left join is:

```sql
ON ur.stay_id = wd.stay_id
    AND ur.charttime > wd.starttime
    AND ur.charttime <= wd.endtime
    AND wd.weight > 0
```

The interval lower bound is strict and the upper bound inclusive. Because this
is a `LEFT JOIN`, a missing, non-positive, or non-covering weight does not
remove the `ur_stg` row; it leaves `weight` and the rate CASE expressions NULL.
The SQL has no final `WHERE` to remove those rows.

### Verbatim literal code set

The target SQL has exactly one coded filter, on the raw ICU chartevents table:

| Exact literal as named by SQL | Source table and field | Feeds |
|---|---|---|
| `220045` | `mimiciv_icu.chartevents.itemid` | `tm` row inclusion; `tm.intime_hr`/`tm.outtime_hr`; existence of a qualifying `tm` row; consequently every `uo_tm`, `ur_stg`, and final output row for that stay. |

The relevant SQL literal is `ce.itemid = 220045`. There are no ICD codes,
other itemid literals, code exclusions, or dead coded filters in
`urine_output_rate.sql`. The itemid's FHIR-side coding-system lead in the
read-only notes is the proprietary chartevents system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`; the
canonical SQL itself names only the numeric `itemid`, not a URI. The itemid
sets used internally by `urine_output` and `weight_durations` are dependency
implementation details and are not filters to duplicate in this consumer.

## Joins and dependency boundary

1. **INNER JOIN** `mimiciv_icu.icustays ie` to
   `mimiciv_icu.chartevents ce` on matching `stay_id`, exact item `220045`,
   and the strict one-month-expanded `intime`/`outtime` chart-time window.
2. **INNER JOIN** `tm` to the completed derived dependency
   `mimiciv_derived.urine_output uo` on `tm.stay_id = uo.stay_id`.
3. **LEFT self-join** `uo_tm io` to `uo_tm iosum` on matching stay and the
   inclusive preceding/equal 23-hour interval described above.
4. **LEFT JOIN** `ur_stg ur` to the completed derived dependency
   `mimiciv_derived.weight_durations wd` on matching stay, strict/inclusive
   weight interval containment, and `wd.weight > 0`.

The target candidate must consume the completed dependency views under their
unqualified stems, `urine_output` and `weight_durations`, after preprocessing.
It must not inline or rederive either dependency from FHIR resources.

### Exact dependency columns consumed

From `urine_output`:

- `stay_id`: inner-join key to the heart-rate-qualified `tm` stays and the
  partition/grouping identity.
- `charttime`: `LAG` ordering, the 23-hour self-join, six-/12-hour
  `DATETIME_DIFF` cutoffs, and final `charttime` output/key.
- `urineoutput`: current-row `uo` aggregate and all 6-/12-/24-hour volume
  aggregates.

The completed dependency output is `stay_id INTEGER`, `charttime TIMESTAMP`,
`urineoutput DOUBLE`. Its itemid filters and GU-irrigant sign transformation
are not repeated here.

From `weight_durations`:

- `stay_id`: final left-join key.
- `starttime`: strict lower interval bound.
- `endtime`: inclusive upper interval bound.
- `weight`: `> 0` join predicate, final output, and all three rate
  denominators.

The completed dependency also exposes `weight_type VARCHAR`, but this consumer
does not read it. Its dependency output types are `stay_id INTEGER`,
`starttime TIMESTAMP`, `endtime TIMESTAMP`, `weight DECIMAL(38,3)`, and
`weight_type VARCHAR`.

## Aggregations, windows, and time arithmetic

### Aggregations

- `tm`: `MIN(ce.charttime)` as `intime_hr` and `MAX(ce.charttime)` as
  `outtime_hr`, grouped by `ie.stay_id`.
- `ur_stg`: grouped by `io.stay_id, io.charttime` and computes:
  - `SUM(DISTINCT io.urineoutput)` as `uo` (the `DISTINCT` is canonical and
    must not be removed);
  - conditional `SUM` of `iosum.urineoutput` for the `<= 5` hour and
    `<= 11` hour windows;
  - conditional `SUM` of `iosum.tm_since_last_uo` for the same two windows,
    divided by `60.0`, cast to `NUMERIC`, and rounded to six places;
  - unconditional `SUM(iosum.urineoutput)` and `SUM(iosum.tm_since_last_uo)`
    for the 24-hour staging values, with the latter divided by `60.0`, cast to
    `NUMERIC`, and rounded to six places.
- There is no final `GROUP BY`; the final left join can theoretically fan out
  if overlapping dependency weight intervals cover one urine row. The full
  oracle manifest nevertheless identifies `(stay_id, charttime)` as the
  empirically unique target comparison key.

### Window function

`uo_tm` defines:

```sql
LAG(charttime) OVER (PARTITION BY tm.stay_id ORDER BY charttime)
```

For the first ordered urine row in each stay, the lag is NULL and the query
uses `DATETIME_DIFF(charttime, intime_hr, MINUTE)`. For later rows it uses the
difference from the lagged urine `charttime`. The order has no explicit
tie-breaker; the dependency's grouped output is intended to provide one row per
`(stay_id, charttime)`.

### Time arithmetic and rounding

- Heart-rate eligibility: `ie.intime - 1 MONTH` and `ie.outtime + 1 MONTH`,
  with strict comparisons.
- First urine elapsed time: `DATETIME_DIFF(charttime, intime_hr, MINUTE)`.
- Later urine elapsed time: `DATETIME_DIFF(charttime, LAG(charttime), MINUTE)`.
- Self-join lookback: `iosum.charttime + 23 HOUR`, inclusive at both the
  matching and upper-bound comparisons.
- Short-window tests use `DATETIME_DIFF(..., HOUR) <= 5` and `<= 11`; these are
  hour-unit differences exactly as written, not minute comparisons.
- Staging elapsed times divide summed minutes by `60.0` and round to six
  numeric places; final elapsed-time columns round to two places.
- Each rate CASE requires at least 6, 12, or 24 elapsed hours respectively and
  rounds the numeric mL/kg/hour expression to four places. A false threshold
  yields implicit NULL.
- No time arithmetic is performed in the final join itself; it compares the
  output chart time to dependency interval endpoints.

## Natural grain and key

The intended semantic grain is one urine-output-rate row per ICU `stay_id` and
urine-output `charttime`, after the heart-rate-qualified stay gate, the
preceding-measurement aggregates, and the covering weight lookup. The full
manifest confirms `(stay_id, charttime)` as the empirical keyed comparison key.

The SQL does not carry an output-event identifier. The dependency
`urine_output` has already grouped source output events at `(stay_id,
charttime)`, and this query groups its self-join at that same pair. The final
weight join has no post-join deduplication, so overlapping
`weight_durations` intervals would change multiplicity; the canonical full
result is the reference behavior, not a license to add a tie-breaker or
deduplicate. `icu_encounter_key` and `patient_key` are required opaque FHIR
resource-key columns for the candidate contract, but are auxiliary comparison
metadata rather than the oracle's clinical/source key.

## Semantically essential inputs

These are the source or dependency fields whose values can change inclusion,
identity, grouping, temporal ordering/carry-forward, or a meaningful derived
output:

1. **`ie.stay_id` and `ce.stay_id`** — control the initial inner join, the
   qualifying stay population, and all downstream stay partitions and output
   identity.
2. **`ce.itemid`** — exact `220045` controls whether a chart row can create a
   `tm` row. It consequently controls whether all urine rows for that stay can
   enter the result. No `ce` numeric value is used.
3. **`ie.intime` and `ie.outtime`** — control the strict one-month-expanded
   heart-rate eligibility window. If either endpoint is unavailable or changed,
   a stay can gain or lose its `tm` row and its `intime_hr` baseline.
4. **`ce.charttime`** — controls `tm.intime_hr` and `tm.outtime_hr`; the former
   controls the first urine elapsed-time value and can therefore affect all
   elapsed-time/rate outputs for the stay. `outtime_hr` itself is not consumed
   after `tm`.
5. **Dependency `urine_output.stay_id`** — controls the inner dependency join
   and output stay identity.
6. **Dependency `urine_output.charttime`** — controls each output row's key,
   `LAG` ordering, elapsed intervals, 6-/12-/24-hour lookback membership, and
   the self-join grouping.
7. **Dependency `urine_output.urineoutput`** — controls `uo`, all three
   volume-window sums, and all three rate numerators. It must be consumed as
   supplied, including its upstream item filter, GU-irrigant sign branch, and
   `(stay_id, charttime)` aggregation.
8. **Dependency `weight_durations.stay_id`** — controls which weight intervals
   are eligible for a urine row.
9. **Dependency `weight_durations.starttime` and `endtime`** — control whether
   the strict/inclusive interval join finds a weight, which can change output
   `weight` and whether each rate is NULL or calculated.
10. **Dependency `weight_durations.weight`** — controls the `> 0` join
    predicate, the final weight column, and all three rate denominators. A
    missing covering interval preserves the urine row but makes weight/rates
    NULL because the join is left-sided.
11. **`tm.intime_hr` and `uo_tm.tm_since_last_uo`** — derived temporal inputs
    controlling the elapsed-time sums and all three rate threshold branches.
12. **The `io`/`iosum` temporal self-join and its aggregation** — controls which
    preceding measurements contribute to each 6-, 12-, and 24-hour value. The
    `SUM(DISTINCT io.urineoutput)` semantics and the `ELSE NULL` aggregate
    branches are part of the output behavior.

## MIMIC-on-FHIR representability risks

These are source-side risks for a faithful port, not a terminal equivalence
decision.

- The direct heart-rate gate depends on the exact chartevents item discriminator
  `220045`, its ICU-stay association, and its effective chart time. The notes
  state that itemid-derived Observation codes are verbatim and that chartevents
  use the proprietary chartevents coding system, but the port must retain the
  exact code rather than use a label or profile. Loss of this code or of the
  associated stay can remove the entire stay from the result.
- The two dependency streams must remain dependency views. In particular, the
  target must not reconstruct outputevents item filters, GU-irrigant sign logic,
  weight-event filters, interval construction, or synthetic backfill. It reads
  only the six exact dependency columns documented above. Any accepted
  divergence in a completed dependency is inherited by this consumer and must
  not be misdescribed as a new source mapping.
- `charttime` is not ancillary: it is an output key, a grouping field, a window
  order, and a lookback-join boundary. The shared notes and the urine-output
  fragment document irreversible spring-forward DST normalization in the
  outputevents Observation effective time; the weight fragment documents the
  same class of risk for chartevents and ICU Encounter endpoints. A shifted
  outputevents time can alter the already-completed `urine_output` rows and
  therefore this concept's row keys, windows, sums, and rates. A shifted
  heart-rate time can alter `intime_hr` or the one-month boundary. A shifted ICU
  period endpoint can alter the dependency-produced weight intervals. These
  are timing risks that can reach inclusion, grain, and clinically meaningful
  rates, not merely an ancillary display discrepancy.
- The read fragment gives concrete bounds for those leads: completed
  `urine_output` attempt 0002 attributed 393 shifted keys and 232 aggregation
  conflicts with zero residual, and the judge accepted that outputevents
  divergence at 0.0118% of oracle rows. The `first_day_urine_output` fragment
  independently records outputevents as dateTime-only and found 334 demo target
  rows in the 02:xx hour but no changed demo key. The `weight_durations`
  fragment records 9 full-data ICU-`intime` shifts that remained as derived
  `starttime` conflicts after the dependency's two-hour arithmetic, plus the
  global chartevents omission predicates; those facts are inherited-dependency
  context, not reasons to rebuild either dependency here.
- FHIR dateTime values carry offsets. The shared notes require preserving the
  MIMIC wall-clock value with a `TIMESTAMP_NTZ`-style cast rather than converting
  the instant through the runner's session timezone. The original pre-ETL
  spring-forward 02:xx wall time is not recoverable from the served value, and
  opaque resource/reference ids must not be parsed or regenerated to recover it.
- The final weight join is interval-sensitive and has strict/inclusive
  boundary asymmetry. An endpoint shift or omitted dependency interval can turn
  a calculated rate into NULL, select a different weight, or create/delete a
  matching interval. No post-join deduplication is present to hide such a
  change.
- The source SQL does not filter urine output by ICU `intime`/`outtime`; it
  obtains only the heart-rate-qualified stay set and then joins dependency
  urine rows by `stay_id`. Adding an intuitive ICU-time filter would change the
  canonical behavior.
- No typed-NULL declaration is implied by this source analysis. The core
  temporal fields, dependency volume, and dependency weight/interval fields
  drive keys, inclusion, windows, or rates; substituting estimates for missing
  values would not be an exact source mapping. Any final representability
  ruling belongs to the comparator/equivalence judge under the loop contract.

## Summary

`urine_output_rate` is a level-1 measurement concept with direct ICU
`icustays`/`chartevents` references and two completed derived dependencies. It
keeps stays having chartevent item `220045` within a strict one-month-expanded
ICU window, computes elapsed time from the earliest qualifying chart time and
successive dependency urine measurements, aggregates 6/12/24-hour windows,
and left-joins positive weight intervals to produce 13 typed columns at the
empirical `(stay_id, charttime)` grain. The key risks are exact item/time
survival and inherited dependency timing/interval transformations; neither
dependency may be rederived or inlined.
