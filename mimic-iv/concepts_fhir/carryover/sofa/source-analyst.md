# Source analysis: `sofa`

## Scope and DAG position

- Source of truth: `mimic-iv/concepts/score/sofa.sql` (379 lines).
- The DAG node is `sofa`, path `score/sofa.sql`, level 2, with SHA256
  `a2dcdfa54c7d981c6846e9afdc8492656cfa8aa85137033becec8ac5dc8c1099`.
  The SHA256 was recomputed from the source file and matches the DAG.
- DAG dependencies, in the DAG order supplied for this concept, are:
  `bg`, `chemistry`, `complete_blood_count`, `dobutamine`, `dopamine`,
  `enzyme`, `epinephrine`, `gcs`, `icustay_hourly`, `norepinephrine`,
  `urine_output_rate`, `ventilation`, and `vitalsign`.
- `sofa` is a dependency of `sepsis3`.
- Every `mimiciv_derived` relation below is a completed dependency concept.
  Candidate SQL must reference the completed dependency temp view by its
  unqualified stem (`FROM bg`, `FROM chemistry`, etc.) after preprocessing;
  it must not rederive a dependency from FHIR resources or inline its source
  SQL. In particular, consume `icustay_hourly`, `urine_output_rate`, and
  `ventilation` directly rather than rederiving their own dependencies
  (`icustay_times`; `urine_output`/`weight_durations`; and
  `oxygen_delivery`/`ventilator_setting`, respectively).

## Overall operation, grain, and dialect

The query creates one candidate SOFA row for each ICU `stay_id` and each
nonnegative hourly index `hr` supplied by `icustay_hourly`. `co` uses the
hour's `(endtime - 1 hour, endtime]` interval. Hourly aggregates are computed
for the physiologic inputs, the six current-hour component scores are then
calculated, and a 24-row rolling maximum is taken separately for each
component. Missing current-hour component scores remain NULL in `scorecalc`,
but missing rolling maxima are imputed to integer zero in `score_final`.

The source uses BigQuery-style SQL: backtick-qualified project/schema/table
names, `DATETIME_SUB(..., INTERVAL '1' HOUR)`, and BigQuery `DATETIME` values.
The port's normalized oracle types for the datetime outputs are `TIMESTAMP`.
The FHIR-side datetime strings carry offsets but represent MIMIC wall-clock
values; when materializing dependency datetime columns for Spark, preserve
the wall clock with `CAST(... AS TIMESTAMP_NTZ)`, not an offset-converting
`TIMESTAMP` cast. All time comparisons below are exact comparisons of the
same wall-clock representation. The lower time bound is deliberately strict
and the upper bound inclusive.

The source SQL has no direct `mimiciv_hosp` table reference. Its only raw
table is `mimiciv_icu.icustays`; all other relations named by the SQL are
`mimiciv_derived` dependencies. The dependency concepts themselves may read
hospital or ICU raw tables, but those underlying tables are not direct SOFA
references and must not be rederived by the SOFA candidate.

## Direct table references and joins

The source uses the following relations. The listed join conditions are the
complete set of `FROM`/`JOIN` conditions in the file.

### `co` (lines 29--38)

- `mimiciv_derived.icustay_hourly ih` (`FROM`): `stay_id`, `hr`, and
  `endtime` are read.
- `mimiciv_icu.icustays ie` (`INNER JOIN`):
  `ih.stay_id = ie.stay_id`; `ie.hadm_id` is selected and `ie.stay_id` is
  also the join key.
- Derived column `starttime` is
  `DATETIME_SUB(ih.endtime, INTERVAL '1' HOUR)`. No `WHERE` is applied in
  this CTE.

### `pafi` (lines 40--64)

- `mimiciv_icu.icustays ie` (`FROM`): `ie.stay_id` and `ie.subject_id`.
- `mimiciv_derived.bg bg` (`INNER JOIN`):
  `ie.subject_id = bg.subject_id`. This is a subject-level join, not a
  `stay_id` or `hadm_id` join.
