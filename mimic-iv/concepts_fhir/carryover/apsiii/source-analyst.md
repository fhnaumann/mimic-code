# APS III source analysis

## Source and DAG metadata

- Concept: `apsiii`
- Canonical SQL: `mimic-iv/concepts/score/apsiii.sql`
- DAG path: `score/apsiii.sql`
- DAG level: `2`
- DAG SHA256: `9692a6342940d7c2f885a67db72fc18ce38eab174c4e360a3fe82262d03085c0`
- The SHA256 of the canonical SQL was checked and matches the DAG value.
- DAG dependencies, which must be ported first and are available to candidate SQL
  by their unqualified stems, are: `bg`, `first_day_gcs`, `first_day_lab`,
  `first_day_urine_output`, `first_day_vitalsign`, and `ventilation`.
- The loop contract and current MIMIC-on-FHIR notes were read. In particular,
  the candidate must preserve these dependency boundaries, must not parse or
  reconstruct FHIR resource IDs, and must emit the FHIR resource-key columns
  required by the manifest in addition to the relational identifier columns.

## 1. Grain, row inclusion, and output contract

The final query is anchored on `mimiciv_icu.icustays ie` and performs a `LEFT
JOIN score` on `stay_id`. Its intended semantic grain is one row per ICU stay
(`stay_id`), for **all** ICU stays. The score-side CTEs are intended to be one
row per stay; the `ROW_NUMBER()` filters and per-stay/per-admission aggregates
enforce that for the locally computed branches. The final `LEFT JOIN` means a
stay remains in the result even when its score-side row is absent. The final
identifiers come from `ie`, not from `score`.

The full oracle manifest confirms the comparison key and output types:

| output column | required type | role |
|---|---:|---|
| `subject_id` | `INTEGER` | patient identifier |
| `hadm_id` | `INTEGER` | hospital admission identifier |
| `stay_id` | `INTEGER` | ICU-stay identifier and manifest key |
| `apsiii` | `INTEGER` | sum of the sixteen component scores |
| `apsiii_prob` | `DOUBLE` | logistic hospital-mortality probability |
| `hr_score` | `INTEGER` | heart-rate component |
| `mbp_score` | `INTEGER` | mean-blood-pressure component |
| `temp_score` | `INTEGER` | temperature component |
| `resp_rate_score` | `INTEGER` | respiratory-rate component |
| `pao2_aado2_score` | `INTEGER` | oxygenation component |
| `hematocrit_score` | `INTEGER` | hematocrit component |
| `wbc_score` | `INTEGER` | WBC component |
| `creatinine_score` | `INTEGER` | creatinine/ARF component |
| `uo_score` | `INTEGER` | urine-output component |
| `bun_score` | `INTEGER` | BUN component |
| `sodium_score` | `INTEGER` | sodium component |
| `albumin_score` | `INTEGER` | albumin component |
| `bilirubin_score` | `INTEGER` | total-bilirubin component |
| `glucose_score` | `INTEGER` | glucose component |
| `acidbase_score` | `INTEGER` | pH/pCO2 interaction component |
| `gcs_score` | `INTEGER` | GCS interaction component |

The manifest records `comparison = keyed_join`, `key = ["stay_id"]`, and
`row_count = 73181`. Its `key_columns` are `encounter_key`,
`icu_encounter_key`, and `patient_key`; these are FHIR identity columns needed
by the loop's downstream SQL-on-FHIR layer, even though they are not columns in
the canonical relational `SELECT`. They must be retained as opaque resource
keys and joined by equality only.

## 2. Every physical table reference and join

The SQL uses BigQuery-style project qualification
`physionet-data.<schema>.<table>`. The physical schemas and tables are:

### `pa` CTE (lines 35-53)

- `FROM mimiciv_derived.bg bg`.
- `INNER JOIN mimiciv_icu.icustays ie` on
  `bg.hadm_id = ie.hadm_id AND bg.charttime >= ie.intime AND bg.charttime < ie.outtime`.
- `LEFT JOIN mimiciv_derived.ventilation vd` on
  `ie.stay_id = vd.stay_id AND bg.charttime >= vd.starttime AND
  bg.charttime <= vd.endtime AND vd.ventilation_status = 'InvasiveVent'`.
- The `LEFT JOIN` plus `WHERE vd.stay_id IS NULL` is an anti-join: this branch
  retains arterial blood gases taken during the ICU stay while not covered by
  an invasive-ventilation interval.

### `aa` CTE (lines 55-77)

- `FROM mimiciv_derived.bg bg`.
- `INNER JOIN mimiciv_icu.icustays ie` on the same admission and ICU-window
  predicates as `pa`.
