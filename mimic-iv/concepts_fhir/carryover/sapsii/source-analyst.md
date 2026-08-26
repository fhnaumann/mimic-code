# Source analysis: `sapsii`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/score/sapsii.sql` (549 lines).
- DAG node: `sapsii`, path `score/sapsii.sql`, level `2`, SHA256
  `a7f474712fd8e8e68b7293d1e70e7f42b19fe2712c9c8a8b14149a20a1f52df7`.
- DAG dependencies, in the DAG order: `age`, `bg`, `chemistry`,
  `complete_blood_count`, `enzyme`, `gcs`, `urine_output`, `ventilation`,
  `vitalsign`. The node has no dependents.
- The candidate must preserve these `mimiciv_derived` dependency boundaries;
  the dependency stems are the unqualified candidate SQL table names.

## Natural grain and time semantics

The intended natural grain is one row per ICU stay, identified by
`stay_id`, with `subject_id` and `hadm_id` retained. The `co` CTE defines the
first-day window as:

- `starttime = icustays.intime`;
- `endtime = DATETIME_ADD(intime, INTERVAL '24' HOUR)`;
- most source joins use the half-open-on-the-left, closed-on-the-right
  condition `starttime < event_time AND event_time <= endtime` (or its
  equivalent `endtime >= event_time`).

The final manifest confirms a keyed comparison on `stay_id` and 73,181 oracle
rows. `encounter_key`, `icu_encounter_key`, and `patient_key` are candidate
FHIR resource-key columns required by the manifest, but are not columns in the
canonical SQL output; the source natural key remains `stay_id`.

The `cpap` CTE first selects qualifying chart events inside the first-day
window, then expands the resulting interval by one hour before the earliest
chart time and four hours after the latest chart time, clipping both ends to
the first-day window. `pafi2` keeps only blood-gas rows that overlap either an
invasive ventilation interval or the CPAP interval and takes the minimum ratio.

## Table references

### Raw `mimiciv_hosp` / `mimiciv_icu` tables

The source SQL uses BigQuery-style `physionet-data.mimiciv_*` qualification;
the schemas and table names are the following:

| Source schema | Table | CTE/use |
|---|---|---|
| `mimiciv_icu` | `icustays` | `co`; also the final `cohort` spine as `ie` |
| `mimiciv_icu` | `chartevents` | `cpap` as `ce` |
| `mimiciv_hosp` | `admissions` | `surgflag` as `adm`; final `cohort` as `adm` |
| `mimiciv_hosp` | `services` | `surgflag` as `se` |
| `mimiciv_hosp` | `diagnoses_icd` | `comorb` |

No `d_items` or other dimension table is referenced.

### `mimiciv_derived` tables

These are direct DAG dependencies, not raw tables:

| Dependency table | Exact consumer columns read | Consumer use |
|---|---|---|
| `mimiciv_derived.age` | `hadm_id`, `age` | Join by admission and compute `age_score` |
| `mimiciv_derived.bg` | `subject_id`, `charttime`, `specimen`, `pao2fio2ratio` | First-day arterial blood-gas rows, ventilation/CPAP overlap, and `pao2fio2_vent_min` |
| `mimiciv_derived.chemistry` | `subject_id`, `charttime`, `bun`, `potassium`, `sodium`, `bicarbonate` | First-day extrema and four laboratory score components |
| `mimiciv_derived.complete_blood_count` | `subject_id`, `charttime`, `wbc` | First-day WBC extrema and `wbc_score` |
| `mimiciv_derived.enzyme` | `subject_id`, `charttime`, `bilirubin_total` | First-day bilirubin extrema and `bilirubin_score` |
| `mimiciv_derived.gcs` | `stay_id`, `charttime`, `gcs` | First-day minimum GCS and `gcs_score` |
| `mimiciv_derived.urine_output` | `stay_id`, `charttime`, `urineoutput` | First-day sum and `uo_score` |
| `mimiciv_derived.ventilation` | `stay_id`, `starttime`, `endtime`, `ventilation_status` | Overlap discriminator for invasive ventilation in `pafi1` |
| `mimiciv_derived.vitalsign` | `subject_id`, `charttime`, `heart_rate`, `sbp`, `temperature` | First-day vital-sign extrema and three score components |