- `mimiciv_derived.ventilation vd` (`LEFT JOIN`):
  `ie.stay_id = vd.stay_id`
  `AND bg.charttime >= vd.starttime`
  `AND bg.charttime <= vd.endtime`
  `AND vd.ventilation_status = 'InvasiveVent'`.
  The status restriction is in the `ON` clause, so a blood gas with no
  matching invasive-ventilation interval remains in `pafi` with the
  non-ventilated branch.
- `WHERE specimen = 'ART.'`; the unqualified `specimen` resolves to
  `bg.specimen`.
- The CTE emits the non-ventilated ratio only when `vd.stay_id IS NULL` and
  the ventilated ratio only when `vd.stay_id IS NOT NULL`.

### Hourly input aggregates (lines 66--151)

Each CTE starts from `co` and uses a `LEFT JOIN`, preserving the hourly ICU
spine when no measurement is available:

- `vs`: `mimiciv_derived.vitalsign vs`, on
  `co.stay_id = vs.stay_id AND co.starttime < vs.charttime
  AND co.endtime >= vs.charttime`; groups by `co.stay_id, co.hr`.
- `gcs`: `mimiciv_derived.gcs gcs`, on
  `co.stay_id = gcs.stay_id AND co.starttime < gcs.charttime
  AND co.endtime >= gcs.charttime`; groups by `co.stay_id, co.hr`.
- `bili`: `mimiciv_derived.enzyme enz`, on
  `co.hadm_id = enz.hadm_id AND co.starttime < enz.charttime
  AND co.endtime >= enz.charttime`; groups by `co.stay_id, co.hr`.
- `cr`: `mimiciv_derived.chemistry chem`, on
  `co.hadm_id = chem.hadm_id AND co.starttime < chem.charttime
  AND co.endtime >= chem.charttime`; groups by `co.stay_id, co.hr`.
- `plt`: `mimiciv_derived.complete_blood_count cbc`, on
  `co.hadm_id = cbc.hadm_id AND co.starttime < cbc.charttime
  AND co.endtime >= cbc.charttime`; groups by `co.stay_id, co.hr`.
- `pf`: the intermediate `pafi` CTE, on
  `co.stay_id = pafi.stay_id AND co.starttime < pafi.charttime
  AND co.endtime >= pafi.charttime`; groups by `co.stay_id, co.hr`.
- `uo`: `mimiciv_derived.urine_output_rate uo`, on
  `co.stay_id = uo.stay_id AND co.starttime < uo.charttime
  AND co.endtime >= uo.charttime`; groups by `co.stay_id, co.hr`.

The aggregate expressions are respectively `MIN(vs.mbp)`, `MIN(gcs.gcs)`,
`MAX(enz.bilirubin_total)`, `MAX(chem.creatinine)`, `MIN(cbc.platelet)`,
`MIN(pafi.pao2fio2ratio_novent)`, `MIN(pafi.pao2fio2ratio_vent)`, and:

```sql
MAX(CASE WHEN uo.uo_tm_24hr >= 22 AND uo.uo_tm_24hr <= 30
         THEN uo.urineoutput_24hr / uo.uo_tm_24hr * 24 END)
```

Thus a urine row contributes only when its dependency-provided 24-hour
elapsed-time value is in the inclusive range `[22, 30]`, and the result is a
24-hour rate estimate rather than the raw `urineoutput_24hr`.

### `vaso` (lines 153--185)

`vaso` starts from `co` and uses four `LEFT JOIN`s, each with the same
end-aligned interval rule:

- `mimiciv_derived.epinephrine epi`: `co.stay_id = epi.stay_id
  AND co.endtime > epi.starttime AND co.endtime <= epi.endtime`.
- `mimiciv_derived.norepinephrine nor`: `co.stay_id = nor.stay_id
  AND co.endtime > nor.starttime AND co.endtime <= nor.endtime`.
- `mimiciv_derived.dopamine dop`: `co.stay_id = dop.stay_id
  AND co.endtime > dop.starttime AND co.endtime <= dop.endtime`.
- `mimiciv_derived.dobutamine dob`: `co.stay_id = dob.stay_id
  AND co.endtime > dob.starttime AND co.endtime <= dob.endtime`.