- `INNER JOIN mimiciv_derived.ventilation vd` on
  `ie.stay_id = vd.stay_id AND bg.charttime >= vd.starttime AND
  bg.charttime <= vd.endtime AND vd.ventilation_status = 'InvasiveVent'`.
- This is the ventilated arterial branch and is also constrained to FiO2 at
  least 50% and non-null `aado2`.

### `acidbase` CTE (lines 82-136)

- `FROM mimiciv_derived.bg bg`.
- `INNER JOIN mimiciv_icu.icustays ie` on
  `bg.hadm_id = ie.hadm_id AND bg.charttime >= ie.intime AND bg.charttime < ie.outtime`.
- No ventilation join is used. Arterial gases with non-null `ph` and `pco2`
  feed the pH/pCO2 interaction score.

### `acidbase_max` CTE (lines 138-145)

- `FROM acidbase` (an internal CTE, not a physical source table).
- No join; one row is later retained per `stay_id` by `acidbase_rn = 1`.

### `arf` CTE (lines 151-188)

- `FROM mimiciv_icu.icustays ie`.
- `LEFT JOIN mimiciv_derived.first_day_urine_output uo` on
  `ie.stay_id = uo.stay_id`.
- `LEFT JOIN mimiciv_derived.first_day_lab labs` on
  `ie.stay_id = labs.stay_id`.
- `LEFT JOIN` an inline `icd` aggregate on `mimiciv_hosp.diagnoses_icd`.
  The inline aggregate groups by `hadm_id` and is joined on
  `ie.hadm_id = icd.hadm_id`.

### Inline `icd` aggregate (lines 168-186)

- `FROM mimiciv_hosp.diagnoses_icd`.
- No join; `GROUP BY hadm_id` produces one `ckd` flag per admission.

### `vent` CTE (lines 191-215)

- `FROM mimiciv_icu.icustays ie`.
- `LEFT JOIN mimiciv_derived.ventilation v` on
  `ie.stay_id = v.stay_id AND v.ventilation_status = 'InvasiveVent'` and
  the interval-overlap condition:
  - `v.starttime >= ie.intime AND v.starttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`, **or**
  - `v.endtime >= ie.intime AND v.endtime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`, **or**
  - `v.starttime <= ie.intime AND v.endtime >= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`.
- This produces a first-day invasive-ventilation indicator per stay.

### `cohort` CTE (lines 217-318)

- `FROM mimiciv_icu.icustays ie`.
- `INNER JOIN mimiciv_hosp.admissions adm` on `ie.hadm_id = adm.hadm_id`.
- `INNER JOIN mimiciv_hosp.patients pat` on `ie.subject_id = pat.subject_id`.
- `LEFT JOIN pa` on `ie.stay_id = pa.stay_id AND pa.rn = 1`.
- `LEFT JOIN aa` on `ie.stay_id = aa.stay_id AND aa.rn = 1`.
- `LEFT JOIN acidbase_max ab` on
  `ie.stay_id = ab.stay_id AND ab.acidbase_rn = 1`.
- `LEFT JOIN arf` on `ie.stay_id = arf.stay_id`.
- `LEFT JOIN vent` on `ie.stay_id = vent.stay_id`.
- `LEFT JOIN mimiciv_derived.first_day_gcs gcs` on
  `ie.stay_id = gcs.stay_id`.
- `LEFT JOIN mimiciv_derived.first_day_vitalsign vital` on
  `ie.stay_id = vital.stay_id`.
- `LEFT JOIN mimiciv_derived.first_day_urine_output uo` on
  `ie.stay_id = uo.stay_id`.
- `LEFT JOIN mimiciv_derived.first_day_lab labs` on
  `ie.stay_id = labs.stay_id`.

The two inner joins to `admissions` and `patients` are the only cohort joins
that can remove an ICU-stay row. The remaining joins are left joins and must
preserve missing component data as NULL.

### `score_min` and `score_max` CTEs (lines 321-444 and 446-569)

- Each has `FROM cohort` and no join or filter. They calculate identical CASE
  scoring rules over the minimum or maximum value columns, respectively.

### `scorecomp` CTE (lines 577-843)

- `FROM cohort co`.
- `LEFT JOIN score_min smin ON co.stay_id = smin.stay_id`.
- `LEFT JOIN score_max smax ON co.stay_id = smax.stay_id`.
- It chooses the value/score for each APS component and retains the cohort row.

### `score` CTE (lines 846-868)

- `FROM scorecomp s`.
- No join or filter. It adds `apsiii` by summing coalesced component scores.

### Final SELECT (lines 870-894)

