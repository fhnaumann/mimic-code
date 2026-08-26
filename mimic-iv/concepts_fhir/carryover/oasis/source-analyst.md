# OASIS source analysis

## Provenance and DAG position

- Canonical SQL: `mimic-iv/concepts/score/oasis.sql` (287 lines).
- DAG node: `oasis`, authoritative path `score/oasis.sql`, level 2, SHA-256
  `7b5082e8e66df40a95590567ab4dad7ef28e44d4a0be7b921d02186c6616a19e`.
- Direct `mimiciv_derived` dependencies in the DAG, in the names exposed to
  candidate SQL, are `age`, `first_day_gcs`, `first_day_urine_output`,
  `first_day_vitalsign`, and `ventilation`.
- The dependency edges are recorded in
  `mimic-iv/concept_dag/concept_dag.json:968-985`. The dependency node SQLs
  read for this analysis were `demographics/age.sql`,
  `firstday/first_day_gcs.sql`, `firstday/first_day_urine_output.sql`,
  `firstday/first_day_vitalsign.sql`, and `treatment/ventilation.sql`.
  Their transitive source concepts were also checked where their values or
  discriminators control an OASIS input: `measurement/gcs.sql`,
  `measurement/urine_output.sql`, `measurement/vitalsign.sql`,
  `measurement/oxygen_delivery.sql`, and
  `measurement/ventilator_setting.sql`.
 - Read-only contextual material: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`,
   `MIMIC_NOTES.d/README.md`, and the relevant provisional leads
   `MIMIC_NOTES.d/age.md`, `first_day_gcs.md`,
   `first_day_urine_output.md`, `first_day_vitalsign.md`, and
   `ventilation.md`, plus the transitive-source leads `gcs.md`,
   `urine_output.md`, `vitalsign.md`, `oxygen_delivery.md`, and
   `ventilator_setting.md`. The source schema declarations were checked in
  `mimic-iv/buildmimic/postgres/create.sql`, and the exact output schema and
  natural key were checked in
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.

## Grain, key, and row inclusion

The final query is one row per `mimiciv_icu.icustays.stay_id` (the oracle
manifest declares `stay_id` as the keyed comparison column; 73,181 full-data
rows). The base cohort starts from every ICU stay, then uses INNER JOINs to
`admissions` and `patients`, so only stays with a matching hospital admission
and patient survive. All score-input dependency joins are LEFT JOINs. The
`surgflag` and `vent` CTEs aggregate back to one row per stay before joining.
The first-day dependency outputs are also one row per stay. Missing component
inputs do not remove the stay: their component score is NULL and the final
`oasis` sum uses `COALESCE(component_score, 0)`.

The source natural key is therefore `stay_id`, with `subject_id` and `hadm_id`
as identifiers. The FHIR comparator manifest additionally declares
`patient_key`, `encounter_key`, and `icu_encounter_key` as resource-key
columns; those are port bookkeeping keys, not source SQL columns and must be
kept opaque.

## Physical table references and columns

These are every physical `FROM`/`JOIN` reference in the canonical OASIS SQL.
The CTE references are listed separately below.

| schema.table | alias | join/use and referenced columns | source types from `create.sql` |
|---|---|---|---|
| `mimiciv_icu.icustays` | `ie` | base rows; `subject_id`, `hadm_id`, `stay_id`, `intime`, `outtime`; `stay_id` grouping and joins, `hadm_id`/`subject_id` joins, `intime` windows, `outtime` mortality test | `subject_id INTEGER`, `hadm_id INTEGER`, `stay_id INTEGER`, `intime TIMESTAMP`, `outtime TIMESTAMP` |
| `mimiciv_hosp.services` | `se` | `hadm_id`, `transfertime`, `curr_service`; service classification and first-day upper-bound predicate | `hadm_id INTEGER`, `transfertime TIMESTAMP`, `curr_service VARCHAR(10)` |
| `mimiciv_derived.ventilation` | `v` | `stay_id`, `starttime`, `endtime`, `ventilation_status`; invasive-ventilation status and interval overlap | dependency output: `stay_id INTEGER`, `starttime TIMESTAMP`, `endtime TIMESTAMP`, `ventilation_status VARCHAR` |
| `mimiciv_hosp.admissions` | `adm` | `hadm_id`, `admittime`, `deathtime`, `dischtime`, `admission_type`, `discharge_location`, `hospital_expire_flag`; pre-ICU minutes, elective-surgery branch, mortality flags | `hadm_id INTEGER`, `admittime/dischtime/deathtime TIMESTAMP`, `admission_type VARCHAR(40)`, `discharge_location VARCHAR(60)`, `hospital_expire_flag SMALLINT` |
| `mimiciv_hosp.patients` | `pat` | `subject_id` only, for the INNER JOIN existence constraint | `subject_id INTEGER` |
| `mimiciv_derived.age` | `ag` | `hadm_id`, `age`; admission-age dependency join and score/value | dependency output consumer types: `hadm_id INTEGER`, `age BIGINT` |
| `mimiciv_derived.first_day_gcs` | `gcs` | `stay_id`, `gcs_min`; minimum GCS score/value | dependency output consumer types: `stay_id INTEGER`, `gcs_min FLOAT` |
| `mimiciv_derived.first_day_vitalsign` | `vital` | `stay_id`, `heart_rate_max/min`, `mbp_max/min`, `resp_rate_max/min`, `temperature_max/min`; physiologic score/value branches | dependency output consumer types: identifier `stay_id INTEGER`; heart-rate/MAP/respiratory values `DOUBLE`; `temperature_min/max DECIMAL(38,2)` |
| `mimiciv_derived.first_day_urine_output` | `uo` | `stay_id`, `urineoutput`; urine score/value | dependency output consumer types: `stay_id INTEGER`, `urineoutput DOUBLE` |

The SQL also reads the CTE relations `surgflag`, `vent`, `cohort`, and
`scorecomp`/`score`; these are not additional warehouse tables.

## Join conditions and types

### Canonical OASIS joins

1. `surgflag`: `icustays ie LEFT JOIN services se` on
   `ie.hadm_id = se.hadm_id AND se.transfertime < DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`.
   There is deliberately no lower bound on `se.transfertime`; every matching
   service row before the ICU-intime-plus-one-day cutoff participates. The
   result is `MAX(CASE ...)` grouped by `ie.stay_id`.
2. `vent`: `icustays ie LEFT JOIN mimiciv_derived.ventilation v` on
   `ie.stay_id = v.stay_id`, `v.ventilation_status = 'InvasiveVent'`, and an
   inclusive interval-overlap test:
   `v.starttime >= ie.intime AND v.starttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`,
   OR `v.endtime >= ie.intime AND v.endtime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`,
   OR `v.starttime <= ie.intime AND v.endtime >= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`.
   It groups by `ie.stay_id` and computes a 0/1 `vent` flag.
3. `cohort`: `icustays ie INNER JOIN admissions adm ON ie.hadm_id = adm.hadm_id`.
4. `cohort`: `cohort` then `INNER JOIN patients pat ON ie.subject_id = pat.subject_id`.
   `pat` contributes no selected column; this is an existence join.
5. `cohort`: `LEFT JOIN age ag ON ie.hadm_id = ag.hadm_id`.
6. `cohort`: `LEFT JOIN surgflag sf ON ie.stay_id = sf.stay_id`.
7. `cohort`: `LEFT JOIN first_day_gcs gcs ON ie.stay_id = gcs.stay_id`.
8. `cohort`: `LEFT JOIN first_day_vitalsign vital ON ie.stay_id = vital.stay_id`.
9. `cohort`: `LEFT JOIN first_day_urine_output uo ON ie.stay_id = uo.stay_id`.
10. `cohort`: `LEFT JOIN vent ON ie.stay_id = vent.stay_id`.
11. `scorecomp`: `FROM cohort co`; no join.
12. `score`: `FROM scorecomp s`; no join.

### Relevant dependency joins and windows

These are dependency-owned transformations. OASIS must consume their
registered stem outputs rather than re-deriving them from FHIR resources.

- `age.sql`: `admissions ad INNER JOIN patients pa ON ad.subject_id = pa.subject_id`.
  It emits one row per admission with `hadm_id` and calculated `age`.
- `first_day_gcs.sql`: `icustays ie LEFT JOIN derived.gcs g ON ie.stay_id = g.stay_id`
  with `g.charttime >= ie.intime - 6 hours` and `g.charttime <= ie.intime + 1
  day`; `ROW_NUMBER() OVER (PARTITION BY g.stay_id ORDER BY g.gcs ASC NULLS LAST,
  g.charttime DESC NULLS LAST)` selects the minimum GCS and deterministic
  latest charttime tie-break. Its final `icustays` LEFT JOIN retains every
  stay.
- `first_day_urine_output.sql`: `icustays ie LEFT JOIN derived.urine_output
  uo ON ie.stay_id = uo.stay_id` with inclusive
  `uo.charttime >= ie.intime` and `uo.charttime <= ie.intime + 1 day`; it
  `SUM`s to stay grain.
- `first_day_vitalsign.sql`: `icustays ie LEFT JOIN derived.vitalsign ce ON
  ie.stay_id = ce.stay_id` with inclusive
  `ce.charttime >= ie.intime - 6 hours` and `ce.charttime <= ie.intime + 1
  day`; it computes MIN/MAX/AVG at `(subject_id, stay_id)` grain.
- `ventilation.sql`: `tm` is `UNION DISTINCT` of `(stay_id, charttime)` from
  derived `ventilator_setting` and `oxygen_delivery`. `vs` LEFT JOINs both
  derived sources back to `tm` on exact `(stay_id, charttime)`. `vd0` filters
  `ventilation_status IS NOT NULL` and uses `LAG`/`LEAD`; `vd1` starts a new
  event for the first row, a gap of at least 14 hours, or a status change;
  `vd2` assigns `SUM(new_ventilation_event) OVER (PARTITION BY stay_id ORDER BY
  charttime)`; the final grouping is `(stay_id, vent_seq)` and has
  `HAVING MIN(charttime) != MAX(charttime)`. OASIS reads the resulting interval
  columns and applies its own first-day overlap test.
- `oxygen_delivery.sql` and `ventilator_setting.sql` both source
  `mimiciv_icu.chartevents`; each pivots to `(subject_id, stay_id, charttime)`.
  `oxygen_delivery` joins its selected chart rows to the oxygen-device rows
  on `(subject_id, charttime)` and uses `ROW_NUMBER` ordered by storetime/value
  to retain deterministic rows. `ventilator_setting` groups by
  `(subject_id, charttime)` and uses MAX pivots. These are transitive
  dependency internals, not tables for the OASIS candidate to query.

## Filters, windows, and value constraints in `oasis.sql`

There is **no `WHERE` clause** in the canonical OASIS SQL. The predicates that
control row participation are in JOIN `ON` clauses (listed above), and the
following CASE predicates control derived values.

### Component-score branches

The NULL guard in every component returns NULL when its source is NULL; the
final sum later converts each NULL score to zero. The non-NULL thresholds are:

- `preiculos_score` from `preiculos`: `< 10.2 -> 5`; `< 297 -> 3`; `< 1440 ->
  0`; `< 18708 -> 2`; otherwise `1`.
- `age_score` from `age`: `< 24 -> 0`; `<= 53 -> 3`; `<= 77 -> 6`; `<= 89 ->
  9`; `>= 90 -> 7`; final `ELSE 0` is present in the SQL.
- `gcs_score` from `gcs_min`: `<= 7 -> 10`; `< 14 -> 4`; `= 14 -> 3`;
  otherwise `0`.
- `heart_rate_score`: if `heart_rate_max > 125 -> 6`; else if
  `heart_rate_min < 33 -> 4`; else if `heart_rate_max >= 107 AND
  heart_rate_max <= 125 -> 3`; else if `heart_rate_max >= 89 AND
  heart_rate_max <= 106 -> 1`; otherwise `0`. The only initial NULL guard is
  `heart_rate_max IS NULL`.
- `mbp_score`: `mbp_min < 20.65 -> 4`; `mbp_min < 51 -> 3`; `mbp_max > 143.44
  -> 3`; `mbp_min >= 51 AND mbp_min < 61.33 -> 2`; otherwise `0`. The NULL
  guard is `mbp_min IS NULL`.
- `resp_rate_score`: `resp_rate_min < 6 -> 10`; `resp_rate_max > 44 -> 9`;
  `resp_rate_max > 30 -> 6`; `resp_rate_max > 22 -> 1`; `resp_rate_min < 13
  -> 1`; otherwise `0`. The NULL guard is `resp_rate_min IS NULL`.
- `temp_score`: `temperature_max > 39.88 -> 6`; `temperature_min >= 33.22
  AND temperature_min <= 35.93 -> 4`; `temperature_max >= 33.22 AND
  temperature_max <= 35.93 -> 4`; `temperature_min < 33.22 -> 3`;
  `temperature_min > 35.93 AND temperature_min <= 36.39 -> 2`;
  `temperature_max >= 36.89 AND temperature_max <= 39.88 -> 2`; otherwise
  `0`. The NULL guard is `temperature_max IS NULL`.
- `urineoutput_score`: `urineoutput < 671.09 -> 10`; `urineoutput > 6896.80
  -> 8`; `urineoutput >= 671.09 AND urineoutput <= 1426.99 -> 5`;
  `urineoutput >= 1427.00 AND urineoutput <= 2544.14 -> 1`; otherwise `0`.
- `mechvent_score`: `mechvent = 1 -> 9`, otherwise `0` after a NULL guard.
- `electivesurgery_score`: `electivesurgery = 1 -> 0`, otherwise `6` after a
  NULL guard.

The representative value CASE expressions (`heartrate`, `meanbp`, `resprate`,
and `temp`) repeat the same ordered thresholds, selecting the corresponding
min or max value for an abnormal branch and `(min + max) / 2` otherwise. They
have the same initial max/min NULL guards as their score counterparts. The
exact probability expression is `1 / (1 + EXP(-(-6.1746 + 0.1275 * (oasis))))`.

### Mortality and elective-surgery discriminators

These expressions are computed in `cohort` and carried through `scorecomp` and
`score`, but are not selected by the final projection:

- `electivesurgery = 1` only when `adm.admission_type = 'ELECTIVE'` AND
  `sf.surgical = 1`; it is NULL when `adm.admission_type IS NULL OR
  sf.surgical IS NULL`; otherwise it is `0`.
- `icustay_expire_flag = 1` when `adm.deathtime BETWEEN ie.intime AND
  ie.outtime`, or when `adm.deathtime <= ie.intime`, or when `adm.dischtime <=
  ie.outtime AND adm.discharge_location = 'DEAD/EXPIRED'`; otherwise `0`.
- `hospital_expire_flag` is copied from `adm` but is not part of the final
  output and does not enter the score.

## Literal code specification

No `itemid`, ICD, or other numeric code filter occurs in `oasis.sql` itself.
The exact literals in the canonical query are below. They are not to be
translated or expanded.

| literal exactly as SQL names it | source table/column or dependency column | feeds |
|---|---|---|
| `LOWER(curr_service) LIKE '%surg%'` | `mimiciv_hosp.services.curr_service` | `surgflag.surgical`, then `cohort.electivesurgery` |
| `curr_service = 'ORTHO'` | `mimiciv_hosp.services.curr_service` | `surgflag.surgical`, then `cohort.electivesurgery` |
| `v.ventilation_status = 'InvasiveVent'` | `mimiciv_derived.ventilation.ventilation_status` | `vent.vent`, then `cohort.mechvent` |
| `adm.admission_type = 'ELECTIVE'` | `mimiciv_hosp.admissions.admission_type` | `cohort.electivesurgery` and its score/value |
| `adm.discharge_location = 'DEAD/EXPIRED'` | `mimiciv_hosp.admissions.discharge_location` | intermediate `cohort.icustay_expire_flag` only |

The dependency-owned exact code sets which produce the OASIS inputs are
recorded here so they are not silently changed while porting the dependency
boundary. They remain specifications for those dependency concepts, not new
filters for an OASIS candidate:

- `gcs.sql` filters `mimiciv_icu.chartevents.itemid IN (223900, 223901,
  220739)`. The exact source-text discriminator is
  `ce.itemid = 223900 AND ce.value = 'No Response-ETT'`, which sets the
  intubation/`gcs_unable` branch and changes the calculated `gcs`.
- `urine_output.sql` filters `mimiciv_icu.outputevents.itemid IN (226559,
  226560, 226561, 226584, 226563, 226564, 226565, 226567, 226557, 226558,
  227488, 227489)`. For `oe.itemid = 227488 AND oe.value > 0`, the volume is
  negated; the other selected rows retain `oe.value`.
- `vitalsign.sql` filters `mimiciv_icu.chartevents` with `ce.stay_id IS NOT
  NULL` and `ce.itemid IN (220045, 225309, 225310, 225312, 220050, 220051,
  220052, 220179, 220180, 220181, 220210, 224690, 220277, 225664, 220621,
  226537, 223762, 223761, 224642)`. Its value constraints are, verbatim in
  meaning: heart rate `> 0 AND < 300`; SBP and SBP-NI `> 0 AND < 400`; DBP,
  MBP and their NI variants `> 0 AND < 300`; respiratory rate `> 0 AND < 70`;
  Fahrenheit temperature `> 70 AND < 120`; Celsius temperature `> 10 AND
  < 50`; SpO2 `> 0 AND <= 100`; glucose `> 0`. Temperature Fahrenheit is
  converted as `(valuenum - 32) / 1.8` and rounded to two decimal places.
- `oxygen_delivery.sql` filters non-NULL `ce.value` and
  `mimiciv_icu.chartevents.itemid IN (223834, 227582, 227287)` for flows;
  `itemid = 226732` is the oxygen-device stream. It maps `223834` and
  `227582` to the merged flow item `223834`.
- `ventilator_setting.sql` filters non-NULL `ce.value`, non-NULL
  `ce.stay_id`, and `mimiciv_icu.chartevents.itemid IN (224688, 224689,
  224690, 224687, 224685, 224684, 224686, 224696, 220339, 224700, 223835,
  223849, 229314, 223848, 224691)`. Its cleaning discriminators include
  `itemid = 223835` (FiO2), `itemid IN (220339, 224700)` (PEEP), and the
  corresponding numeric limits in `ventilator_setting.sql:11-31`.
- `ventilation.sql` maps the derived device/mode values into the exact output
  statuses `Tracheostomy`, `InvasiveVent`, `NonInvasiveVent`, `HFNC`,
  `SupplementalOxygen`, `None`, or NULL. The exact categorical literals that
  can feed the `InvasiveVent` status are:
  `o2_delivery_device_1 IN ('Endotracheal tube')`;
  `ventilator_mode IN ('(S) CMV', 'APRV', 'APRV/Biphasic+ApnPress',
  'APRV/Biphasic+ApnVol', 'APV (cmv)', 'Ambient', 'Apnea Ventilation', 'CMV',
  'CMV/ASSIST', 'CMV/ASSIST/AutoFlow', 'CMV/AutoFlow', 'CPAP/PPS', 'CPAP/PSV',
  'CPAP/PSV+Apn TCPL', 'CPAP/PSV+ApnPres', 'CPAP/PSV+ApnVol', 'MMV',
  'MMV/AutoFlow', 'MMV/PSV', 'MMV/PSV/AutoFlow', 'P-CMV', 'PCV+', 'PCV+/PSV',
  'PCV+Assist', 'PRES/AC', 'PRVC/AC', 'PRVC/SIMV', 'PSV/SBT', 'SIMV',
  'SIMV/AutoFlow', 'SIMV/PRES', 'SIMV/PSV', 'SIMV/PSV/AutoFlow', 'SIMV/VOL',
  'SYNCHRON MASTER', 'SYNCHRON SLAVE', 'VOL/AC')`; or
  `ventilator_mode_hamilton IN ('APRV', 'APV (cmv)', 'Ambient', '(S) CMV',
  'P-CMV', 'SIMV', 'APV (simv)', 'P-SIMV', 'VS', 'ASV')`.
  Other dependency status literals are also source SQL and can affect which
  intervals are excluded/terminated: tracheostomy device values
  `'Tracheostomy tube'`, `'Trach mask '`; NIV device values `'Bipap mask '`,
  `'CPAP mask '` in slots 1-4 and Hamilton modes `'DuoPaP'`, `'NIV'`,
  `'NIV-ST'`; HFNC `'High flow nasal cannula'`; supplemental devices
  `'Non-rebreather'`, `'Face tent'`, `'Aerosol-cool'`, `'Venti mask '`,
  `'Medium conc mask '`, `'Ultrasonic neb'`, `'Vapomist'`, `'Oxymizer'`,
  `'High flow neb'`, `'Nasal cannula'`; and no-device `'None'`.

## Aggregations and windows

### Canonical OASIS

- `surgflag`: `MAX(CASE ... END)` grouped by `ie.stay_id`.
- `vent`: `MAX(CASE WHEN v.stay_id IS NOT NULL THEN 1 ELSE 0 END)` grouped by
  `ie.stay_id`.
- There is no `GROUP BY`, aggregate, or window in `cohort`, `scorecomp`, or
  `score`. The final score is a sum of ten `COALESCE`d integer component
  scores, and `oasis_prob` is a logistic expression, not an aggregate.

### Dependency aggregations/windows that determine consumed values

- `age`: arithmetic `anchor_age + DATETIME_DIFF(admittime, anchor_year-01-01,
  YEAR)`; the consumer reads only the resulting `age`.
- `first_day_gcs`: `ROW_NUMBER` minimum-GCS selection with charttime DESC tie
  break; the consumer reads only `gcs_min`.
- `first_day_urine_output`: `SUM(urineoutput)` grouped by
  `(subject_id, stay_id)` over the first-day rows.
- `first_day_vitalsign`: `MIN`, `MAX`, and `AVG` by `(subject_id, stay_id)`;
  OASIS reads only the min/max fields listed in the dependency boundary.
- `ventilation`: `UNION DISTINCT`, `LAG`, `LEAD`, cumulative `SUM` window,
  `MIN`/`MAX` interval aggregation, and the final `HAVING` clause described in
  the join section. Its interval grain is `(stay_id, vent_seq)` before OASIS
  collapses it to stay grain.

## Exact final output schema

The following is the final SELECT order and the exact type recorded in
`oracle_manifest.full.json`:

| ordinal | output column | type | source/derivation |
|---:|---|---|---|
| 1 | `subject_id` | `INTEGER` | `icustays.subject_id` |
| 2 | `hadm_id` | `INTEGER` | `icustays.hadm_id` |
| 3 | `stay_id` | `INTEGER` | `icustays.stay_id`, natural key |
| 4 | `oasis` | `INTEGER` | sum of ten `COALESCE`d component scores |
| 5 | `oasis_prob` | `DOUBLE` | `1 / (1 + EXP(-(-6.1746 + 0.1275 * oasis)))` |
| 6 | `age` | `BIGINT` | `age.age` |
| 7 | `age_score` | `INTEGER` | age branch |
| 8 | `preiculos` | `BIGINT` | `DATETIME_DIFF(ie.intime, adm.admittime, MINUTE)` |
| 9 | `preiculos_score` | `INTEGER` | pre-ICU LOS branch |
| 10 | `gcs` | `FLOAT` | `first_day_gcs.gcs_min` |
| 11 | `gcs_score` | `INTEGER` | GCS branch |
| 12 | `heartrate` | `DOUBLE` | selected HR min/max or `(min + max) / 2` |
| 13 | `heart_rate_score` | `INTEGER` | HR branch |
| 14 | `meanbp` | `DOUBLE` | selected MBP min/max or `(min + max) / 2` |
| 15 | `mbp_score` | `INTEGER` | MBP branch |
| 16 | `resprate` | `DOUBLE` | selected respiratory-rate min/max or average |
| 17 | `resp_rate_score` | `INTEGER` | respiratory-rate branch |
| 18 | `temp` | `DOUBLE` | selected temperature min/max or average |
| 19 | `temp_score` | `INTEGER` | temperature branch |
| 20 | `urineoutput` | `DOUBLE` | `first_day_urine_output.urineoutput` |
| 21 | `urineoutput_score` | `INTEGER` | urine-output branch |
| 22 | `mechvent` | `INTEGER` | `vent.vent`, 0/1 invasive-vent flag |
| 23 | `mechvent_score` | `INTEGER` | mechanical-ventilation branch |
| 24 | `electivesurgery` | `INTEGER` | elective admission plus surgical-service branch |
| 25 | `electivesurgery_score` | `INTEGER` | elective-surgery branch |

`icustay_expire_flag` and `hospital_expire_flag` are referenced and carried in
intermediate CTEs but intentionally do not appear in this final schema.

## Dependency boundary: exact columns the OASIS consumer reads

Candidate SQL must use the preprocessed unqualified dependency stems. It must
not query raw `mimiciv_derived` tables or rederive these values from FHIR:

| stem | exact consumer columns | role in OASIS |
|---|---|---|
| `age` | `hadm_id`, `age` | join by hospital admission; age score and final `age` |
| `first_day_gcs` | `stay_id`, `gcs_min` | join by ICU stay; GCS score and final `gcs` |
| `first_day_urine_output` | `stay_id`, `urineoutput` | join by ICU stay; urine score and final urine value |
| `first_day_vitalsign` | `stay_id`, `heart_rate_max`, `heart_rate_min`, `mbp_max`, `mbp_min`, `resp_rate_max`, `resp_rate_min`, `temperature_max`, `temperature_min` | join by ICU stay; four score/value pairs |
| `ventilation` | `stay_id`, `starttime`, `endtime`, `ventilation_status` | filter exact `'InvasiveVent'`, overlap the first 24 hours, derive `mechvent` |

Dependency columns not read by OASIS include age `subject_id/admittime/anchor_age/anchor_year`, first-day GCS component columns, all first-day vital means and non-OASIS vital streams, and the other ventilation statuses/interval values after the exact invasive-status filter. They are not inputs to this concept's output.

## Semantically essential inputs and trace

- `ie.stay_id` is the natural key, every ICU/dependency join key, and the
  partition/group key in `surgflag`, `vent`, and all first-day dependencies.
  A wrong or missing stay identity changes row inclusion or combines patients.
- `ie.subject_id` and `ie.hadm_id` are final identifiers. `hadm_id` controls
  the admission join and the `age` dependency join; `subject_id` controls the
  patient existence join and is emitted.
- `ie.intime` controls the service cutoff, invasive-vent interval overlap, and
  all first-day windows. `adm.admittime` controls `preiculos`, which feeds both
  the score and output. The dependency chart/output times and the exact
  inclusive endpoints control which GCS, vital, and urine observations enter
  their aggregate values.
- `ag.age` controls `age_score` and final `age`; the age dependency's loss of
  its source anchor pair is therefore relevant to this clinically meaningful
  output, even though the OASIS consumer must use the dependency result.
- `gcs.gcs_min` controls `gcs_score` and final `gcs`. The upstream GCS
  discriminator `value = 'No Response-ETT'`, its carry-forward/self-join, and
  its minimum/tie-break selection can change both.
- `vital.heart_rate_min/max`, `mbp_min/max`, `resp_rate_min/max`, and
  `temperature_min/max` each control one score branch and one representative
  final value. Their itemid identity, numeric plausibility constraints,
  Fahrenheit conversion, aggregation, and first-day time window are therefore
  essential; means and unrelated vital fields are not consumed.
- `uo.urineoutput` controls `urineoutput_score` and final `urineoutput`. Its
  item set, GU-irrigant sign reversal, charttime grouping, and first-day window
  are essential.
- `vent.vent` controls `mechvent` and `mechvent_score`. Its value depends on
  the exact `ventilation_status = 'InvasiveVent'` discriminator, interval
  overlap, ventilation-state classification, and interval construction; the
  source oxygen/ventilator item and mode/device strings are consequently
  essential through the dependency boundary.
- `adm.admission_type` and `sf.surgical` control `electivesurgery`, which
  controls `electivesurgery_score` and final `electivesurgery`. The exact
  service patterns `LOWER(curr_service) LIKE '%surg%'` and
  `curr_service = 'ORTHO'` are essential.
- Nullness is semantically significant: component NULLs remain NULL in the
  component/value output but contribute zero to `oasis`; `mechvent` is
  generated as a stay-level 0/1 flag, while `electivesurgery` can be NULL and
  then contributes zero through its score. This distinction must not be
  replaced by dropping the ICU stay.
- `deathtime`, `dischtime`, `discharge_location`, and
  `hospital_expire_flag` are source/intermediate inputs and are listed for
  SQL fidelity, but the mortality flags do not feed any final OASIS column or
  score branch. They are not semantically essential to the final selected
  result once the source projection is understood.

## Porting constraints surfaced by the notes

- Itemid-derived observations retain the exact numeric itemid in
  `Observation.code.coding.code`; no code translation is allowed. Numeric
  chartevent text that carries a discriminator is now preserved in
  `Observation.component.valueString` in the rebuilt warehouse, including the
  GCS `No Response-ETT` and ventilator-mode cases. The fragment leads are
  provisional dataset findings, not terminal equivalence evidence.
 - The authoritative notes say the current upstream UTC rebuild fixed the
   historical birthDate/DST defects; nevertheless, datetime values are served
   with offsets and ports must preserve wall-clock values with the documented
   `TIMESTAMP_NTZ` approach. For OASIS this matters because dependency windows
   and aggregates are anchored on `intime`/`charttime`.
- The relevant fragment leads also record dataset-level row-shape hazards that
  affect these dependency aggregates: the chartevents ETL has a global
  non-NULL-value predicate and a hard-coded stay/time exclusion, outputevents
  effective times are the dateTime variant, and oxygen-delivery source rows
  can repeat at one patient/charttime and must be ranked rather than
  pre-deduplicated. These are not OASIS SQL predicates; they are upstream
  served-data facts for the prober to verify at the dependency boundary.
 - Patient/admission/ICU identifiers are numeric source values carried in FHIR
  identifier values, while resource keys are opaque and must only be used for
  equality joins. This is why the source grain is `stay_id` but the FHIR port
  also retains the three manifest resource-key columns.
