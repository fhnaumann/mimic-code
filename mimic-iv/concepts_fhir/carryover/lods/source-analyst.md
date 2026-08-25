# Source analysis: `lods`

## Provenance and DAG position

- Canonical source: `mimic-iv/concepts/score/lods.sql` (230 lines).
- DAG node: stem `lods`, path `score/lods.sql`, level 2, SHA256
  `ddfc09733ed165a9e35a8ce9901878383facc47b8600c7cd9051f3993246f9c7`.
  The file hash was checked against `mimic-iv/concept_dag/concept_dag.json`.
- DAG dependencies, all referenced as `mimiciv_derived` tables by the source
  SQL: `bg`, `first_day_gcs`, `first_day_lab`, `first_day_urine_output`,
  `first_day_vitalsign`, and `ventilation`.

## Exact CTE semantics

### `cpap` (lines 28–46)

The CTE starts with ICU stays and **INNER JOINs** ICU chartevents.  A chart row
must have the same `stay_id`, a `charttime >= ie.intime`, and a
`charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)`.  The `WHERE` clause
then retains only `itemid = 226732` rows whose lower-cased `value` contains
`%cpap%` or `%bipap mask%`.

It groups by `ie.stay_id` and emits one row per matching stay:

- `starttime = MIN(charttime - 1 hour)`;
- `endtime = MAX(charttime + 4 hours)`;
- `cpap = MAX(CASE WHEN LOWER(value) LIKE '%cpap%' THEN 1 WHEN
  LOWER(value) LIKE '%bipap mask%' THEN 1 ELSE 0 END)`.

Because the text predicates are also in `WHERE`, every retained group has a
matching CPAP/BiPAP-mask value and the flag is normally 1.  The interval is a
single stay-wide envelope, not one interval per chart event.

### `pafi1` (lines 48–68)

This CTE starts from dependency `mimiciv_derived.bg` and **INNER JOINs** ICU
`icustays` by `bg.hadm_id = ie.hadm_id`, with
`bg.charttime >= ie.intime` and `bg.charttime < ie.outtime`.  It then **LEFT
JOINs** dependency `mimiciv_derived.ventilation` by stay and inclusive interval
membership (`bg.charttime >= vd.starttime` and `bg.charttime <= vd.endtime`),
restricted in the join to `vd.ventilation_status = 'InvasiveVent'`.  It also
**LEFT JOINs** the `cpap` CTE by stay and inclusive membership in its envelope.

For every resulting blood-gas/stay match it emits the blood-gas time and ratio,
plus integer flags:

- `vent = CASE WHEN vd.stay_id IS NOT NULL THEN 1 ELSE 0 END`;
- `cpap = CASE WHEN cp.stay_id IS NOT NULL THEN 1 ELSE 0 END`.

The blood-gas join is by `hadm_id`, not by `stay_id`; the time interval is what
limits a hospital admission's blood gases to an ICU stay.  Multiple matching
ICU stays or intervals can therefore multiply intermediate rows if the
upstream data permits them.

### `pafi2` (lines 70–77)

It keeps only `pafi1` rows where `vent = 1 OR cpap = 1`, groups by `stay_id`,
and computes `MIN(pao2fio2ratio)` as `pao2fio2_vent_min`.  Null ratios are
ignored by `MIN`; if no non-null ratio remains, the result is null.  This is
the only ratio used by the pulmonary component.

### `cohort` (lines 79–126)

The cohort starts from ICU `icustays` and **INNER JOINs** hospital `admissions`
on `hadm_id`, and hospital `patients` on `subject_id`.  These two joins do not
select any admission/patient attributes; they are existence/inclusion gates.
It then **LEFT JOINs** `pafi2`, `first_day_gcs`, `first_day_vitalsign`,
`first_day_urine_output`, and `first_day_lab`, each on `ie.stay_id`.

It carries the ICU identifiers and stay bounds, the dependency inputs needed by
the score, and renames `labs.bilirubin_total_max` to `bilirubin_max` and
`labs.platelets_min` to `platelet_min`.  The dependency rows are expected to
be one row per stay; the source SQL does not add a deduplication step here.