The candidate consumer must use `FROM age`, `FROM bg`, `FROM chemistry`,
`FROM complete_blood_count`, `FROM enzyme`, `FROM gcs`, `FROM urine_output`,
`FROM ventilation`, and `FROM vitalsign` after preprocessing, rather than
rederiving these values from FHIR resources.

### CTE references

For completeness, every CTE-to-CTE `FROM`/`JOIN` is:

- `cpap`: `FROM co`; `INNER JOIN chartevents`.
- `surgflag`: raw `admissions`; `LEFT JOIN services`.
- `pafi1`: `FROM co`; `LEFT JOIN bg`, `LEFT JOIN ventilation`, and `LEFT JOIN cpap`.
- `pafi2`: `FROM pafi1`.
- `gcs`: `FROM co`; `LEFT JOIN gcs` (the derived table).
- `vital`: `FROM co`; `LEFT JOIN vitalsign`.
- `uo`: `FROM co`; `LEFT JOIN urine_output`.
- `labs`: `FROM co`; `LEFT JOIN chemistry`.
- `cbc`: `FROM co`; `LEFT JOIN complete_blood_count`.
- `enz`: `FROM co`; `LEFT JOIN enzyme`.
- `cohort`: raw `icustays` plus `INNER JOIN admissions`, `LEFT JOIN age`,
  `INNER JOIN co`, and `LEFT JOIN` to `pafi2`, `surgflag`, `comorb`, `gcs`,
  `vital`, `uo`, `labs`, `cbc`, and `enz`.
- `scorecomp`: `FROM cohort`.
- `score`: `FROM scorecomp`.
- final query: `FROM score`.

## Joins and join predicates

All raw and derived joins are listed here, including their temporal and value
predicates.

1. `cpap` `INNER JOIN mimiciv_icu.chartevents ce` on
   `co.stay_id = ce.stay_id`, `ce.charttime > co.starttime`, and
   `ce.charttime <= co.endtime`. Its `WHERE` additionally requires the exact
   item/value predicates documented below. This inner join means a stay has no
   `cpap` aggregate row unless it has a matching item 226732 event.
2. `surgflag` `LEFT JOIN mimiciv_hosp.services se` on
   `adm.hadm_id = se.hadm_id`. The left join retains admissions with no
   service row; `ROW_NUMBER()` later selects their first service row (with
   null service) as `serviceorder = 1`.
3. `pafi1` `LEFT JOIN mimiciv_derived.bg bg` on
   `co.subject_id = bg.subject_id`, `bg.specimen = 'ART.'`,
   `bg.charttime > co.starttime`, and `bg.charttime <= co.endtime`.
4. `pafi1` `LEFT JOIN mimiciv_derived.ventilation vd` on
   `co.stay_id = vd.stay_id`, `bg.charttime > vd.starttime`,
   `bg.charttime <= vd.endtime`, and
   `vd.ventilation_status = 'InvasiveVent'`. Because this is a left join,
   `vent` is explicitly set to 0 when no qualifying interval exists.
5. `pafi1` `LEFT JOIN cpap cp` on `bg.subject_id = cp.subject_id`,
   `bg.charttime > cp.starttime`, and `bg.charttime <= cp.endtime`.
   `cpap` is explicitly set to 0 when no qualifying CPAP interval exists.
6. `gcs` `LEFT JOIN mimiciv_derived.gcs gcs` on
   `co.stay_id = gcs.stay_id`, `co.starttime < gcs.charttime`, and
   `gcs.charttime <= co.endtime`.
7. `vital` `LEFT JOIN mimiciv_derived.vitalsign vital` on
   `co.subject_id = vital.subject_id`, `co.starttime < vital.charttime`,
   and `co.endtime >= vital.charttime`.