The join lower boundary is strict and the medication interval end boundary is
inclusive. `WHERE epi.stay_id IS NOT NULL OR nor.stay_id IS NOT NULL OR
dop.stay_id IS NOT NULL OR dob.stay_id IS NOT NULL` removes hourly rows with
no matching vasoactive interval. `MAX` of each dependency's `vaso_rate` is
then used to collapse medication fan-out to one row per `(stay_id, hr)`.

### `scorecomp` (lines 187--231)

`scorecomp` starts from `co` and `LEFT JOIN`s `vs`, the `gcs` CTE, `bili`,
`cr`, `plt`, `pf`, `uo`, and `vaso`, each on the two-column aggregate key:

```sql
co.stay_id = component.stay_id AND co.hr = component.hr
```

It selects the hourly spine, both time boundaries, and one aggregate from each
component CTE. There is no `GROUP BY` here; uniqueness is supplied by the
preceding aggregate CTEs.

`scorecalc` (lines 233--323) reads `scorecomp` without a join and appends the
six current-hour component score columns. `score_final` (lines 325--376)
reads `scorecalc` without a join, appends the rolling columns, and the outer
query applies `WHERE hr >= 0` (line 379).

The intermediate CTE schemas, including types inferred from the expressions,
are:

- `co`: `stay_id INTEGER`, `hadm_id INTEGER`, `hr BIGINT`, `starttime
  TIMESTAMP`, `endtime TIMESTAMP`.
- `pafi`: `stay_id INTEGER`, `charttime TIMESTAMP`,
  `pao2fio2ratio_novent DOUBLE`, `pao2fio2ratio_vent DOUBLE`.
- `vs`: `stay_id INTEGER`, `hr BIGINT`, `meanbp_min DOUBLE`.
- `gcs`: `stay_id INTEGER`, `hr BIGINT`, `gcs_min FLOAT`.
- `bili`: `stay_id INTEGER`, `hr BIGINT`, `bilirubin_max DOUBLE`.
- `cr`: `stay_id INTEGER`, `hr BIGINT`, `creatinine_max DOUBLE`.
- `plt`: `stay_id INTEGER`, `hr BIGINT`, `platelet_min DOUBLE`.
- `pf`: `stay_id INTEGER`, `hr BIGINT`, both P/F columns `DOUBLE`.
- `uo`: `stay_id INTEGER`, `hr BIGINT`, `uo_24hr DOUBLE`.
- `vaso`: `stay_id INTEGER`, `hr BIGINT`, the four `rate_*` columns
  `FLOAT`.
- `scorecomp`: the five `co` columns, the two P/F columns, four rate
  columns, `meanbp_min`, `gcs_min`, `uo_24hr`, `bilirubin_max`,
  `creatinine_max`, and `platelet_min`, in the order shown by output columns
  1--16 below.
- `scorecalc`: all `scorecomp` columns plus six nullable current-hour
  `INTEGER` scores: `respiration`, `coagulation`, `liver`,
  `cardiovascular`, `cns`, and `renal`.
- `score_final`: all `scorecalc` columns plus six rolling `INTEGER` scores
  and integer `sofa_24hours`.

## Exact dependency columns consumed

These are the only columns the SOFA SQL reads from the completed dependency
temp views. Columns present in a dependency but absent from this list, such as
medication `linkorderid` and `vaso_amount`, are not SOFA inputs.

