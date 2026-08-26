# Source analysis: `first_day_sofa`

This is a static description of the canonical SQL. It does not author a
ViewDefinition or candidate SQL, execute SQL, or make a terminal
representability decision.

## Source and DAG identity

- Concept stem: `first_day_sofa`.
- Canonical SQL: `mimic-iv/concepts/firstday/first_day_sofa.sql`.
- DAG node: `first_day_sofa`, path `firstday/first_day_sofa.sql`, level `2`.
- DAG SHA256:
  `e56ae4c67d7b19bf8d47f262011bcd888bdb04160b1e9ce744423243b867892e`.
  The file on disk hashes to this value.
- DAG dependencies, in the DAG's dependency list:
  `bg`, `dobutamine`, `dopamine`, `epinephrine`, `first_day_gcs`,
  `first_day_lab`, `first_day_urine_output`, `first_day_vitalsign`,
  `norepinephrine`, and `ventilation`.
- The oracle manifest records 73,181 rows, `keyed_join` comparison, natural
  comparison key `stay_id`, and required FHIR key columns
  `encounter_key`, `icu_encounter_key`, and `patient_key`.

The canonical SQL uses the deployment-qualified form
`physionet-data.mimiciv_<schema>.<table>`. The logical schemas below omit the
project prefix.

## 1. Table and relation references

### Physical source/dependency tables

| SQL relation | Logical schema | Table/stem | Alias/use |
|---|---|---|---|
| Four `FROM` clauses in `vaso_stg` | `mimiciv_icu` | `icustays` | `ie`; driving ICU-stay spine for each vasoactive branch |
| Four `INNER JOIN` clauses in `vaso_stg` | `mimiciv_derived` | `norepinephrine`, `epinephrine`, `dobutamine`, `dopamine` | `mv`; completed medication dependencies |
| `FROM` in `vaso_mv` | `mimiciv_icu` | `icustays` | `ie`; one row per ICU stay before the rate pivot |
| `FROM` in `pafi1` | `mimiciv_icu` | `icustays` | `ie`; ICU stay and `intime` anchor |
| `LEFT JOIN` in `pafi1` | `mimiciv_derived` | `bg` | `bg`; blood-gas ratio and specimen/time |
| `LEFT JOIN` in `pafi1` | `mimiciv_derived` | `ventilation` | `vd`; ventilation intervals/status |
| `FROM` in `scorecomp` | `mimiciv_icu` | `icustays` | `ie`; final score-component spine |
| `LEFT JOIN` in `scorecomp` | `mimiciv_derived` | `first_day_vitalsign` | `v`; `mbp_min` |
| `LEFT JOIN` in `scorecomp` | `mimiciv_derived` | `first_day_lab` | `l`; creatinine, bilirubin, and platelets |
| `LEFT JOIN` in `scorecomp` | `mimiciv_derived` | `first_day_urine_output` | `uo`; first-day urine total |
| `LEFT JOIN` in `scorecomp` | `mimiciv_derived` | `first_day_gcs` | `gcs`; minimum GCS |
| Final `FROM` | `mimiciv_icu` | `icustays` | `ie`; final one-row-per-stay spine |

The SQL also references these local CTE relations, which are not physical
tables: `vaso_stg`, `vaso_mv`, `pafi1`, `pafi2`, `scorecomp`, and `scorecalc`.
Their exact local `FROM`/`JOIN` references are `FROM vaso_stg` in
`vaso_mv`, `FROM pafi1` in `pafi2`, `FROM scorecomp` in `scorecalc`,
`LEFT JOIN vaso_stg` in `vaso_mv`, `LEFT JOIN vaso_mv` and `LEFT JOIN pafi2`
in `scorecomp`, and `LEFT JOIN scorecalc` in the final query.
Their relation flow is:

```text
vaso_stg -> vaso_mv
icustays + bg + ventilation -> pafi1 -> pafi2
icustays + vaso_mv + pafi2 + first_day_* dependencies -> scorecomp
scorecomp -> scorecalc
icustays + scorecalc -> final SELECT
```

There is no direct `mimiciv_hosp` table reference. There are no raw
`chartevents`, `labevents`, `inputevents`, or `outputevents` references in
this file; those inputs are encapsulated by the derived dependencies.

## 2. Columns and inferred types

### Raw `mimiciv_icu.icustays` columns