- `FROM mimiciv_icu.icustays ie`.
- `LEFT JOIN score s ON ie.stay_id = s.stay_id`.
- No final `WHERE`, `GROUP BY`, or `HAVING`.

## 3. Columns and inferred types

### Direct source and dependency columns consumed

The following are the exact dependency columns consumed by this concept. They
are dependency outputs, not fields to rederive from FHIR resources. Candidate
SQL should use the completed dependency temp views under these unqualified
stems (`bg`, `first_day_gcs`, `first_day_lab`,
`first_day_urine_output`, `first_day_vitalsign`, `ventilation`).

| dependency/source | columns consumed | inferred type/context |
|---|---|---|
| `mimiciv_icu.icustays` | `subject_id`, `hadm_id`, `stay_id` | `INTEGER` identifiers |
| `mimiciv_icu.icustays` | `intime`, `outtime` | `TIMESTAMP` |
| `mimiciv_hosp.admissions` | `hadm_id` | `INTEGER` join identifier |
| `mimiciv_hosp.patients` | `subject_id` | `INTEGER` join identifier |
| `mimiciv_hosp.diagnoses_icd` | `hadm_id`, `icd_code`, `icd_version` | `INTEGER`, `CHAR(7)`, `SMALLINT` |
| `bg` | `hadm_id`, `charttime` | `INTEGER`, timestamp-like |
| `bg` | `po2`, `aado2`, `ph`, `pco2`, `fio2`, `fio2_chartevents` | numeric measurements |
| `bg` | `specimen` | text categorical value |
| `ventilation` | `stay_id`, `starttime`, `endtime` | `INTEGER`, timestamp-like |
| `ventilation` | `ventilation_status` | text categorical value |
| `first_day_urine_output` | `stay_id`, `urineoutput` | `INTEGER`, numeric aggregate |
| `first_day_lab` | `stay_id` | `INTEGER` |
| `first_day_lab` | `hematocrit_min`, `hematocrit_max`, `wbc_min`, `wbc_max` | numeric aggregates |
| `first_day_lab` | `creatinine_min`, `creatinine_max`, `bun_min`, `bun_max` | numeric aggregates |
| `first_day_lab` | `sodium_min`, `sodium_max`, `albumin_min`, `albumin_max` | numeric aggregates |
| `first_day_lab` | `bilirubin_total_min`, `bilirubin_total_max`, `glucose_min`, `glucose_max` | numeric aggregates |
| `first_day_vitalsign` | `stay_id` | `INTEGER` |
| `first_day_vitalsign` | `heart_rate_min`, `heart_rate_max`, `mbp_min`, `mbp_max` | numeric aggregates |
| `first_day_vitalsign` | `temperature_min`, `temperature_max`, `resp_rate_min`, `resp_rate_max` | numeric aggregates |
| `first_day_vitalsign` | `glucose_min`, `glucose_max` | numeric aggregates |
| `first_day_gcs` | `stay_id`, `gcs_min`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs_unable` | `INTEGER` identifiers/components and numeric categorical components |

`bg.subject_id`, `bg.specimen_id`, raw itemids, and other fields of the `bg`
dependency are not read by `apsiii.sql`. Likewise, fields not listed above
from the first-day dependencies are not consumed by this concept.

### Intermediate CTE columns

- `pa`: `stay_id` (`INTEGER`), `charttime` (timestamp), `pao2` (numeric alias
  of `bg.po2`), and `rn` (window row number, integer-like/bigint). `rn = 1`
  retains the highest qualifying PaO2 per stay.
- `aa`: `stay_id`, `charttime`, `aado2` (numeric), and `rn` (integer-like/
  bigint). `rn = 1` retains the highest qualifying A-aDO2 per stay.
- `acidbase`: `stay_id` (`INTEGER`), `ph` (numeric), `paco2` (numeric alias
  of `pco2`), and `acidbase_score` (nullable integer).
- `acidbase_max`: `stay_id`, `acidbase_score`, `ph`, `paco2`, and
  `acidbase_rn` (integer-like/bigint). Only `acidbase_rn = 1` is joined into
  `cohort`.
- Inline `icd`: `hadm_id` (`INTEGER`) and `ckd` (integer 0/1), one row per
  admission with at least one diagnosis row. An admission with no diagnosis
  row has NULL `ckd` after the outer join.
- `arf`: `stay_id` (`INTEGER`) and `arf` (nullable in principle, but the CASE
  returns integer `1` or `0`; with the SQL's ELSE it is normally non-null).
- `vent`: `stay_id` (`INTEGER`) and `vent` (integer 0/1 from `MAX`).
- `cohort`: identifiers `subject_id`, `hadm_id`, `stay_id` (all `INTEGER`),
  `intime`/`outtime` (timestamps), and the following numeric or integer-like
  columns: `heart_rate_min`, `heart_rate_max`, `mbp_min`, `mbp_max`,
  `temperature_min`, `temperature_max`, `resp_rate_min`, `resp_rate_max`,
  `pao2`, `aado2`, `ph`, `paco2`, `acidbase_score`,
  `hematocrit_min`, `hematocrit_max`, `wbc_min`, `wbc_max`,
  `creatinine_min`, `creatinine_max`, `bun_min`, `bun_max`,
  `sodium_min`, `sodium_max`, `albumin_min`, `albumin_max`,
  `bilirubin_min`, `bilirubin_max`, `glucose_min`, `glucose_max`, `vent`,
  `urineoutput`, `mingcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`,
  `gcs_unable`, and `arf`. `bilirubin_min/max` are aliases of
  `labs.bilirubin_total_min/max`; `glucose_min/max` are the merged lab/vital
  values described below.
- `score_min` and `score_max`: the three identifiers plus twelve nullable
  integer component scores: `hr_score`, `mbp_score`, `temp_score`,
  `resp_rate_score`, `hematocrit_score`, `wbc_score`, `creatinine_score`,
  `bun_score`, `sodium_score`, `albumin_score`, `bilirubin_score`, and
  `glucose_score`.
- `scorecomp`: `co.*` (all cohort columns) plus the selected/worst-value
  integer scores `hr_score`, `mbp_score`, `temp_score`, `resp_rate_score`,
  `hematocrit_score`, `wbc_score`, `creatinine_score`, `bun_score`,
  `sodium_score`, `albumin_score`, `bilirubin_score`, `glucose_score`,
  `uo_score`, `gcs_score`, and `pao2_aado2_score`. The cohort's existing
  `acidbase_score` is retained rather than recomputed in this CTE.
- `score`: all `scorecomp` columns plus `apsiii` (integer-like sum; the
  manifest requires `INTEGER`).

Some intermediate selected columns are dead with respect to the final output:
`intime`, `outtime`, `mingcs`, `ph`, `paco2`, and the raw component values are
carried through `cohort`/`scorecomp` but are not selected by the final query.
They must nevertheless not be confused with the values that drive their
associated scores; `acidbase_score`, for example, remains final output.

## 4. Filters, time windows, and value constraints

### Explicit `WHERE` predicates in `apsiii.sql`

These are all the source SQL `WHERE` predicates:

1. `pa`: `vd.stay_id IS NULL` (not covered by an invasive ventilation
   interval); `COALESCE(fio2, fio2_chartevents, 21) < 50`; `bg.po2 IS NOT
   NULL`; and `bg.specimen = 'ART.'`.
2. `aa`: `vd.stay_id IS NOT NULL` (covered by invasive ventilation);
   `COALESCE(fio2, fio2_chartevents) >= 50`; `bg.aado2 IS NOT NULL`; and
   `bg.specimen = 'ART.'`.
3. `acidbase`: `ph IS NOT NULL AND pco2 IS NOT NULL`, and
   `bg.specimen = 'ART.'`.

There is no `WHERE` in `arf`, `vent`, `cohort`, `score_min`, `score_max`,
`scorecomp`, `score`, or the final query. The `ventilation_status` and time
constraints in the `ON` clauses are still row-selection predicates and are
listed above under joins.

### Time semantics

- The direct blood-gas branches use the entire half-open ICU stay interval:
  `charttime >= intime` and `charttime < outtime`.
- The `vent` flag uses the inclusive first-day interval ending at
  `DATETIME_ADD(intime, INTERVAL '1' DAY)` and treats a ventilation interval as
  overlapping if either endpoint is in that interval or it fully encloses the
  interval.
- The first-day dependency outputs are already aggregated by their own SQL.
  The dependency definitions use a `[-6 hours, +1 day]` window for first-day
  labs, vitals, and GCS, and `[intime, +1 day]` for first-day urine output. The
  APS III candidate must consume those completed outputs rather than
  reimplementing their windows.

### ARF and CKD logic

The inline admission aggregate is:

```sql
MAX(CASE
    WHEN icd_version = 9 AND SUBSTR(icd_code, 1, 4)
         IN ('5854', '5855', '5856') THEN 1
    WHEN icd_version = 10 AND SUBSTR(icd_code, 1, 4)
         IN ('N184', 'N185', 'N186') THEN 1
    ELSE 0
END) AS ckd
```

`arf = 1` only if `creatinine_max >= 1.5`, `urineoutput < 410`, and
`icd.ckd = 0`; otherwise it is `0`. The source comment explicitly says that
`5859` is intentionally excluded because it can represent acute-on-chronic
ARF; do not add it. A missing `icd` aggregate leaves `ckd` NULL, so the
three-way condition is not true and the `arf` CASE takes its `ELSE 0`.

### Lab/vital glucose merge

`cohort.glucose_max` is NULL only when both `labs.glucose_max` and
`vital.glucose_max` are NULL. If one side is NULL, the other is used; if both
are present, the larger is used, with the lab value selected on equality.
`cohort.glucose_min` follows the analogous rule using the smaller value and
also selects the lab value on equality. These merged extrema, not either raw
source alone, feed glucose scoring.

### Min/max score lookup rules

`score_min` applies these CASE rules to each `*_min` value and `score_max`
applies the same rules to each `*_max` value. Every rule first returns NULL
when its input is NULL. Bounds are lower-inclusive through ordered `<` tests,
with the final `>=` branch as shown:

| component | exact ordered value rules (value -> score) |
|---|---|
| heart rate | `< 40 -> 8`; `< 50 -> 5`; `< 100 -> 0`; `< 110 -> 1`; `< 120 -> 5`; `< 140 -> 7`; `< 155 -> 13`; `>= 155 -> 17` |
| MBP | `< 40 -> 23`; `< 60 -> 15`; `< 70 -> 7`; `< 80 -> 6`; `< 100 -> 0`; `< 120 -> 4`; `< 130 -> 7`; `< 140 -> 9`; `>= 140 -> 10` |
| temperature | `< 33.0 -> 20`; `< 33.5 -> 16`; `< 34.0 -> 13`; `< 35.0 -> 8`; `< 36.0 -> 2`; `< 40.0 -> 0`; `>= 40.0 -> 4` |
| respiratory rate | if `vent = 1` and value `< 14`, `0`; otherwise `< 6 -> 17`; `< 12 -> 8`; `< 14 -> 7`; `< 25 -> 0`; `< 35 -> 6`; `< 40 -> 9`; `< 50 -> 11`; `>= 50 -> 18` |
| hematocrit | `< 41.0 -> 3`; `< 50.0 -> 0`; `>= 50.0 -> 3` |
| WBC | `< 1.0 -> 19`; `< 3.0 -> 5`; `< 20.0 -> 0`; `< 25.0 -> 1`; `>= 25.0 -> 5` |
| creatinine | if `arf = 1` and value `< 1.5`, `0`; if `arf = 1` and value `>= 1.5`, `10`; otherwise `< 0.5 -> 3`; `< 1.5 -> 0`; `< 1.95 -> 4`; `>= 1.95 -> 7` |
| BUN | `< 17.0 -> 0`; `< 20.0 -> 2`; `< 40.0 -> 7`; `< 80.0 -> 11`; `>= 80.0 -> 12` |
| sodium | `< 120 -> 3`; `< 135 -> 2`; `< 155 -> 0`; `>= 155 -> 4` |
| albumin | `< 2.0 -> 11`; `< 2.5 -> 6`; `< 4.5 -> 0`; `>= 4.5 -> 4` |
| bilirubin | `< 2.0 -> 0`; `< 3.0 -> 5`; `< 5.0 -> 6`; `< 8.0 -> 8`; `>= 8.0 -> 16` |
| glucose | `< 40 -> 8`; `< 60 -> 9`; `< 200 -> 0`; `< 350 -> 3`; `>= 350 -> 5` |

### Acid-base score

`acidbase_score` is calculated within one blood gas, only when both `ph` and
`pco2` are non-null, then the maximum score per stay is selected. The exact
branch table is:

| pH branch | pCO2 branch (ordered) |
|---|---|
| `ph < 7.20` | `< 50 -> 12`; otherwise `4` |
| `ph < 7.30` | `< 30 -> 9`; `< 40 -> 6`; `< 50 -> 3`; otherwise `2` |
| `ph < 7.35` | `< 30 -> 9`; `< 45 -> 0`; otherwise `1` |
| `ph < 7.45` | `< 30 -> 5`; `< 45 -> 0`; otherwise `1` |
| `ph < 7.50` | `< 30 -> 5`; `< 35 -> 0`; `< 45 -> 2`; otherwise `12` |
| `ph < 7.60` | `< 40 -> 3`; otherwise `12` |
| `ph >= 7.60` | `< 25 -> 0`; `< 40 -> 3`; otherwise `12` |

### Worst-value selection in `scorecomp`

For the paired min/max scores, the source chooses the value furthest from a
normal center; if equidistant, it chooses the larger score. The normal centers
are:

| component | normal center / special selection |
|---|---|
| heart rate | `75` |
| MBP | `90` |
| temperature | `38` |
| respiratory rate | `19` |
| hematocrit | `45.5` |
| WBC | `11.5` |
| creatinine | `1`; if `arf = 1`, always use `smax.creatinine_score` |
| BUN | always use `smax.bun_score` when `bun_max` is non-null |
| sodium | `145.5` |
| albumin | `3.5` |
| bilirubin | always use `smax.bilirubin_score` when `bilirubin_max` is non-null |
| glucose | `130` |

The `WHEN <max> IS NULL THEN NULL` guard is present for every selector. For
heart rate, MBP, and temperature the equality test compares the max and min
distances as written. For respiratory rate, hematocrit, WBC, sodium, albumin,
and glucose the tie predicate in the canonical SQL is literally
`ABS(<max> - center) = ABS(<max> - center)`, which is tautological for a
non-null max; this apparent source typo is part of the behavior to preserve.
If the preceding greater-than/less-than branches are not selected, the later
score comparison therefore controls the result. The creatinine selector uses
the max under ARF, otherwise the same furthest-from-1/tie-worse-score logic.

### Interaction scores

- Urine output: NULL -> NULL; `< 400 -> 15`; `< 600 -> 8`; `< 900 -> 7`;
  `< 1500 -> 5`; `< 2000 -> 4`; `< 4000 -> 0`; `>= 4000 -> 1`.
- GCS: if `gcs_unable = 1`, score `0`. If `gcs_eyes = 1`, the exact
  `gcs_verbal`/`gcs_motor` combinations are:
  - `gcs_verbal = 1` and motor `IN (1, 2) -> 48`, `IN (3, 4) -> 33`,
    `IN (5, 6) -> 16`;
  - verbal `IN (2, 3)` and motor `IN (1, 2) -> 29`, `IN (3, 4) -> 24`,
    motor `>= 5 -> NULL`;
  - verbal `>= 4 -> NULL`.
  If `gcs_eyes > 1`, the exact combinations are:
  - verbal `= 1`: motor `IN (1, 2) -> 29`, `IN (3, 4) -> 24`, `IN (5, 6) -> 15`;
  - verbal `IN (2, 3)`: motor `IN (1, 2) -> 29`, `IN (3, 4) -> 24`,
    `= 5 -> 13`, `= 6 -> 10`;
  - verbal `= 4`: motor `IN (1, 2, 3, 4) -> 13`, `= 5 -> 8`, `= 6 -> 3`;
  - verbal `= 5`: motor `IN (1, 2, 3, 4, 5) -> 3`, `= 6 -> 0`.
  All unmatched combinations and the final `ELSE` are NULL.
- Oxygenation: if both `pao2` and `aado2` are NULL, NULL. If `pao2` is
  non-null it takes precedence over `aado2`: `< 50 -> 15`; `< 70 -> 5`;
  `< 80 -> 2`; otherwise `0`. Only when PaO2 is NULL does the A-aDO2 branch
  apply: `< 100 -> 0`; `< 250 -> 7`; `< 350 -> 9`; `< 500 -> 11`;
  `>= 500 -> 14`; the CASE's final fallback is `0`.

## 5. Aggregations and windows

Directly in `apsiii.sql`:

- `pa`: `ROW_NUMBER() OVER (PARTITION BY ie.stay_id ORDER BY bg.po2 DESC)`.
- `aa`: `ROW_NUMBER() OVER (PARTITION BY ie.stay_id ORDER BY bg.aado2 DESC)`.
- `acidbase_max`: `ROW_NUMBER() OVER (PARTITION BY stay_id ORDER BY acidbase_score DESC)`.
- `arf`'s inline ICD aggregate: `MAX(CASE ... END)` with `GROUP BY hadm_id`.
- `vent`: `MAX(CASE WHEN v.stay_id IS NOT NULL THEN 1 ELSE 0 END)` with
  `GROUP BY ie.stay_id`.

There are no explicit `AVG`, `MIN`, or `MAX` vital/lab aggregations in this
SQL; those extrema are consumed from `first_day_lab` and
`first_day_vitalsign`, and urine total from `first_day_urine_output`. The
dependency boundaries therefore include their already-computed aggregation
semantics. The three local row-number windows have no secondary tie-breaker;
equal values can therefore make the selected `charttime`/row nondeterministic,
although the selected value itself is equal for the ranking field.

## 6. Null behavior and derived-score composition

- The blood-gas and dependency joins are left-preserving at the cohort level.
  Missing qualifying PaO2, A-aDO2, acid-base, lab, vital, urine, GCS, or
  ventilation data leaves the corresponding cohort fields NULL rather than
  removing the stay.
- `pa` uses a default FiO2 of `21` only for the non-ventilated PaO2 branch;
  `aa` does not default missing FiO2, so a NULL coalesced FiO2 fails its
  `>= 50` predicate.
- `arf` explicitly returns `0` when its renal/dialysis conditions are not all
  true, including missing `icd.ckd`, missing creatinine, or missing urine
  output. It is not NULL merely because its inputs are NULL.
- Every min/max score CASE returns NULL for a NULL source value. The selected
  `scorecomp` component can consequently be NULL. Some selectors also become
  NULL when their max is present but the required min is NULL and all distance
  comparisons evaluate UNKNOWN; reproduce the CASE semantics rather than
  imputing a side.
- `cohort.glucose_min/max` has explicit two-source NULL handling, selecting a
  non-null lab or vital value and choosing the lab on equality.
- `uo_score`, `gcs_score`, and `pao2_aado2_score` are NULL when their special
  interaction inputs do not match a branch.
- `score.apsiii` coalesces every one of the sixteen component scores to zero
  before summing. Missing data therefore contributes a normal score of zero
  to `apsiii`, while the individual final component columns remain NULL.
- `apsiii_prob` is computed from `apsiii`; it is NULL when the final score-side
  row or `apsiii` is NULL. With a normal score-side row, the all-NULL component
  case still produces a numeric APS III of zero because of the COALESCEs.
- The final left join preserves all base ICU-stay rows. If a score row does not
  match, all score and probability columns are NULL while the three final
  identifiers remain populated from `ie`.

## 7. Literal code specification

The canonical APS III SQL contains no direct `itemid` filter. Its itemid
selection is encapsulated in the already-dependent `bg` and first-day views;
those dependency code sets are not to be expanded or rederived in this
consumer. The coded literals that **this SQL itself** names are:

| source table/derived stream | exact SQL literals and predicate | feeds |
|---|---|---|
| `mimiciv_derived.ventilation` | `vd.ventilation_status = 'InvasiveVent'` in `pa` | excludes invasive-ventilation intervals from the non-ventilated `pa.pao2` branch |
| `mimiciv_derived.ventilation` | `vd.ventilation_status = 'InvasiveVent'` in `aa` | selects the ventilated `aa.aado2` branch |
| `mimiciv_derived.ventilation` | `v.ventilation_status = 'InvasiveVent'` in `vent` | produces `vent.vent`, which changes the low respiratory-rate score branch |
| `mimiciv_derived.bg` | `bg.specimen = 'ART.'` in `pa` | `pa.pao2` |
| `mimiciv_derived.bg` | `bg.specimen = 'ART.'` in `aa` | `aa.aado2` |
| `mimiciv_derived.bg` | `bg.specimen = 'ART.'` in `acidbase` | `acidbase.ph`, `acidbase.paco2`, and `acidbase_score` |
| `mimiciv_hosp.diagnoses_icd` | `icd_version = 9` with `SUBSTR(icd_code, 1, 4) IN ('5854', '5855', '5856')` | inline `icd.ckd = 1`, then `arf`, then creatinine scoring |
| `mimiciv_hosp.diagnoses_icd` | `icd_version = 10` with `SUBSTR(icd_code, 1, 4) IN ('N184', 'N185', 'N186')` | inline `icd.ckd = 1`, then `arf`, then creatinine scoring |

The diagnosis code systems represented are the SQL's `icd_version = 9` and
`icd_version = 10` branches (ICD-9 and ICD-10 diagnosis codes); the SQL uses
the four-character prefixes exactly as shown. `5859` is mentioned only in a
comment as deliberately excluded and is not part of the code set. The
`'InvasiveVent'` and `'ART.'` literals are categorical values in derived
streams, not ICD or itemid codes.

The numeric GCS sets (`IN (1, 2)`, `IN (3, 4)`, `IN (5, 6)`,
`IN (2, 3)`, and the other exact values listed above) are component-value
discriminators, not source itemid/code-system filters; they nevertheless feed
`gcs_score` and must be preserved literally. The `1`/`0` flags for `ckd`,
`arf`, `vent`, and `gcs_unable` likewise are SQL discriminator values, not
terminology mappings.

For avoidance of ambiguity, itemids such as `50807` are not named by
`apsiii.sql`; `50807` is a literal in the separate `bg.sql` dependency, where
it is present-in-SQL and expected-absent-in-data in MIMIC-IV 2.2. It is
therefore not an APS III consumer filter or a second APS III code-set entry;
the `bg` dependency's own analysis/probe owns that dead-filter confirmation.

## 8. Semantically essential inputs and dependency trace

The following inputs can change row inclusion, row identity, a temporal
selection, a grouping/aggregate, or a clinically meaningful APS III output:

1. **ICU identity and existence:** `icustays.subject_id`, `hadm_id`, and
   `stay_id` define the output identity and the per-stay joins. `intime` and
   `outtime` control all direct blood-gas inclusion windows. The inner joins to
   `admissions.hadm_id` and `patients.subject_id` control cohort row
   inclusion. `stay_id` is the semantic grain and final comparison key.
2. **Blood-gas temporal and arterial selection:** `bg.hadm_id` links a gas to
   an ICU stay; `bg.charttime` controls ICU-window inclusion, ventilation
   interval matching, and the retained ranked row. `bg.specimen` controls
   arterial eligibility. `bg.po2` controls PaO2 eligibility, ranking, and
   oxygenation scoring. `bg.aado2` controls the ventilated A-aDO2 branch,
   ranking, and fallback oxygenation scoring. `bg.ph` and `bg.pco2` jointly
   control acid-base row eligibility, ranking, and `acidbase_score`.
3. **Ventilation state:** `ventilation.stay_id`, `starttime`, `endtime`, and
   `ventilation_status` control whether a blood gas is in the non-ventilated
   PaO2 branch, the ventilated high-FiO2 A-aDO2 branch, and whether the first
   day `vent` flag changes the respiratory-rate score. `fio2` and
   `fio2_chartevents` control the branch split and the FiO2 threshold, with
   the distinct default behavior described above.
4. **Renal/CKD interaction:** `first_day_lab.creatinine_max` and
   `first_day_urine_output.urineoutput` control `arf`; the diagnosis
   `icd_code`, `icd_version`, and `hadm_id` control `ckd` and thereby the ARF
   creatinine scoring branch. All of `creatinine_min/max` then affect the
   creatinine score, with ARF forcing use of the maximum score.
5. **First-day physiological extrema:** the min/max columns consumed from
   `first_day_vitalsign` and `first_day_lab` each feed the corresponding CASE
   lookup and worst-value selection. This includes heart rate, MBP,
   temperature, respiratory rate, hematocrit, WBC, creatinine, BUN, sodium,
   albumin, bilirubin, and the merged glucose extrema. Any change can alter an
   individual score and/or the total `apsiii` and `apsiii_prob`.
6. **Glucose merge inputs:** both lab and vital `glucose_min/max` are
   essential because the source selects the cross-source minimum/maximum,
   with explicit NULL and equality behavior.
7. **GCS interaction inputs:** `gcs_unable`, `gcs_eyes`, `gcs_verbal`, and
   `gcs_motor` select mutually different branches and scores. `gcs_min` is
   selected into `mingcs` but is not used downstream by this SQL; the four
   component/discriminator columns are the essential GCS inputs for APS III.
8. **Dependency aggregation boundaries:** `bg`, `first_day_gcs`,
   `first_day_lab`, `first_day_urine_output`, `first_day_vitalsign`, and
   `ventilation` are semantically essential tables, not optional conveniences.
   Their outputs already encode source-side itemid pivots, first-day time
   windows, extrema, urine totals, GCS selection, and ventilation interval
   construction. A candidate must join their completed outputs by the listed
   `stay_id`/admission keys and preserve NULLs; rederiving from FHIR resources
   would change the dependency contract.

The source comments say the score is intended for the first ICU day, but the
local blood-gas CTEs use the full `[intime, outtime)` ICU stay window. The
first-day physiological values come from dependencies whose own windows are
first-day windows. This distinction is part of the canonical SQL and is
essential: do not narrow `pa`, `aa`, or `acidbase` to 24 hours merely from the
commentary.

## Evidence block

Concept: `apsiii`. Read `mimic-iv/concepts/score/apsiii.sql` in full; read the
`apsiii` node, dependency edges, level, path, and SHA256 in
`mimic-iv/concept_dag/concept_dag.json`; checked the SQL hash against the DAG;
read the relevant output shape/key in
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`; read the loop
contract and current MIMIC-on-FHIR notes; and read the six dependency SQL
definitions needed to identify the exact consumer columns and their temporal
aggregation boundaries. Findings cover all `mimiciv_icu`, `mimiciv_hosp`, and
`mimiciv_derived` references, join types and predicates, WHERE predicates,
windows, aggregates, null behavior, literal ventilation/specimen and ICD-9 /
ICD-10 code sets, intermediate columns, final types, one-row-per-`stay_id`
grain, and essential inputs. The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/apsiii/source-analyst.md`; no ViewDefinition
or `concept.sql` was authored and no SQL was run.