8. `uo` `LEFT JOIN mimiciv_derived.urine_output uo` on
   `co.stay_id = uo.stay_id`, `co.starttime < uo.charttime`, and
   `co.endtime >= uo.charttime`.
9. `labs` `LEFT JOIN mimiciv_derived.chemistry labs` on
   `co.subject_id = labs.subject_id`, `co.starttime < labs.charttime`, and
   `co.endtime >= labs.charttime`.
10. `cbc` `LEFT JOIN mimiciv_derived.complete_blood_count cbc` on
    `co.subject_id = cbc.subject_id`, `co.starttime < cbc.charttime`, and
    `co.endtime >= cbc.charttime`.
11. `enz` `LEFT JOIN mimiciv_derived.enzyme enz` on
    `co.subject_id = enz.subject_id`, `co.starttime < enz.charttime`, and
    `co.endtime >= enz.charttime`.
12. In `cohort`, raw `icustays ie` `INNER JOIN mimiciv_hosp.admissions adm` on
    `ie.hadm_id = adm.hadm_id`; `LEFT JOIN mimiciv_derived.age va` on
    `ie.hadm_id = va.hadm_id`; and `INNER JOIN co` on
    `ie.stay_id = co.stay_id`.
13. In `cohort`, the aggregate/flag CTEs are all left joined: `pafi2 pf` on
    `ie.stay_id = pf.stay_id`; `surgflag sf` on
    `adm.hadm_id = sf.hadm_id AND sf.serviceorder = 1`; `comorb` on
    `ie.hadm_id = comorb.hadm_id`; and each of `gcs`, `vital`, `uo`, `labs`,
    `cbc`, and `enz` on `ie.stay_id = <cte>.stay_id`.

The two inner joins in `cohort` are row-inclusion predicates: an ICU stay
without a matching hospital admission or `co` row is not emitted. All
measurement joins after the ICU-stay spine are left joins, so missing data
becomes null aggregates rather than removing the stay.

## Source columns and inferred types by CTE

The raw table types below follow the MIMIC-IV DDL (`INTEGER`, `SMALLINT`,
`TIMESTAMP`, `FLOAT`, and `VARCHAR`). Derived measurement columns retain their
numeric or timestamp/string types through the dependency boundary; aggregate
`MIN`/`MAX`/`SUM` results retain the corresponding numeric family.

### `co`

- `subject_id`: `INTEGER`; selected from `icustays`.
- `hadm_id`: `INTEGER`; selected from `icustays`.
- `stay_id`: `INTEGER`; selected from `icustays` and the CTE join key.
- `intime`: `TIMESTAMP`; renamed to `starttime` in this CTE.
- `starttime`: `TIMESTAMP`; the ICU admission time.
- `endtime`: `TIMESTAMP`; `DATETIME_ADD(intime, INTERVAL '24' HOUR)`.

### `cpap`

Read from `co` plus raw `chartevents` columns `stay_id` (`INTEGER`),
`charttime` (`TIMESTAMP`), `itemid` (`INTEGER`), and `value` (`VARCHAR`). It
outputs:

- `subject_id`, `stay_id`: `INTEGER` grouping/identity columns;
- `starttime`, `endtime`: `TIMESTAMP`, clipped aggregate interval;
- `cpap`: nullable-looking but effectively integer `0/1`, from `MAX(CASE ...)`.

### `surgflag`

Reads `admissions.hadm_id` (`INTEGER`), `services.hadm_id` (`INTEGER`),
`services.curr_service` (`VARCHAR`), and `services.transfertime`
(`TIMESTAMP`). It outputs `hadm_id` (`INTEGER`), `surgical` (`INTEGER 0/1`),
and `serviceorder` (`ROW_NUMBER`, integer/bigint window result).

### `comorb`

Reads `diagnoses_icd.hadm_id` (`INTEGER`), `icd_code` (`CHAR/VARCHAR`), and
`icd_version` (`SMALLINT`). It outputs one row per `hadm_id` and integer flags
`aids`, `hem`, and `mets`, each from a `MAX(CASE ...)`.