### `scorecomp` (lines 128–210)

`scorecomp` selects `cohort.*` and adds six component scores.  These are
ordered `CASE` branches, so the first true branch wins:

- **Neurologic:** null `gcs_min` or `gcs_min < 3` gives NULL; `<= 5` gives 5;
  `<= 8` gives 3; `<= 13` gives 1; otherwise 0.
- **Cardiovascular:** if both `heart_rate_max` and `sbp_min` are NULL, give
  NULL. Otherwise, in order: `heart_rate_min < 30` → 5; `sbp_min < 40` → 5;
  `sbp_min < 70` → 3; `sbp_max >= 270` → 3; `heart_rate_max >= 140` → 1;
  `sbp_max >= 240` → 1; `sbp_min < 90` → 1; otherwise 0. Null comparisons
  not caught by the initial gate fall through to later branches/ELSE.
- **Renal:** if any of `bun_max`, `urineoutput`, or `creatinine_max` is NULL,
  give NULL. Otherwise, in order: `urineoutput < 500.0` → 5;
  `bun_max >= 56.0` → 5; `creatinine_max >= 1.60` → 3;
  `urineoutput < 750.0` → 3; `bun_max >= 28.0` → 3;
  `urineoutput >= 10000.0` → 3; `creatinine_max >= 1.20` → 1;
  `bun_max >= 17.0` → 1; `bun_max >= 7.50` → 1; otherwise 0.
- **Pulmonary:** null `pao2fio2_vent_min` gives 0 (not NULL);
  `>= 150` gives 1; `< 150` gives 3; the final ELSE is NULL.
- **Hematologic:** if both `wbc_max` and `platelet_min` are NULL, give NULL.
  Otherwise, in order: `wbc_min < 1.0` → 3; `wbc_min < 2.5` → 1;
  `platelet_min < 50.0` → 1; `wbc_max >= 50.0` → 1; otherwise 0.
- **Hepatic:** if both `pt_max` and `bilirubin_max` are NULL, give NULL.
  Otherwise, in order: `bilirubin_max >= 2.0` → 1;
  `pt_max > (12 + 3)` → 1; `pt_min < (12 * 0.25)` → 1; otherwise 0.
  The source comment explicitly identifies 12 seconds as the assumed standard
  PT; this is a source-code assumption, not an input field.

### Final SELECT (lines 212–230)

The final query starts from **all** ICU `icustays` and **LEFT JOINs**
`scorecomp` on `stay_id`.  It returns the three ICU identifiers and the total
plus six components.  The total is the sum of the six component values after
each is `COALESCE`d to integer zero.  The component columns themselves are not
coalesced.  Consequently, if no `scorecomp` row exists, the final row still
has `lods = 0` but all six component columns are NULL; if a component is NULL
within an existing score row, it contributes zero to `lods` while remaining
NULL in its own output column.

## Direct table and CTE references

Logical schemas below omit the BigQuery project qualifier
`physionet-data`.