| Temp view stem | Exact columns read (inferred type) | How the values are consumed |
|---|---|---|
| `icustay_hourly` | `stay_id` (`INTEGER`), `hr` (`BIGINT`), `endtime` (`TIMESTAMP`/source `DATETIME`) | Defines the ICU hourly spine, output `stay_id`/`hr`, interval end, and derived `starttime`. |
| `bg` | `subject_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `specimen` (`VARCHAR`), `pao2fio2ratio` (`DOUBLE`) | Subject join to ICU stays; arterial-blood-gas filter; time join; respiratory P/F ratio. |
| `ventilation` | `stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`/source `DATETIME`), `ventilation_status` (`VARCHAR`) | Matches the blood-gas time to an interval and classifies the P/F ratio as invasive-ventilated only for exact status `'InvasiveVent'`. |
| `vitalsign` | `stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `mbp` (`DOUBLE`) | Time-windowed minimum MAP (`meanbp_min`). |
| `gcs` | `stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `gcs` (`FLOAT`) | Time-windowed minimum GCS (`gcs_min`). |
| `enzyme` | `hadm_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `bilirubin_total` (`DOUBLE`) | Admission/time-windowed maximum bilirubin (`bilirubin_max`). |
| `chemistry` | `hadm_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `creatinine` (`DOUBLE`) | Admission/time-windowed maximum creatinine (`creatinine_max`). |
| `complete_blood_count` | `hadm_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `platelet` (`DOUBLE`) | Admission/time-windowed minimum platelet (`platelet_min`). |
| `urine_output_rate` | `stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`/source `DATETIME`), `uo_tm_24hr` (`DECIMAL(38,2)`), `urineoutput_24hr` (`DOUBLE`) | Time-windowed eligible 24-hour urine output and scaled rate (`uo_24hr`). |
| `epinephrine` | `stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`/source `DATETIME`), `vaso_rate` (`FLOAT`) | End-aligned medication interval; hourly maximum `rate_epinephrine`. |
| `norepinephrine` | `stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`/source `DATETIME`), `vaso_rate` (`FLOAT`) | End-aligned medication interval; hourly maximum `rate_norepinephrine`. |
| `dopamine` | `stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`/source `DATETIME`), `vaso_rate` (`FLOAT`) | End-aligned medication interval; hourly maximum `rate_dopamine`. |
| `dobutamine` | `stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`/source `DATETIME`), `vaso_rate` (`FLOAT`) | End-aligned medication interval; hourly maximum `rate_dobutamine`. |

The raw `mimiciv_icu.icustays` relation is not a dependency temp view. SOFA
reads its `stay_id` (`INTEGER`), `hadm_id` (`INTEGER`), and `subject_id`
(`INTEGER`): `stay_id` joins to `icustay_hourly` and is used in `pafi`;
`hadm_id` is carried into `co` for the three hospital-lab joins; and
`subject_id` joins the blood-gas stream. `subject_id` and `hadm_id` are
intermediate-only inputs and are not final output columns.

Inferred dependency value types used by SOFA are: identifiers `INTEGER`,
`hr` `BIGINT`, datetimes `TIMESTAMP`/source `DATETIME`, `pao2fio2ratio`
`DOUBLE`, `uo_tm_24hr` `DECIMAL(38,2)`, `vaso_rate` `FLOAT`, and the aggregate
analytes (`mbp`, `bilirubin_total`, `creatinine`, `platelet`, and urine
quantities) numeric floating-point values; the completed `gcs.gcs` output is
`FLOAT`. The final output types are listed exactly below.

## Filters, literals, and value boundaries

### Row filters and coded literals in `sofa.sql`

The complete direct filter set in this file is:

1. `WHERE specimen = 'ART.'` in `pafi`, filtering the `specimen` column of
   the completed `bg` dependency and feeding the two pafi respiratory ratio
   columns. The literal is copied verbatim, including the period.
2. `AND vd.ventilation_status = 'InvasiveVent'` in the `pafi` **LEFT JOIN
   condition**, filtering the `ventilation` dependency's status column and
   determining whether `pao2fio2ratio` feeds `pao2fio2ratio_vent` rather than
   `pao2fio2ratio_novent`.
3. `WHERE epi.stay_id IS NOT NULL OR nor.stay_id IS NOT NULL OR
   dop.stay_id IS NOT NULL OR dob.stay_id IS NOT NULL` in `vaso`, retaining
   only hours with at least one matched epinephrine, norepinephrine, dopamine,
   or dobutamine interval.
4. Final `WHERE hr >= 0`, retaining hour zero and later and excluding the
   `icustay_hourly` pre-ICU negative-hour rows.

There are **no direct `itemid` or ICD literals in `sofa.sql`**. The literal
code specification for this concept is therefore exactly `'ART.'` on
`bg.specimen` and `'InvasiveVent'` on `ventilation.ventilation_status`, plus
the numeric boundaries below. Itemid filters owned by `bg`, `gcs`,
`vitalsign`, the laboratory dependencies, and the medication dependencies
belong to those completed concepts' source SQL; SOFA must consume their temp
views and must not copy or invent those code lists. There are no dead direct
filters in this file.