### `pafi1` and `pafi2`

`pafi1` reads `co.stay_id` (`INTEGER`), derived `bg.subject_id` (`INTEGER`),
`bg.charttime` (`TIMESTAMP`), `bg.specimen` (`VARCHAR`),
`bg.pao2fio2ratio` (numeric/`FLOAT`), derived ventilation
`stay_id` (`INTEGER`), `starttime`/`endtime` (`TIMESTAMP`),
`ventilation_status` (`VARCHAR`), and `cp.subject_id` (`INTEGER`). It outputs
`stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`), `pao2fio2` (numeric/`FLOAT`),
and integer flags `vent` and `cpap`.

`pafi2` outputs one row per `stay_id` (`INTEGER`) and
`pao2fio2_vent_min` (numeric/`FLOAT`), the `MIN(pao2fio2)` among rows with
`vent = 1 OR cpap = 1`.

### `gcs`, `vital`, `uo`, `labs`, `cbc`, and `enz`

- `gcs` reads `co.stay_id` (`INTEGER`) and dependency `stay_id` (`INTEGER`),
  `charttime` (`TIMESTAMP`), and `gcs` (numeric/integer); outputs `stay_id`
  and `mingcs` (numeric/integer) from `MIN`.
- `vital` reads dependency `subject_id` (`INTEGER`), `charttime`
  (`TIMESTAMP`), `heart_rate`, `sbp`, and `temperature` (numeric/`FLOAT`);
  outputs `stay_id` and `heartrate_min`, `heartrate_max`, `sysbp_min`,
  `sysbp_max`, `tempc_min`, and `tempc_max` (numeric/`FLOAT`).
- `uo` reads dependency `stay_id` (`INTEGER`), `charttime` (`TIMESTAMP`), and
  `urineoutput` (numeric/`FLOAT`); outputs `stay_id` and `urineoutput`
  (numeric/`FLOAT`) from `SUM`.
- `labs` reads dependency `subject_id` (`INTEGER`), `charttime` (`TIMESTAMP`),
  and `bun`, `potassium`, `sodium`, `bicarbonate` (numeric/`FLOAT`); outputs
  `stay_id` plus each of their `_min` and `_max` numeric/`FLOAT` aggregates.
- `cbc` reads dependency `subject_id` (`INTEGER`), `charttime` (`TIMESTAMP`),
  and `wbc` (numeric/`FLOAT`); outputs `stay_id`, `wbc_min`, and `wbc_max`
  (numeric/`FLOAT`).
- `enz` reads dependency `subject_id` (`INTEGER`), `charttime` (`TIMESTAMP`),
  and `bilirubin_total` (numeric/`FLOAT`); outputs `stay_id`,
  `bilirubin_min`, and `bilirubin_max` (numeric/`FLOAT`).

### `cohort`

`cohort` selects the ICU-stay spine and all aggregate/flag results:

- `subject_id`, `hadm_id`, `stay_id`: `INTEGER`;
- `intime`, `outtime`, `starttime`, `endtime`: `TIMESTAMP`;
- `age`: numeric/integer from `age`;
- `heartrate_max`, `heartrate_min`, `sysbp_max`, `sysbp_min`,
  `tempc_max`, `tempc_min`, `pao2fio2_vent_min`, `urineoutput`,
  `bun_min`, `bun_max`, `wbc_min`, `wbc_max`, `potassium_min`,
  `potassium_max`, `sodium_min`, `sodium_max`, `bicarbonate_min`,
  `bicarbonate_max`, `bilirubin_min`, `bilirubin_max`, and `mingcs`: nullable
  numeric/`FLOAT`-family values (with integer-like `mingcs` where supplied by
  the dependency);
- `aids`, `hem`, `mets`: integer comorbidity flags;
- `admissiontype`: `VARCHAR`, with values `ScheduledSurgical`,
  `UnscheduledSurgical`, or `Medical` for the normal branches.