| SQL location | source | type | join / use |
|---|---|---|---|
| `cpap` | `mimiciv_icu.icustays ie` | raw table | FROM; supplies `stay_id`, `intime` |
| `cpap` | `mimiciv_icu.chartevents ce` | raw table | INNER JOIN on stay and first-day chart-time window |
| `pafi1` | `mimiciv_derived.bg bg` | derived dependency | FROM; inner-joined to ICU stay by hadm/time |
| `pafi1` | `mimiciv_icu.icustays ie` | raw table | INNER JOIN by `hadm_id`, `intime`, `outtime` |
| `pafi1` | `mimiciv_derived.ventilation vd` | derived dependency | LEFT interval join by `stay_id`, time, and status |
| `pafi1` | CTE `cpap cp` | local CTE | LEFT interval join by stay and envelope |
| `pafi2` | CTE `pafi1` | local CTE | FROM; filters flags and aggregates |
| `cohort` | `mimiciv_icu.icustays ie` | raw table | FROM; final cohort spine |
| `cohort` | `mimiciv_hosp.admissions adm` | raw table | INNER JOIN `ie.hadm_id = adm.hadm_id`; inclusion gate only |
| `cohort` | `mimiciv_hosp.patients pat` | raw table | INNER JOIN `ie.subject_id = pat.subject_id`; inclusion gate only |
| `cohort` | CTE `pafi2 pf` | local CTE | LEFT JOIN `ie.stay_id = pf.stay_id` |
| `cohort` | `mimiciv_derived.first_day_gcs gcs` | derived dependency | LEFT JOIN by stay |
| `cohort` | `mimiciv_derived.first_day_vitalsign vital` | derived dependency | LEFT JOIN by stay |
| `cohort` | `mimiciv_derived.first_day_urine_output uo` | derived dependency | LEFT JOIN by stay |
| `cohort` | `mimiciv_derived.first_day_lab labs` | derived dependency | LEFT JOIN by stay |
| `scorecomp` | CTE `cohort` | local CTE | FROM; adds component CASE expressions |
| final | `mimiciv_icu.icustays ie` | raw table | FROM; preserves every ICU stay |
| final | CTE `scorecomp s` | local CTE | LEFT JOIN `ie.stay_id = s.stay_id` |

## Column inventory and inferred types

The canonical SQL is BigQuery-style and does not cast the final columns. Types
below are inferred from source schema usage, arithmetic, and `CASE` branches;
the six score components, flags, and totals are integer-valued, while measured
and aggregate clinical values retain their numeric source type.

### Raw columns directly touched

- `mimiciv_icu.icustays`: `subject_id` (integer), `hadm_id` (integer),
  `stay_id` (integer key), `intime` (DATETIME/timestamp-like), and `outtime`
  (DATETIME/timestamp-like).
- `mimiciv_icu.chartevents`: `stay_id` (integer), `charttime`
  (DATETIME/timestamp-like), `itemid` (integer), and `value` (string).
- `mimiciv_hosp.admissions`: `hadm_id` (integer join key).
- `mimiciv_hosp.patients`: `subject_id` (integer join key).

### Dependency columns consumed exactly (do not rederive these from FHIR)

The candidate may reference these completed dependency outputs by their
unqualified stems. These are the exact consumer columns used by `lods`:

- `FROM bg`: `hadm_id` (integer), `charttime` (DATETIME/timestamp-like), and
  `pao2fio2ratio` (numeric). `bg` also supplies the dependency row grain, but
  no other `bg` column is read by this SQL.
- `FROM ventilation`: `stay_id` (integer), `starttime` and `endtime`
  (DATETIME/timestamp-like), and `ventilation_status` (string category).
- `FROM first_day_gcs`: `stay_id` (integer) and `gcs_min` (integer-valued).
- `FROM first_day_vitalsign`: `stay_id` (integer), `heart_rate_max`,
  `heart_rate_min`, `sbp_max`, and `sbp_min` (numeric; source aggregates).
- `FROM first_day_urine_output`: `stay_id` (integer) and `urineoutput`
  (numeric; SUM result).
- `FROM first_day_lab`: `stay_id` (integer), `bun_max`, `bun_min`,
  `wbc_max`, `wbc_min`, `bilirubin_total_max`, `creatinine_max`, `pt_min`,
  `pt_max`, and `platelets_min` (numeric source aggregates). `cohort` aliases
  `bilirubin_total_max` to `bilirubin_max` and `platelets_min` to
  `platelet_min`.

### CTE and final columns

- `cpap`: `stay_id` (integer), `starttime` and `endtime` (DATETIME), `cpap`
  (integer 0/1).
- `pafi1`: `stay_id` (integer), `charttime` (DATETIME),
  `pao2fio2ratio` (numeric), `vent` (integer 0/1), and `cpap` (integer 0/1).