The SQL references exactly:

| Column | Inferred type | Uses |
|---|---|---|
| `subject_id` | `INTEGER` | Final output and the `bg` join in `pafi1` |
| `hadm_id` | `INTEGER` | Final output only |
| `stay_id` | `INTEGER` | All ICU-stay joins, grouping, and final natural key |
| `intime` | `TIMESTAMP`/`DATETIME` | All vaso medication windows and the blood-gas window |

`outtime`, care-unit fields, and all other `icustays` fields are unused.

### Exact dependency read-set

The following is the complete column interface read by this consumer. A
candidate must consume the completed dependency under its unqualified stem and
must not rederive these values from FHIR resources.

| Candidate stem / source table | Exact columns read | CTE and downstream use |
|---|---|---|
| `bg` / `mimiciv_derived.bg` | `subject_id`, `charttime`, `pao2fio2ratio`, `specimen` | `pafi1`; ratio and specimen-selected arterial gases feed `pafi2` and respiration |
| `norepinephrine` / `mimiciv_derived.norepinephrine` | `stay_id`, `starttime`, `vaso_rate` | `vaso_stg` → `rate_norepinephrine` → cardiovascular score |
| `epinephrine` / `mimiciv_derived.epinephrine` | `stay_id`, `starttime`, `vaso_rate` | `vaso_stg` → `rate_epinephrine` → cardiovascular score |
| `dobutamine` / `mimiciv_derived.dobutamine` | `stay_id`, `starttime`, `vaso_rate` | `vaso_stg` → `rate_dobutamine` → cardiovascular score |
| `dopamine` / `mimiciv_derived.dopamine` | `stay_id`, `starttime`, `vaso_rate` | `vaso_stg` → `rate_dopamine` → cardiovascular score |
| `ventilation` / `mimiciv_derived.ventilation` | `stay_id`, `starttime`, `endtime`, `ventilation_status` | `pafi1`; `InvasiveVent` interval membership sets `isvent` |
| `first_day_vitalsign` / `mimiciv_derived.first_day_vitalsign` | `stay_id`, `mbp_min` | `scorecomp` → cardiovascular score |
| `first_day_lab` / `mimiciv_derived.first_day_lab` | `stay_id`, `creatinine_max`, `bilirubin_total_max`, `platelets_min` | `scorecomp` → renal, liver, and coagulation scores |
| `first_day_urine_output` / `mimiciv_derived.first_day_urine_output` | `stay_id`, `urineoutput` | `scorecomp` → renal score |
| `first_day_gcs` / `mimiciv_derived.first_day_gcs` | `stay_id`, `gcs_min` | `scorecomp` → CNS score |

The dependency's other columns are not read by this SQL. In particular, this
consumer does not read medication `linkorderid`, `vaso_amount`, `endtime`,
units, source `itemid`, or dependency `subject_id` values except for `bg`'s
explicit `subject_id` join. The source SQL's logical integer `stay_id`
joins may need to be represented by the published opaque ICU encounter key in
the candidate dependency interface; that is an equality join, not permission
to parse or regenerate a resource id.

### Intermediate CTE columns and types

#### `vaso_stg`

Each of four `UNION ALL` branches selects:

| Column | Type | Expression |
|---|---|---|
| `stay_id` | `INTEGER` | `ie.stay_id` |
| `treatment` | `VARCHAR`/`STRING` | One of the four exact treatment literals |
| `rate` | nullable floating-point (`FLOAT`/`DOUBLE`) | Dependency `mv.vaso_rate` |

There is one row per dependency medication row whose `starttime` is in the
branch's inclusive window and whose `stay_id` matches.

#### `vaso_mv`

| Column | Type | Expression |
|---|---|---|
| `stay_id` | `INTEGER` | ICU stay/grouping key |
| `rate_norepinephrine` | nullable floating-point | `MAX(CASE WHEN treatment = 'norepinephrine' THEN rate ELSE NULL END)` |
| `rate_epinephrine` | nullable floating-point | `MAX(CASE WHEN treatment = 'epinephrine' THEN rate ELSE NULL END)` |
| `rate_dopamine` | nullable floating-point | `MAX(CASE WHEN treatment = 'dopamine' THEN rate ELSE NULL END)` |
| `rate_dobutamine` | nullable floating-point | `MAX(CASE WHEN treatment = 'dobutamine' THEN rate ELSE NULL END)` |