`ie.outtime` is selected into this intermediate CTE but is not referenced by
any later score branch and is not in the final projection.

### `scorecomp` and `score`

`scorecomp` carries `cohort.*` and adds the following nullable integer score
columns: `age_score`, `hr_score`, `sysbp_score`, `temp_score`,
`pao2fio2_score`, `uo_score`, `bun_score`, `wbc_score`, `potassium_score`,
`sodium_score`, `bicarbonate_score`, `bilirubin_score`, `gcs_score`,
`comorbidity_score`, and `admissiontype_score`.

`score` carries `scorecomp.*` and adds `sapsii`, an integer sum of the fifteen
component scores after `COALESCE(component, 0)`. The final probability is a
`DOUBLE`/`FLOAT64` expression.

## Filters, value constraints, and branch logic

### Explicit `WHERE` predicates

There are two explicit `WHERE` clauses:

1. In `cpap` (lines 53–54):
   `ce.itemid = 226732` and
   `REGEXP_CONTAINS(LOWER(ce.value), '(cpap mask|bipap)')`.
2. In `pafi2` (lines 198–199): `vent = 1 OR cpap = 1`.

The other row-inclusion conditions are in join `ON` clauses and are listed in
the joins section, especially the first-day time windows, `bg.specimen`, and
`ventilation_status`.

### Score value constraints

These are not source-row `WHERE` filters; they are the exact `CASE` branch
constraints controlling the derived component output columns:

- `age_score`: null if `age IS NULL`; 0 for `age < 40`; 7 for `age < 60`; 12
  for `age < 70`; 15 for `age < 75`; 16 for `age < 80`; 18 for `age >= 80`.
- `hr_score`: null if `heartrate_max IS NULL`; 11 if `heartrate_min < 40`; 7
  if `heartrate_max >= 160`; 4 if `heartrate_max >= 120`; 2 if
  `heartrate_min < 70`; otherwise 0 only when both min and max are in
  `[70, 120)`.
- `sysbp_score`: null if `sysbp_min IS NULL`; 13 if `sysbp_min < 70`; 5 if
  `sysbp_min < 100`; 2 if `sysbp_max >= 200`; otherwise 0 only when both min
  and max are in `[100, 200)`.
- `temp_score`: null if `tempc_max IS NULL`; 3 if `tempc_max >= 39.0`; 0 if
  `tempc_min < 39.0`.
- `pao2fio2_score`: null if `pao2fio2_vent_min IS NULL`; 11 if `< 100`; 9 if
  `< 200`; 6 if `>= 200`.
- `uo_score`: null if `urineoutput IS NULL`; 11 if `< 500.0`; 4 if `<
  1000.0`; 0 if `>= 1000.0`.
- `bun_score`: null if `bun_max IS NULL`; 0 if `< 28.0`; 6 if `< 84.0`; 10
  if `>= 84.0`.
- `wbc_score`: null if `wbc_max IS NULL`; 12 if `wbc_min < 1.0`; 3 if
  `wbc_max >= 20.0`; otherwise 0 only when both min and max are in `[1, 20)`.
- `potassium_score`: null if `potassium_max IS NULL`; 3 if
  `potassium_min < 3.0`; 3 if `potassium_max >= 5.0`; otherwise 0 only when
  both min and max are in `[3, 5)`.
- `sodium_score`: null if `sodium_max IS NULL`; 5 if `sodium_min < 125`; 1 if
  `sodium_max >= 145`; otherwise 0 only when both min and max are in
  `[125, 145)`.
- `bicarbonate_score`: null if `bicarbonate_max IS NULL`; 6 if
  `bicarbonate_min < 15.0`; 3 if `bicarbonate_min < 20.0`; otherwise 0 when
  `bicarbonate_max >= 20.0 AND bicarbonate_min >= 20.0`.
- `bilirubin_score`: null if `bilirubin_max IS NULL`; 0 if `< 4.0`; 4 if `<
  6.0`; 9 if `>= 6.0`.