- `pafi2`: `stay_id` (integer), `pao2fio2_vent_min` (numeric).
- `cohort`: `subject_id`, `hadm_id`, `stay_id` (integers), `intime` and
  `outtime` (DATETIME), `gcs_min` (integer-valued), the four vital extrema
  (`heart_rate_max`, `heart_rate_min`, `sbp_max`, `sbp_min`, numeric),
  `pao2fio2_vent_min` (numeric), the nine lab fields listed above after the
  two aliases (numeric), and `urineoutput` (numeric).
- `scorecomp`: every `cohort.*` column plus `neurologic`, `cardiovascular`,
  `renal`, `pulmonary`, `hematologic`, and `hepatic` (integer-valued; nullable
  before the final sum).
- Final output, exactly in source order: `subject_id` (integer), `hadm_id`
  (integer), `stay_id` (integer), `lods` (integer-valued sum), `neurologic`,
  `cardiovascular`, `renal`, `pulmonary`, `hematologic`, and `hepatic`
  (nullable integer-valued component scores).

## Filters, time windows, and literal code specification

### WHERE predicates

1. `cpap`: `itemid = 226732` and
   `(LOWER(ce.value) LIKE '%cpap%' OR LOWER(ce.value) LIKE '%bipap mask%')`.
2. `pafi2`: `vent = 1 OR cpap = 1`.

There is no `WHERE` clause in `pafi1`, `cohort`, `scorecomp`, or the final
SELECT.  Time restrictions in JOIN predicates are still inclusion conditions:
the CPAP chart rows are in `[intime, intime + 1 day]`; blood gases are in
`[intime, outtime)` for the ICU stay; invasive-vent intervals and the CPAP
envelope use inclusive endpoints.

### Verbatim coded/text literals

This is the complete code/filter set named directly by `lods.sql`; dependency
concepts retain their own code specifications and must not be re-derived here.

| literal exactly as named | source column/table | feeds |
|---|---|---|
| `226732` | `mimiciv_icu.chartevents.itemid` | `cpap` CTE inclusion, then its `cpap` flag and interval used by `pafi1` |
| `'%cpap%'` | `mimiciv_icu.chartevents.value` after `LOWER` | `cpap` CTE inclusion and `cpap` CASE flag |
| `'%bipap mask%'` | `mimiciv_icu.chartevents.value` after `LOWER` | `cpap` CTE inclusion and `cpap` CASE flag |
| `'InvasiveVent'` | `mimiciv_derived.ventilation.ventilation_status` | `pafi1` LEFT JOIN restriction and therefore `vent` flag |

No ICD codes or other coded filters are present in this source SQL.  The
literal `12` in the hepatic PT CASE is a scoring assumption/threshold, not a
code.

## Aggregation and grain

- `cpap`: `MIN`/`MAX` over chart times and `MAX` over a 0/1 CASE, grouped by
  `stay_id`.
- `pafi2`: `MIN(pao2fio2ratio)`, grouped by `stay_id`, after the vent/CPAP
  flag filter.
- No window functions, `GROUP BY`, or aggregate functions occur in
  `pafi1`, `cohort`, `scorecomp`, or the final SELECT.  The source SQL does
  not itself define the windows used to make the six dependency tables; those
  dependency outputs must be consumed as tables.
- Intended final grain is one row per ICU stay (`stay_id`), with
  `subject_id` and `hadm_id` as associated identifiers.  The final ICU-stay
  spine and `LEFT JOIN scorecomp` preserve all `icustays` rows, while the
  inner admission/patient joins inside `cohort` can cause a score row to be
  absent for a stay.

## Semantically essential inputs and representability risks

These are inputs whose value changes inclusion, interval membership, grain, a
component, or the clinically meaningful total:

- `stay_id` is the natural grain and every interval/dependency join key.
  `hadm_id` controls the blood-gas-to-ICU inner join; `subject_id` is the
  patient identifier and final output.  `admissions.hadm_id` and
  `patients.subject_id` are inclusion gates even though their other fields are
  unused.
- `intime` controls the CPAP first-day chart window, the CPAP envelope's
  reference, and blood-gas inclusion. `outtime` is the exclusive upper bound
  for blood gases.  The first-day dependency tables also embody their own
  `intime`-based windows, so their already-derived outputs must be used rather
  than recomputing from FHIR resources.