#### `pafi1`

| Column | Type | Expression |
|---|---|---|
| `stay_id` | `INTEGER` | `ie.stay_id` |
| `charttime` | `TIMESTAMP`/`DATETIME` | `bg.charttime` |
| `pao2fio2ratio` | nullable floating-point | `bg.pao2fio2ratio` |
| `isvent` | integer-valued `INTEGER` (0/1) | `CASE WHEN vd.stay_id IS NOT NULL THEN 1 ELSE 0 END` |

#### `pafi2`

| Column | Type | Expression |
|---|---|---|
| `stay_id` | `INTEGER` | Grouping key |
| `pao2fio2_novent_min` | nullable floating-point | Minimum ratio where `isvent = 0` |
| `pao2fio2_vent_min` | nullable floating-point | Minimum ratio where `isvent = 1` |

#### `scorecomp`

`scorecomp` has one row per ICU stay after the left joins. Its columns are:

| Column | Type | Source |
|---|---|---|
| `stay_id` | `INTEGER` | `ie.stay_id` |
| `mbp_min` | nullable numeric/floating-point | `v.mbp_min` |
| `rate_norepinephrine`, `rate_epinephrine`, `rate_dopamine`, `rate_dobutamine` | nullable floating-point | `vaso_mv` |
| `creatinine_max` | nullable numeric/floating-point | `l.creatinine_max` |
| `bilirubin_max` | nullable numeric/floating-point | `l.bilirubin_total_max` (renamed in this CTE) |
| `platelet_min` | nullable numeric/floating-point | `l.platelets_min` (renamed in this CTE) |
| `pao2fio2_novent_min`, `pao2fio2_vent_min` | nullable floating-point | `pafi2` |
| `urineoutput` | nullable numeric/floating-point | `uo.urineoutput` |
| `gcs_min` | nullable numeric/floating-point | `gcs.gcs_min` |

#### `scorecalc`

`scorecalc` contains `stay_id INTEGER` and six nullable integer-valued CASE
outputs: `respiration`, `coagulation`, `liver`, `cardiovascular`, `cns`, and
`renal`. Null is retained at this stage when the relevant source component is
missing; the final total substitutes zero for a null component.

### Final output columns

The final SELECT returns the following columns in this order. Types are the
oracle manifest types (and agree with the SQL expressions):

| # | Output | Expression | Type |
|---:|---|---|---|
| 1 | `subject_id` | `ie.subject_id` | `INTEGER` |
| 2 | `hadm_id` | `ie.hadm_id` | `INTEGER` |
| 3 | `stay_id` | `ie.stay_id` | `INTEGER` |
| 4 | `sofa` | sum of six `COALESCE(component, 0)` expressions | `INTEGER` |
| 5 | `respiration` | `s.respiration` | `INTEGER` |
| 6 | `coagulation` | `s.coagulation` | `INTEGER` |
| 7 | `liver` | `s.liver` | `INTEGER` |
| 8 | `cardiovascular` | `s.cardiovascular` | `INTEGER` |
| 9 | `cns` | `s.cns` | `INTEGER` |
| 10 | `renal` | `s.renal` | `INTEGER` |

The FHIR-port loop additionally requires the manifest key columns
`encounter_key`, `icu_encounter_key`, and `patient_key`; these are comparison
interface requirements, not columns selected by the canonical relational SQL.

## 3. Filters and value constraints

### WHERE clauses

There are **no `WHERE` clauses** in `first_day_sofa.sql`. There is no direct
`itemid`, ICD, LOINC, null, unit, admission, or explicit value-range WHERE
filter. All row inclusion in this file is expressed in `JOIN ... ON`
predicates or in conditional score expressions.

### Join-window predicates

The four `vaso_stg` branches each use the same inclusive predicates:

```sql
ie.stay_id = mv.stay_id
AND mv.starttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
AND mv.starttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

Thus, medication rows from six hours before `intime` through exactly one day
after `intime` are included. The window is applied to `starttime`, not
`endtime`.

`pafi1` uses:

```sql
ie.subject_id = bg.subject_id
AND bg.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
AND bg.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
AND bg.specimen = 'ART.'
```

and then overlays ventilation with:

```sql
ie.stay_id = vd.stay_id
AND bg.charttime >= vd.starttime
AND bg.charttime <= vd.endtime
AND vd.ventilation_status = 'InvasiveVent'
```

The blood-gas-to-ventilation temporal relationship is inclusive at both
interval endpoints. `pafi2` and all score-component dependency joins do not
add time predicates.

The `bg` join intentionally uses `subject_id` plus time, not `bg.stay_id` or
`hadm_id`; no stay equality predicate is present on that branch.

### Score/value conditions

The following are not SQL row filters; they are ordered CASE branch
discriminators that determine component values and NULL behavior.

**Respiration** (evaluated in this order):

```text
pao2fio2_vent_min < 100  -> 4
pao2fio2_vent_min < 200  -> 3
pao2fio2_novent_min < 300 -> 2
pao2fio2_novent_min < 400 -> 1
COALESCE(pao2fio2_vent_min, pao2fio2_novent_min) IS NULL -> NULL
ELSE -> 0
```

**Coagulation:**

```text
platelet_min < 20  -> 4
platelet_min < 50  -> 3
platelet_min < 100 -> 2
platelet_min < 150 -> 1
platelet_min IS NULL -> NULL
ELSE -> 0
```

**Liver:**

```text
bilirubin_max >= 12.0 -> 4
bilirubin_max >= 6.0  -> 3
bilirubin_max >= 2.0  -> 2
bilirubin_max >= 1.2  -> 1
bilirubin_max IS NULL -> NULL
ELSE -> 0
```

**Cardiovascular** (the SQL's exact ordered conditions, including its
three-valued-logic behavior):

```text
rate_dopamine > 15
  OR rate_epinephrine > 0.1
  OR rate_norepinephrine > 0.1 -> 4
rate_dopamine > 5
  OR rate_epinephrine <= 0.1
  OR rate_norepinephrine <= 0.1 -> 3
rate_dopamine > 0
  OR rate_dobutamine > 0 -> 2
mbp_min < 70 -> 1
COALESCE(mbp_min, rate_dopamine, rate_dobutamine,
         rate_epinephrine, rate_norepinephrine) IS NULL -> NULL