- `gcs_score`: null if `mingcs IS NULL`; null again for `mingcs < 3` (the SQL
  comment calls this erroneous/on-trach); 26 if `< 6`; 13 if `< 9`; 7 if `<
  11`; 5 if `< 14`; 0 when `mingcs >= 14 AND mingcs <= 15`.
- `comorbidity_score`: 17 when `aids = 1`, otherwise 10 when `hem = 1`,
  otherwise 9 when `mets = 1`, otherwise 0. This is priority-ordered.
- `admissiontype_score`: 0 for `ScheduledSurgical`, 6 for `Medical`, 8 for
  `UnscheduledSurgical`, and null for any other value.

All fifteen component scores are added with `COALESCE(score, 0)`. Thus missing
measurement data produces a null component column but contributes zero to the
total. The probability is exactly:

```sql
1 / (
  1 + EXP(-(-7.7631 + 0.0737 * (sapsii) + 0.9971 * (LN(sapsii + 1))))
)
```

## Literal code and enumerated-value specification (verbatim)

This is the complete coded/value set named by the SQL. No code translation or
expansion is implied.

### Item/value and dependency discriminators

| Source table/column | Exact SQL literal/predicate | Feeds |
|---|---|---|
| `mimiciv_icu.chartevents.itemid` | `ce.itemid = 226732` | `cpap` CTE; CPAP flag used by `pafi1`/`pafi2` and ultimately `pao2fio2_score` |
| `mimiciv_icu.chartevents.value` | `REGEXP_CONTAINS(LOWER(ce.value), '(cpap mask|bipap)')` | `cpap` CTE and its interval/flag |
| `mimiciv_derived.bg.specimen` | `bg.specimen = 'ART.'` | `pafi1` arterial-blood-gas rows, then `pao2fio2_vent_min`/`pao2fio2_score` |
| `mimiciv_derived.ventilation.ventilation_status` | `vd.ventilation_status = 'InvasiveVent'` | `pafi1.vent`, `pafi2`, `pao2fio2_vent_min`, `pao2fio2_score` |
| `mimiciv_hosp.services.curr_service` | `LOWER(curr_service) LIKE '%surg%'` | `surgflag.surgical`, then `admissiontype` and `admissiontype_score` |
| `mimiciv_hosp.admissions.admission_type` | `adm.admission_type = 'ELECTIVE'` | `admissiontype = 'ScheduledSurgical'` when surgical |
| `mimiciv_hosp.admissions.admission_type` | `adm.admission_type != 'ELECTIVE'` | `admissiontype = 'UnscheduledSurgical'` when surgical |

The `itemid` set is from the ICU chartevents item coding (the MIMIC
chartevents d-items system in the FHIR representation). `ART.` and
`InvasiveVent` are exact dependency discriminator values; the SQL does not
name a broader set. No dead itemid/code filter is identified in this SQL.

### ICD code sets, verbatim

All of these predicates filter `mimiciv_hosp.diagnoses_icd.icd_code` together
with the stated `icd_version`. Each set feeds the indicated one-admission
`comorb` flag, which then feeds `comorbidity_score`.

#### `comorb.aids`

- `icd_version = 9 AND SUBSTR(icd_code, 1, 3) BETWEEN '042' AND '044'`.
- `icd_version = 10 AND SUBSTR(icd_code, 1, 3) BETWEEN 'B20' AND 'B22'`.
- `icd_version = 10 AND SUBSTR(icd_code, 1, 3) = 'B24'`.

#### `comorb.hem`

For `icd_version = 9`:

- `SUBSTR(icd_code, 1, 5) BETWEEN '20000' AND '20238'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20240' AND '20248'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20250' AND '20302'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20310' AND '20312'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20302' AND '20382'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20400' AND '20522'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20580' AND '20702'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20720' AND '20892'`.
- `SUBSTR(icd_code, 1, 4) IN ('2386', '2733')`.