- Chartevents `itemid`, `value`, and `charttime` control whether CPAP exists,
  the CPAP interval, and blood-gas CPAP membership.  The authoritative notes
  say itemid-derived Observation codes preserve exact itemid text and that
  categorical chartevents use `value.ofType(string)`; use the exact
  chartevents coding system plus code, not display or profile.  Repeated
  same-item rows must not be assumed to be unique.  The global chartevents
  ETL drops NULL-valued rows and one hard-coded tuple; verify the target 226732
  stream during probing because a dropped earliest/latest matching row could
  change the CPAP envelope.
- `bg.hadm_id`, `bg.charttime`, and `bg.pao2fio2ratio` control blood-gas row
  inclusion, interval matching, and the pulmonary minimum.  `ventilation`
  interval endpoints and the exact `ventilation_status = 'InvasiveVent'`
  discriminator control the invasive-vent flag.  Do not broaden it to other
  statuses: the source only scores the minimum ratio for invasive-vent or CPAP
  rows.
- `gcs_min` controls the neurologic CASE, including the special NULL result
  below 3.  `heart_rate_max`, `heart_rate_min`, `sbp_max`, and `sbp_min`
  control cardiovascular null gating and ordered threshold branches.
  `bun_max`, `urineoutput`, and `creatinine_max` control renal null gating and
  all renal thresholds.  `pao2fio2_vent_min` controls pulmonary scoring, with
  absent ventilated/CPAP ratio intentionally scoring 0.
  `wbc_max`, `wbc_min`, and `platelet_min` control hematologic null gating and
  thresholds.  `pt_max`, `pt_min`, and `bilirubin_max` control hepatic null
  gating and thresholds.
- Component nullness is semantically meaningful in the component outputs,
  while the total deliberately imputes each null component as zero.  Preserve
  both behaviors; do not replace component NULLs with zero in their individual
  columns.

The FHIR-side risks are primarily dependency and time-window risks:

1. `lods` cannot be faithfully rebuilt by selecting raw FHIR observations and
   reimplementing the dependency algorithms.  The DAG requires `bg`,
   `first_day_gcs`, `first_day_lab`, `first_day_urine_output`,
   `first_day_vitalsign`, and `ventilation` to be ported first; candidate SQL
   should consume their unqualified stems and the exact columns above.
2. `first_day_gcs.gcs_min` is essential because it changes neurologic and the
   total score.  The notes record that the rebuilt upstream ETL now carries a
   distinct numeric chartevent text discriminator in `Observation.component`
   (the older loss of `No Response-ETT` is historical); the prober should
   verify the repaired component path rather than infer labels from an opaque
   resource id or from Quantity 1.
3. All dependency aggregations and both direct CPAP/blood-gas windows depend
   on FHIR datetimes.  Served FHIR datetimes include offsets and must be
   treated as de-identified wall-clock values; the notes require
   `TIMESTAMP_NTZ`-style parsing rather than offset-aware timezone conversion.
   The previously documented upstream DST-gap shift was fixed in the current
   UTC-built warehouse, so a new shifted value would be a port defect, not a
   reason to reproduce the historical shift.  Window boundaries remain an
   essential probe target.
4. The cohort's raw admission/patient existence joins have no clinical values
   to map, but an incorrect Encounter stream (hospital or ED instead of ICU),
   an inner join through an incompletely referenced Encounter, or an uncast
   identifier can change row inclusion or output types.  The FHIR notes specify
   ICU Encounter discrimination by the ICU identifier system and MIMIC numeric
   identifiers in `identifier.value`; resource keys are opaque join identity,
   not substitutes for `stay_id`, `hadm_id`, or `subject_id`.
5. `pao2fio2_vent_min` is nullable for no matching ratio but pulmonary maps
   that null to score zero.  This is distinct from the other component null
   gates and should be retained exactly.

No new dataset-wide quirk was discovered in this source-only analysis, so no
`MIMIC_NOTES.d/lods.md` fragment was created.