ELSE -> 0
```

**CNS:**

```text
gcs_min >= 13 AND gcs_min <= 14 -> 1
gcs_min >= 10 AND gcs_min <= 12 -> 2
gcs_min >= 6 AND gcs_min <= 9 -> 3
gcs_min < 6 -> 4
gcs_min IS NULL -> NULL
ELSE -> 0
```

**Renal** (ordered high-creatinine/urine-output branches):

```text
creatinine_max >= 5.0 -> 4
urineoutput < 200 -> 4
creatinine_max >= 3.5 AND creatinine_max < 5.0 -> 3
urineoutput < 500 -> 3
creatinine_max >= 2.0 AND creatinine_max < 3.5 -> 2
creatinine_max >= 1.2 AND creatinine_max < 2.0 -> 1
COALESCE(urineoutput, creatinine_max) IS NULL -> NULL
ELSE -> 0
```

The final total is:

```sql
COALESCE(respiration, 0)
+ COALESCE(coagulation, 0)
+ COALESCE(liver, 0)
+ COALESCE(cardiovascular, 0)
+ COALESCE(cns, 0)
+ COALESCE(renal, 0)
```

This differs from the component columns: a missing component remains NULL in
its named output but contributes zero to `sofa`.

## 4. Joins and join types

| CTE/location | Type | Left/right | Exact condition |
|---|---|---|---|
| `vaso_stg` norepinephrine branch | `INNER JOIN` | `icustays ie` / `norepinephrine mv` | `ie.stay_id = mv.stay_id` and `mv.starttime >= intime - 6 h` and `mv.starttime <= intime + 1 day` |
| `vaso_stg` epinephrine branch | `INNER JOIN` | `icustays ie` / `epinephrine mv` | Same stay and inclusive starttime window |
| `vaso_stg` dobutamine branch | `INNER JOIN` | `icustays ie` / `dobutamine mv` | Same stay and inclusive starttime window |
| `vaso_stg` dopamine branch | `INNER JOIN` | `icustays ie` / `dopamine mv` | Same stay and inclusive starttime window |
| `vaso_mv` | `LEFT JOIN` | `icustays ie` / local `vaso_stg v` | `ie.stay_id = v.stay_id` |
| `pafi1` blood gas | `LEFT JOIN` | `icustays ie` / `bg` | `ie.subject_id = bg.subject_id`, closed `[-6 h,+1 day]` charttime window, `bg.specimen = 'ART.'` |
| `pafi1` ventilation | `LEFT JOIN` | `icustays ie` / `ventilation vd` | `ie.stay_id = vd.stay_id`, `bg.charttime` between `vd.starttime` and `vd.endtime` inclusive, `vd.ventilation_status = 'InvasiveVent'` |
| `scorecomp` vaso rates | `LEFT JOIN` | `icustays ie` / `vaso_mv mv` | `ie.stay_id = mv.stay_id` |
| `scorecomp` P/F ratios | `LEFT JOIN` | `icustays ie` / `pafi2 pf` | `ie.stay_id = pf.stay_id` |
| `scorecomp` vitals | `LEFT JOIN` | `icustays ie` / `first_day_vitalsign v` | `ie.stay_id = v.stay_id` |
| `scorecomp` labs | `LEFT JOIN` | `icustays ie` / `first_day_lab l` | `ie.stay_id = l.stay_id` |
| `scorecomp` urine | `LEFT JOIN` | `icustays ie` / `first_day_urine_output uo` | `ie.stay_id = uo.stay_id` |
| `scorecomp` GCS | `LEFT JOIN` | `icustays ie` / `first_day_gcs gcs` | `ie.stay_id = gcs.stay_id` |
| Final query | `LEFT JOIN` | `icustays ie` / `scorecalc s` | `ie.stay_id = s.stay_id` |

The final LEFT JOIN preserves every `icustays` row, including stays with no
score inputs. The four medication INNER JOINs only build the optional
`vaso_stg` relation; `vaso_mv` is left-joined back to all stays, so absence of
a medication does not remove a stay.

## 5. `mimiciv_derived` dependencies

All ten DAG dependencies are direct source-table dependencies of this query.
They must be ported first and are available to candidate SQL under these
unqualified stems:

```text
bg
dobutamine
dopamine
epinephrine
first_day_gcs
first_day_lab
first_day_urine_output
first_day_vitalsign
norepinephrine
ventilation
```

The exact consumer read-set is the table in the dependency-column section
above. No dependency's raw item filters, FHIR extraction, or clinical
calculation should be copied into this concept. In particular:

- `bg` already owns its blood-gas item selection, numeric cleaning, specimen
  text, and `pao2fio2ratio` derivation.
- Each medication dependency already owns its exact ICU inputevent item
  selection and `vaso_rate` derivation.
- `ventilation` already owns the event-grid, device/mode classification, and
  interval construction; this consumer only tests interval membership and the
  exact status `InvasiveVent`.
- The four `first_day_*` dependencies already own their respective upstream
  item selection, time windows, and aggregates; this consumer reads only the
  named stay-level outputs.

## 6. Literal code and discriminator specification — verbatim

### Direct coded filters in `first_day_sofa.sql`

There are no direct numeric `itemid`, `icd_code`/`icd_version`, LOINC, or
explicit coding-system filters in this file. Therefore the direct numeric
item/code set is empty, and there are no dead direct coded filters to report.
The exact dependency-owned item/code sets are not repeated in this consumer;
they remain specifications of the ten dependency concepts.

The target does contain these exact string discriminator literals:

| Exact literal(s), copied from SQL | Source table/relation filtered | Predicate/role | Feeds |
|---|---|---|---|
| `'norepinephrine'` | local CTE `vaso_stg` | `CASE WHEN treatment = 'norepinephrine'` in `vaso_mv` | `rate_norepinephrine`, then cardiovascular |
| `'epinephrine'` | local CTE `vaso_stg` | `CASE WHEN treatment = 'epinephrine'` in `vaso_mv` | `rate_epinephrine`, then cardiovascular |
| `'dopamine'` | local CTE `vaso_stg` | `CASE WHEN treatment = 'dopamine'` in `vaso_mv` | `rate_dopamine`, then cardiovascular |
| `'dobutamine'` | local CTE `vaso_stg` | `CASE WHEN treatment = 'dobutamine'` in `vaso_mv` | `rate_dobutamine`, then cardiovascular |
| `'ART.'` | `mimiciv_derived.bg` | `bg.specimen = 'ART.'` in `pafi1` LEFT JOIN | `pafi1` arterial P/F rows, then respiration |
| `'InvasiveVent'` | `mimiciv_derived.ventilation` | `vd.ventilation_status = 'InvasiveVent'` in `pafi1` LEFT JOIN | `isvent`, `pao2fio2_vent_min`, and respiration |

The four treatment strings are labels generated by this SQL, not source
`itemid` values. They must not be translated to drug labels or expanded. The
ventilation/status and specimen strings are also exact equality values;
trailing punctuation/spaces would change the branches. No code system URI is
named by this canonical file.

### Numeric threshold literals

For completeness, the exact numeric literals in the component CASE logic are
listed here because they are value discriminators that feed clinically
meaningful output, even though they are not coded filters:

```text
Respiration: 100, 200, 300, 400
Coagulation: 20, 50, 100, 150
Liver: 12.0, 6.0, 2.0, 1.2
Cardiovascular: 15, 0.1, 5, 0.1, 0, 70
CNS: 13, 14, 10, 12, 6, 9, 6
Renal: 5.0, 200, 4, 3.5, 500, 3, 2.0, 1.2, 2.0
```

The repeated values above are retained as they occur in the source branch
conditions; the executable SQL is authoritative for order and comparison
operators. `1` and `0` in `isvent`, the `ELSE` score values, and final
`COALESCE(..., 0)` are also exact SQL literals.

### Dependency code boundary

The source SQL names no dependency itemids. The upstream item/code literals
must be taken verbatim from the canonical SQL of each dependency and kept
inside that dependency's port. They are not additional filters for
`first_day_sofa`, and this consumer must not infer, translate, or replace them.
In particular, a zero count for an upstream item in a served cohort would not
justify dropping its literal from the upstream code specification.

## 7. Aggregations, windows, and row semantics

There are no window functions in `first_day_sofa.sql`, no `ORDER BY`, no
`DISTINCT`, and no `HAVING`.

Aggregations are:

1. `vaso_mv` groups by `ie.stay_id` and uses four conditional `MAX` values to
   retain the maximum observed `vaso_rate` for each treatment in the
   medication window.
2. `pafi2` groups by `stay_id` and uses two conditional `MIN` values, keeping
   separate minima for rows classified as ventilated and non-ventilated.
3. `scorecalc` uses no aggregate; it converts the stay-level component inputs
   into six integer CASE scores.
4. The final SELECT uses no aggregate; it sums the six component scores after
   null-to-zero imputation.

The source natural grain is one output row per `mimiciv_icu.icustays.stay_id`.
`stay_id` is the manifest's empirical comparison key. `subject_id` and
`hadm_id` are identifying attributes for that ICU stay; they are not the
comparison key. All intermediate branches are designed to collapse back to
stay-level values before `scorecomp`, while the final left-side ICU stay spine
preserves stays with entirely missing source measurements.

## 8. Semantically essential inputs

These are fields/discriminators whose values can change row inclusion, the
natural grain, grouping, temporal membership, or a clinically meaningful
derived output.

### Direct `icustays` inputs

1. **`stay_id`** is the final natural/comparison key, the partition/group key
   for medication and P/F branches, and every dependency join key. Changing it
   can move data between stays or change the output row identity.
2. **`subject_id`** is emitted and is also the equality key for the `bg` join.
   It is therefore not merely descriptive: changing it changes which blood gas
   rows can enter `pafi1` and the respiration result.
3. **`hadm_id`** is emitted as a final value. It does not control inclusion or
   score calculations in this SQL, but it is part of the required source output
   and must remain associated with the correct stay.
4. **`intime`** controls all medication starttime windows and the blood-gas
   charttime window. It is the temporal anchor for every first-day inclusion
   decision in this consumer.

### Dependency inputs

5. **Medication `stay_id` and `starttime`** control medication-row
   association and inclusion in the closed `[-6 hours, +1 day]` window.
6. **Medication `vaso_rate`** is aggregated by treatment and compared with the
   cardiovascular thresholds. Its value can change `rate_*`, the
   cardiovascular component, and the final `sofa`.
7. **`bg.subject_id`, `bg.charttime`, `bg.specimen`, and
   `bg.pao2fio2ratio`** control arterial-gas inclusion, its temporal overlap
   with ventilation, and the separate ventilated/non-ventilated minima.
8. **Ventilation `stay_id`, `starttime`, `endtime`, and
   `ventilation_status`** control whether each arterial gas is labelled
   `isvent = 1`; that changes which P/F minimum is populated and can change
   `respiration`.
9. **`first_day_vitalsign.mbp_min`** controls the hypotension cardiovascular
   branch when the vasoactive branches do not already fire.
10. **`first_day_lab.creatinine_max`** controls the renal score; its
    `bilirubin_total_max` controls liver; its `platelets_min` controls
    coagulation. Their NULLs also control whether those components are NULL.
11. **`first_day_urine_output.urineoutput`** controls the renal low-output
    branches and its NULL fallback.
12. **`first_day_gcs.gcs_min`** controls the CNS CASE branch and its NULL
    behavior.

### Control-flow and precedence inputs

13. The exact order of each CASE is essential. For example, renal checks
    creatinine and urine-output branches in a fixed order, cardiovascular
    checks high vasoactive rates before lower-rate branches, and respiration
    checks ventilated minima before non-ventilated minima.
14. The presence/absence of a dependency row is semantically meaningful. The
    component CASEs preserve NULL for missing input, while the final total
    deliberately maps each missing component to zero.
15. `pao2fio2_novent_min` and `pao2fio2_vent_min` must remain separate; using a
    single minimum would change the ventilation-dependent respiration branch.

## 9. Representability risks for a MIMIC-on-FHIR port

These are mapping risks to verify against the served FHIR/dependency data, not
terminal decisions by this source-analysis stage.

1. **ICU-stay spine and identifiers.** `subject_id` and `stay_id` are carried
   by FHIR identifier values as strings, while `intime` is represented by ICU
   `Encounter.period.start`. The candidate must associate the ICU Encounter
   stream using the exact ICU identifier system and cast identifier values to
   the required integer outputs. The ICU Encounter's opaque key is required as
   `icu_encounter_key`; it cannot replace the integer `stay_id` and cannot be
   parsed. The manifest also requires `patient_key` and hospital
   `encounter_key` as opaque equality keys.
2. **`hadm_id` is a separate hospital-admission identifier.** It is not the
   ICU `stay_id`. A port needs the hospital Encounter identifier and its
   relationship to the ICU Encounter (normally the ICU Encounter's
   `partOf`) to reproduce `hadm_id`. The curated notes report that ICU
   Encounter-to-hospital admission links are populated in the checked demo,
   but this association must be probed rather than inferred from Encounter
   class or a resource id.
3. **Temporal anchors are essential.** Every first-day window depends on
   `intime`, and the P/F branch additionally depends on blood-gas and
   ventilation timestamps. FHIR datetimes include offsets and should be
   treated as MIMIC wall-clock values with `TIMESTAMP_NTZ`, not converted as
   real instants. The curated notes document historical upstream
   `TIMESTAMPTZ` normalization and its possible aggregate/window effects,
   while also recording that the 2026-08-21/24 UTC rebuild fixed the known
   spring-forward behavior. The served build/path still needs verification;
   an opaque resource id is never an allowed timestamp repair.
4. **Blood-gas arterial discriminator.** The consumer requires the exact
   dependency value `specimen = 'ART.'`; a missing specimen text or a port that
   groups only by patient/time can admit the wrong specimen class and alter the
   respiration score. The `bg` dependency's `pao2fio2ratio` must be consumed,
   not recomputed from a different FHIR subset.
5. **Ventilation interval/status.** `ventilation_status = 'InvasiveVent'`
   and inclusive interval overlap determine `isvent`. Loss of ventilator mode
   or oxygen-device text, charttime, or interval endpoints can change the
   ventilated/non-ventilated P/F minima and therefore a clinically meaningful
   output. Current sibling notes report that rebuilt chartevents preserve the
   distinct ventilator text in `component.valueString`; this is a dependency
   fact to recheck, not a reason to inline ventilation here.
6. **GCS discriminator is upstream but essential.** The first-day GCS value
   can depend on the `No Response-ETT` versus `No Response` chartevents text.
   The curated notes say the numeric-row text representation was repaired in
   the rebuilt warehouse. The dependency must be verified against the served
   build; this consumer must not rederive GCS or use an opaque Observation id
   to recover the distinction.
7. **Lab values and effective time.** `first_day_lab` supplies extrema that
   are directly thresholded here. Its labevents numeric/comparator handling,
   effective time, patient association, and inclusive first-day window are
   upstream contracts. A missing numeric value or shifted charttime can alter
   `creatinine_max`, `bilirubin_total_max`, or `platelets_min`, not just an
   ancillary timestamp.
8. **Urine total and time-window aggregation.** `first_day_urine_output`
   supplies a first-day sum that is directly thresholded. Its outputevents
   charttime and sum must be consumed as a completed dependency. A missing or
   transformed event can change both the sum and the renal branch; do not
   replace the dependency with a FHIR-side estimate.
9. **Medication timing and rate choice.** ICU MedicationAdministration
   `effective[x]` can be a Period for rate-bearing rows and only an endtime
   dateTime for null-rate rows. Because this consumer filters dependency rows
   on `starttime`, a dependency that cannot preserve starttime for rows where
   the FHIR ETL only serves endtime may lose the inclusion discriminator.
   `vaso_rate` is also thresholded, and ICU Quantity values are served at
   decimal scale six; borderline rates need the dependency's exact source
   semantics. `linkorderid` is absent from ICU MedicationAdministration, but
   this consumer does not read it, so it is not a direct first-day SOFA value
   input; it must not be invented or used as a substitute for starttime.
10. **Dependency key interface.** The loop's dependency preprocessing may
    strip integer `subject_id`/`stay_id` columns when paired opaque resource
    keys are present. The semantic source joins must then be implemented with
    equality on the published `patient_key`/`icu_encounter_key` interface and
    the ICU Encounter/Patient identifier values recovered by ordinary FHIR
    joins. No resource id may be parsed, regenerated, brute-forced, or used as
    a clinical side channel.
11. **Missing inputs versus score imputation.** A candidate must preserve the
    distinction between NULL component outputs and the final total's
    `COALESCE(..., 0)`. Emitting zero prematurely would erase the source's
    missingness diagnostics and could also change downstream comparison of the
    named component columns.

## Evidence and file checks used for this analysis

Read before analysis:

- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`.
- Relevant fragments: `first_day_bg.md`, `first_day_gcs.md`,
  `first_day_urine_output.md`, `first_day_vitalsign.md`, `dobutamine.md`,
  `dopamine.md`, `epinephrine.md`, `norepinephrine.md`, `ventilation.md`,
  `chemistry.md`, `complete_blood_count.md`, `coagulation.md`,
  `blood_differential.md`, `urine_output.md`, `vitalsign.md`, `gcs.md`,
  `icustay_times.md`, `oxygen_delivery.md`, and `ventilator_setting.md`.
  `bg.md`, `first_day_lab.md`, and `enzyme.md` do not exist as fragments; the
  corresponding dependency carryover/source analyses were read where present.