For `icd_version = 10`:

- `SUBSTR(icd_code, 1, 3) BETWEEN 'C81' AND 'C96'`.

#### `comorb.mets`

For `icd_version = 9`:

- `SUBSTR(icd_code, 1, 4) BETWEEN '1960' AND '1991'`.
- `SUBSTR(icd_code, 1, 5) BETWEEN '20970' AND '20975'`.
- `SUBSTR(icd_code, 1, 5) IN ('20979', '78951')`.

For `icd_version = 10`:

- `SUBSTR(icd_code, 1, 3) BETWEEN 'C77' AND 'C79'`.
- `SUBSTR(icd_code, 1, 4) = 'C800'`.

There is no diagnosis `WHERE` clause: these exact ICD predicates occur inside
the `MAX(CASE ...)` expressions in `comorb`, so nonmatching diagnosis rows
remain in the grouped input and yield flag value 0 when no matching code is
present.

## Aggregations and windows

- `cpap`: `MIN(DATETIME_SUB(charttime, INTERVAL '1' HOUR))`,
  `MAX(DATETIME_ADD(charttime, INTERVAL '4' HOUR))`, `MAX(CASE ...)`,
  grouped by `co.subject_id`, `co.stay_id`, `co.starttime`, and `co.endtime`.
- `surgflag`: `ROW_NUMBER() OVER (PARTITION BY adm.hadm_id ORDER BY
  transfertime)`; `sf.serviceorder = 1` selects the first service.
- `comorb`: three `MAX(CASE ...)` flag aggregations, grouped by `hadm_id`.
- `pafi2`: `MIN(pao2fio2)` grouped by `stay_id`, after `vent = 1 OR cpap = 1`.
- `gcs`: `MIN(gcs.gcs)` grouped by `co.stay_id`.
- `vital`: `MIN`/`MAX` of heart rate, SBP, and temperature grouped by
  `co.stay_id`.
- `uo`: `SUM(uo.urineoutput)` grouped by `co.stay_id`.
- `labs`: `MIN`/`MAX` of BUN, potassium, sodium, and bicarbonate grouped by
  `co.stay_id`.
- `cbc`: `MIN`/`MAX` of WBC grouped by `co.stay_id`.
- `enz`: `MIN`/`MAX` of total bilirubin grouped by `co.stay_id`.
- There are no `GROUP BY` or window operations in `cohort`, `scorecomp`,
  `score`, or the final projection. `score` uses scalar `COALESCE`, `EXP`, and
  `LN`, not an aggregate.

## Final output schema

The final `SELECT` explicitly projects only these columns; it does not expose
the `cohort.*` extrema, flags, `age`, `intime`, `outtime`, or `admissiontype`:

| Output column | Inferred/manifest type | Origin |
|---|---|---|
| `subject_id` | `INTEGER` | ICU-stay spine |
| `hadm_id` | `INTEGER` | ICU-stay/admission spine |
| `stay_id` | `INTEGER` | ICU-stay natural key |
| `starttime` | `TIMESTAMP` | `icustays.intime` |
| `endtime` | `TIMESTAMP` | `starttime + 24 hours` |
| `sapsii` | `INTEGER` | Sum of coalesced component scores |
| `sapsii_prob` | `DOUBLE` | SAPS-II logistic formula |
| `age_score` | `INTEGER` | `age` thresholds |
| `hr_score` | `INTEGER` | Heart-rate extrema |
| `sysbp_score` | `INTEGER` | SBP extrema |
| `temp_score` | `INTEGER` | Temperature extrema |
| `pao2fio2_score` | `INTEGER` | Ventilated/CPAP arterial blood-gas ratio |
| `uo_score` | `INTEGER` | Urine-output sum |
| `bun_score` | `INTEGER` | BUN maximum |
| `wbc_score` | `INTEGER` | WBC extrema |
| `potassium_score` | `INTEGER` | Potassium extrema |
| `sodium_score` | `INTEGER` | Sodium extrema |
| `bicarbonate_score` | `INTEGER` | Bicarbonate extrema |
| `bilirubin_score` | `INTEGER` | Total-bilirubin maximum |
| `gcs_score` | `INTEGER` | Minimum GCS |
| `comorbidity_score` | `INTEGER` | ICD-derived AIDS/hematologic malignancy/metastatic cancer flags |
| `admissiontype_score` | `INTEGER` | Admission/surgical classification |