### Numeric/value constraints that change score values

These are `CASE` predicates, not row-eliminating `WHERE` clauses, but every
boundary is semantically part of the source specification:

- **Respiration:** `pao2fio2ratio_vent < 100` → 4; `< 200` → 3;
  `pao2fio2ratio_novent < 300 OR pao2fio2ratio_vent < 300` → 2;
  `pao2fio2ratio_novent < 400 OR pao2fio2ratio_vent < 400` → 1; both ratios
  NULL → NULL; otherwise 0. The order is part of the behavior.
- **Coagulation:** `platelet_min < 20` → 4; `< 50` → 3; `< 100` → 2;
  `< 150` → 1; NULL → NULL; otherwise 0.
- **Liver:** `bilirubin_max >= 12.0` → 4; `>= 6.0` → 3; `>= 2.0` → 2;
  `>= 1.2` → 1; NULL → NULL; otherwise 0.
- **Cardiovascular:**
  `(rate_dopamine > 15 OR rate_epinephrine > 0.1 OR
  rate_norepinephrine > 0.1)` → 4;
  `(rate_dopamine > 5 OR rate_epinephrine <= 0.1 OR
  rate_norepinephrine <= 0.1)` → 3;
  `(rate_dopamine > 0 OR rate_dobutamine > 0)` → 2;
  `meanbp_min < 70` → 1; all five inputs NULL → NULL; otherwise 0.
  The two `<= 0.1` predicates and their placement are literal source
  behavior and must not be clinically “corrected”.
- **CNS:** `(gcs_min >= 13 AND gcs_min <= 14)` → 1;
  `(gcs_min >= 10 AND gcs_min <= 12)` → 2;
  `(gcs_min >= 6 AND gcs_min <= 9)` → 3; `gcs_min < 6` → 4;
  NULL → NULL; otherwise 0.
- **Renal:** `creatinine_max >= 5.0 OR uo_24hr < 200` → 4;
  `creatinine_max >= 3.5 AND creatinine_max < 5.0` or `uo_24hr < 500`
  → 3; `creatinine_max >= 2.0 AND creatinine_max < 3.5` → 2;
  `creatinine_max >= 1.2 AND creatinine_max < 2.0` → 1;
  both `uo_24hr` and `creatinine_max` NULL → NULL; otherwise 0. CASE order
  is significant when both creatinine and urine conditions are present.
- **Urine eligibility:** `uo_tm_24hr >= 22 AND uo_tm_24hr <= 30`, then
  `urineoutput_24hr / uo_tm_24hr * 24` before the `MAX` aggregate.

## Aggregations and windows

- `vs`, `gcs`, `bili`, `cr`, `plt`, `pf`, `uo`, and `vaso` all `GROUP BY
  co.stay_id, co.hr`.
- Aggregates are `MIN(mbp)`, `MIN(gcs)`, `MAX(bilirubin_total)`,
  `MAX(creatinine)`, `MIN(platelet)`, `MIN` of each P/F branch, `MAX` of the
  eligible urine-rate expression, and `MAX` of each vasoactive rate.
- `score_final` defines window `w` as:

  ```sql
  PARTITION BY stay_id
  ORDER BY hr
  ROWS BETWEEN 23 PRECEDING AND 0 FOLLOWING
  ```

  It computes `MAX(respiration)`, `MAX(coagulation)`, `MAX(liver)`,
  `MAX(cardiovascular)`, `MAX(cns)`, and `MAX(renal)` over that exact 24-row
  frame. Each is wrapped in `COALESCE(..., 0)`.
- `sofa_24hours` is the sum of those six coalesced window maxima. There is no
  `GROUP BY` in `scorecalc` or `score_final`, no time-range window, and no
  additional aggregation after the rolling window.

## Exact output shape and types

The outer `SELECT * FROM score_final` preserves the following CTE column
order. The types below are the oracle manifest's normalized types and agree
with the SQL expressions; source BigQuery `DATETIME` is represented as
`TIMESTAMP` by the output contract.