- Relevant dependency carryovers: source analyses for `bg`, `dobutamine`,
  `dopamine`, `epinephrine`, `norepinephrine`, `first_day_gcs`,
  `first_day_lab`, `first_day_urine_output`, `first_day_vitalsign`, and
  `ventilation`; the dependency FHIR-prober carryovers for the last three and
  `ventilation` were also consulted for representability leads.
- `mimic-iv/concept_dag/concept_dag.json` and
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.
- `mimic-iv/buildmimic/postgres/create.sql` for `icustays` types.

Checks performed:

- Confirmed the DAG path, dependency list, level, and SHA256; the canonical
  SQL hash matched the DAG value.
- Enumerated every physical `FROM`/`JOIN`, every local CTE relation, every
  selected/referenced column, all join predicates, all join-window bounds,
  all CASE thresholds, all aggregates, and the final output order.
- Confirmed that the target has no `WHERE` clause and no direct numeric coded
  filter; copied the exact string discriminators and dependency read-set.
- Confirmed the manifest key/output shape and distinguished its required FHIR
  key columns from the canonical SQL's ten source output columns.

## Summary

`first_day_sofa` is a level-2, stay-grain score over an ICU-stay spine. It
windows four vasoactive medication dependencies and arterial blood gases around
`intime`, overlays arterial gases with invasive-ventilation intervals, joins
four first-day component dependencies by `stay_id`, computes six thresholded
organ scores, and sums NULL components as zero. Its key risks are preserving
the dependency boundaries, ICU/hospital/patient identity, inclusive temporal
windows, exact arterial and invasive-ventilation discriminators, and all
upstream values that can change a score branch.