The manifest also requires candidate-only resource keys
`encounter_key`, `icu_encounter_key`, and `patient_key`; those are identity
columns for FHIR joins and are not source SQL values.

## Semantically essential inputs and trace

These are the inputs whose values can alter inclusion, the stay grain, a
grouping/aggregate, a temporal overlap, or a clinically meaningful output.

### Identity, joins, and grain

- `icustays.stay_id` is the natural row identity, every stay-level grouping
  key, the `co`/cohort join key, and a final output column. Losing or changing
  it changes row alignment and the score's stay association.
- `icustays.subject_id` is a final identifier and controls the subject-time
  joins to `bg`, `vitalsign`, `chemistry`, `complete_blood_count`, and
  `enzyme`, plus the CPAP-to-blood-gas subject join.
- `icustays.hadm_id` controls the admission join, the `age` join, diagnosis and
  service association, admission-type classification, and final output.
- `icustays.intime` controls `starttime`, `endtime`, every first-day window,
  CPAP interval clipping, all aggregate membership, and two final time columns.
- `admissions.hadm_id`, `services.hadm_id`, and every dependency identity key
  used in the joins are essential because the joins determine which source
  observations contribute to each stay.

### Temporal and overlap discriminators

- Raw/dependency `charttime` controls first-day inclusion and all min/max/sum
  membership. It also controls the CPAP and ventilation interval overlays.
- `ventilation.starttime`, `ventilation.endtime`, and
  `ventilation_status` determine whether each arterial blood-gas row receives
  `vent = 1` and therefore whether it can contribute to `pafi2`.
- CPAP chart times determine the expanded/clipped CPAP interval; CPAP item/value
  selection determines whether that interval exists at all.
- `services.transfertime` controls `ROW_NUMBER()` and which service is used by
  the surgical classification. `services.curr_service` controls the surgical
  branch.

### Clinical value and branch inputs

- `age.age` controls `age_score` and therefore `sapsii`, `sapsii_prob`, and the
  final score component.
- `bg.pao2fio2ratio` controls the minimum ventilated/CPAP ratio and
  `pao2fio2_score`; `bg.specimen` controls arterial inclusion.
- `gcs.gcs` controls the first-day minimum and `gcs_score`, including the
  special `mingcs < 3` null branch.
- `vitalsign.heart_rate`, `sbp`, and `temperature` control their first-day
  extrema and `hr_score`, `sysbp_score`, and `temp_score`.
- `urine_output.urineoutput` controls the first-day sum and `uo_score`.
- `chemistry.bun`, `potassium`, `sodium`, and `bicarbonate` control their
  extrema and respective score branches.
- `complete_blood_count.wbc` controls WBC extrema and `wbc_score`.
- `enzyme.bilirubin_total` controls bilirubin extrema and `bilirubin_score`.
- `diagnoses_icd.icd_version` plus the exact `icd_code` prefixes/ranges listed
  above control `aids`, `hem`, and `mets`, then the priority-ordered
  `comorbidity_score`.
- `admissions.admission_type` and the first `services.curr_service` result
  control `admissiontype`, then `admissiontype_score`.
- Nullness of every aggregate input is itself semantically relevant: it
  changes whether the corresponding component column is null, and the
  subsequent `COALESCE` explicitly changes its contribution to the total to
  zero. The aggregate value and its nullness must therefore both survive the
  dependency boundary.

The selected `icustays.outtime` is not semantically essential to this SQL: it
is carried in `cohort.*` through intermediate CTEs but is neither used in a
predicate or aggregate nor emitted by the final projection.