| # | Output column | Type | Produced by |
|---:|---|---|---|
| 1 | `stay_id` | `INTEGER` | `co` |
| 2 | `hr` | `BIGINT` | `co` / `icustay_hourly.hr` |
| 3 | `starttime` | `TIMESTAMP` | `co`, `endtime - 1 hour` |
| 4 | `endtime` | `TIMESTAMP` | `co` |
| 5 | `pao2fio2ratio_novent` | `DOUBLE` | `pf` |
| 6 | `pao2fio2ratio_vent` | `DOUBLE` | `pf` |
| 7 | `rate_epinephrine` | `FLOAT` | `vaso` |
| 8 | `rate_norepinephrine` | `FLOAT` | `vaso` |
| 9 | `rate_dopamine` | `FLOAT` | `vaso` |
| 10 | `rate_dobutamine` | `FLOAT` | `vaso` |
| 11 | `meanbp_min` | `DOUBLE` | `vs` |
| 12 | `gcs_min` | `FLOAT` | `gcs` |
| 13 | `uo_24hr` | `DOUBLE` | `uo` |
| 14 | `bilirubin_max` | `DOUBLE` | `bili` |
| 15 | `creatinine_max` | `DOUBLE` | `cr` |
| 16 | `platelet_min` | `DOUBLE` | `plt` |
| 17 | `respiration` | `INTEGER` | `scorecalc` |
| 18 | `coagulation` | `INTEGER` | `scorecalc` |
| 19 | `liver` | `INTEGER` | `scorecalc` |
| 20 | `cardiovascular` | `INTEGER` | `scorecalc` |
| 21 | `cns` | `INTEGER` | `scorecalc` |
| 22 | `renal` | `INTEGER` | `scorecalc` |
| 23 | `respiration_24hours` | `INTEGER` | `score_final` |
| 24 | `coagulation_24hours` | `INTEGER` | `score_final` |
| 25 | `liver_24hours` | `INTEGER` | `score_final` |
| 26 | `cardiovascular_24hours` | `INTEGER` | `score_final` |
| 27 | `cns_24hours` | `INTEGER` | `score_final` |
| 28 | `renal_24hours` | `INTEGER` | `score_final` |
| 29 | `sofa_24hours` | `INTEGER` | `score_final` |

The source natural grain is one row per `(stay_id, hr)` after `hr >= 0`.
The oracle manifest declares the keyed comparison as `(stay_id, starttime)`;
the FHIR comparison metadata also carries ICU encounter and patient resource
keys. `subject_id` and `hadm_id` are not source output columns, and no
additional source output columns may be invented. The manifest records the
SOFA result as a keyed join on `(stay_id, starttime)`.

## Semantically essential inputs and trace

These fields can alter inclusion, the natural grain, a temporal join,
carry-forward/rolling behavior, or a clinically meaningful SOFA output. They
must be retained by the completed dependency views and cannot be replaced by
labels or guessed resource identifiers.

- `icustay_hourly.stay_id`: defines the ICU stay, all aggregate joins, the
  final row identity, and the window partition. `icustays.stay_id` enforces
  the inner-join cohort.
- `icustay_hourly.hr`: defines the hourly row and window order, controls the
  final `hr >= 0` inclusion rule, and participates in the aggregate-CTE join
  key. It is also part of the source natural grain.
- `icustay_hourly.endtime` and derived `starttime`: define every measurement
  window and each vasoactive interval test; `starttime` and `endtime` are
  final outputs. A datetime parse or timezone conversion that changes these
  values changes row membership and all hourly aggregates.
- `icustays.hadm_id`: controls whether chemistry, enzyme, and CBC rows match
  the ICU-hour spine. It is intermediate-only but essential to the lab
  branches.
- `icustays.subject_id`: controls the `pafi` blood-gas inner join. The source
  deliberately joins blood gases by subject, then uses the stay-specific
  ventilation interval to split the P/F branches.
- `bg.specimen = 'ART.'`, `bg.charttime`, and `bg.pao2fio2ratio`: the specimen
  discriminator controls whether a blood gas enters `pafi`; charttime
  controls hourly membership; the ratio controls `respiration` and its
  rolling version.
- `ventilation.stay_id`, `starttime`, `endtime`, and exact status
  `'InvasiveVent'`: control the ventilated/non-ventilated P/F branch and the
  blood-gas interval match. This is not recoverable by reclassifying a raw
  FHIR observation inside SOFA; consume the completed `ventilation` view.
- `vitalsign.charttime` and `mbp`: determine the time-windowed `meanbp_min`
  and therefore the cardiovascular branch when no higher vasoactive branch
  fires.
- `gcs.charttime` and `gcs.gcs`: determine `gcs_min`, the CNS component, and
  its 24-row carry-forward maximum. The upstream GCS discriminator is
  especially essential: the canonical GCS dependency uses the
  `No Response-ETT` source value in its derivation, and its carryover notes
  document that losing that discriminator changes the GCS and subsequent
  carry-forward. SOFA must consume the completed `gcs` view rather than
  rederive GCS from FHIR quantities.
- `enzyme.hadm_id`, `enzyme.charttime`, and `bilirubin_total`: determine the
  liver maximum and liver scores.
- `chemistry.hadm_id`, `chemistry.charttime`, and `creatinine`: determine the
  renal creatinine maximum and renal scores.
- `complete_blood_count.hadm_id`, `complete_blood_count.charttime`, and
  `platelet`: determine the coagulation minimum and coagulation scores.
- `urine_output_rate.stay_id`, `charttime`, `uo_tm_24hr`, and
  `urineoutput_24hr`: control eligible urine rows, the scaled `uo_24hr`, and
  the renal component. `uo_tm_24hr` is both an inclusion discriminator and a
  divisor; it cannot be replaced by a raw urine total.
- Each vaso dependency's `stay_id`, `starttime`, `endtime`, and `vaso_rate`
  controls whether `vaso` retains an hourly row, the four hourly maxima, and
  the cardiovascular score. `linkorderid` and `vaso_amount` are not consumed.
- All six score-component CASE inputs and their exact comparison boundaries
  control current-hour scores. Nullness is itself essential: a missing
  component remains NULL in `scorecalc`, while a missing 24-hour maximum is
  converted to 0 in `score_final`.
- `stay_id` and `hr` are essential to the rolling frame: the window is
  `ROWS`, not a timestamp `RANGE`, so preserving one ordered hourly row per
  stay is required for the intended 24-row carry-forward.

## Files and checks used

Read and checked:

- `mimic-iv/concepts/score/sofa.sql`.
- `mimic-iv/concept_dag/concept_dag.json` and the generated relevant section of
  `concept_dag.md` (node, level, dependency edges, topological order, raw
  table inventory).
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, especially the datetime/
  `TIMESTAMP_NTZ`, dependency/`patient_sofa`, resource-key, and essential-loss
  guidance.
- Relevant provisional fragments:
  `MIMIC_NOTES.d/chemistry.md`, `complete_blood_count.md`, `dobutamine.md`,
  `dopamine.md`, `epinephrine.md`, `gcs.md`, `icustay_hourly.md`,
  `icustay_times.md`, `norepinephrine.md`, `urine_output.md`,
  `ventilation.md`, `vitalsign.md`, `oxygen_delivery.md`, and
  `ventilator_setting.md`. No `sofa.md`, `bg.md`, or `enzyme.md` fragment
  exists; the main notes and canonical dependency SQL were used for those
  inputs.
- Canonical dependency SQLs for the exact output fields consumed:
  `demographics/icustay_hourly.sql`, `demographics/icustay_times.sql`,
  `measurement/bg.sql`, `measurement/chemistry.sql`,
  `measurement/complete_blood_count.sql`, `measurement/enzyme.sql`,
  `measurement/gcs.sql`, `measurement/urine_output_rate.sql`,
  `measurement/vitalsign.sql`, `medication/dobutamine.sql`,
  `medication/dopamine.sql`, `medication/epinephrine.sql`,
  `medication/norepinephrine.sql`, and `treatment/ventilation.sql`.
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for the exact
  normalized SOFA output names, types, comparison key, and grain metadata.

Checks performed: enumerated every CTE `FROM`/`JOIN`, join type and predicate;
traced every selected/intermediate column and dependency field; copied all
direct literals and row/value boundaries; enumerated all `GROUP BY`, scalar
aggregates, and window expressions; verified the DAG dependency set and
source SHA256; and confirmed the 29-column output order and manifest types.
