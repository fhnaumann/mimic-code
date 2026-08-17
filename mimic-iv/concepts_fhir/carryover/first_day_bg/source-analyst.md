# Source Analysis: `first_day_bg`

**Concept:** `first_day_bg`  
**Canonical SQL:** `mimic-iv/concepts/firstday/first_day_bg.sql`  
**DAG path:** `firstday/first_day_bg.sql`  
**DAG level:** 1  
**DAG SHA256:** `3c2ff855bc1fea224d78c50e5905f652e100d75857ef9cf909be8fc10e92a352`  
**SHA256 checked against the SQL on disk:** match  
**DAG dependencies:** `bg` only  
**Oracle manifest:** 44 columns, 73,181 rows, `comparison: keyed_join`, natural key
`stay_id`.

The SQL has one SELECT, no CTEs, and no intermediate named relations. Its
source text is BigQuery-qualified (`physionet-data.mimiciv_icu.icustays` and
`physionet-data.mimiciv_derived.bg`); the logical schemas used by this repo are
`mimiciv_icu` and `mimiciv_derived`.

## 1. Table references

| Clause | Logical schema | Table | Alias | Role |
|---|---|---|---|---|
| `FROM` | `mimiciv_icu` | `icustays` | `ie` | One driving row per ICU stay; supplies IDs and `intime`. |
| `LEFT JOIN` | `mimiciv_derived` | `bg` | `bg` | Ported `bg` concept; supplies blood-gas measurements and chart time. |

There are no `mimiciv_hosp` tables directly referenced by this consumer. The
raw tables behind the derived `bg` concept are not additional tables for this
SQL and must not be re-derived here. `bg` is available to candidate SQL under
the unqualified dependency stem `bg` after dependency preprocessing.

## 2. Columns referenced and inferred types

There are no intermediate CTE columns. The final query references these source
columns:

### `mimiciv_icu.icustays ie`

| Column | Inferred/source type | Use |
|---|---|---|
| `subject_id` | `INTEGER` | Selected; GROUP BY column; equality side of the join. |
| `stay_id` | `INTEGER` | Selected; GROUP BY column; natural ICU-stay grain/key. |
| `intime` | `TIMESTAMP`/datetime | Lower and upper bound for the blood-gas time window; not selected. |

### Dependency `mimiciv_derived.bg bg`

These are the **exact dependency columns read by `first_day_bg`**. The
dependency output types are taken from the `bg` oracle manifest/source
analysis.

| Column | Type | Use |
|---|---|---|
| `subject_id` | `INTEGER` | Join predicate. |
| `charttime` | `TIMESTAMP` | Inclusive temporal join predicates. |
| `lactate` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `ph` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `so2` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `po2` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `pco2` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `aado2` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `aado2_calc` | `DECIMAL(38,4)` | `MIN`/`MAX` output pair. |
| `pao2fio2ratio` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `baseexcess` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `bicarbonate` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `totalco2` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `hematocrit` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `hemoglobin` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `carboxyhemoglobin` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `methemoglobin` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `temperature` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `chloride` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `calcium` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `glucose` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `potassium` | `DOUBLE` | `MIN`/`MAX` output pair. |
| `sodium` | `DOUBLE` | `MIN`/`MAX` output pair. |

The dependency columns present in `bg` but **not read** by this SQL are
`hadm_id`, `specimen`, `fio2_chartevents`, and `fio2`. In particular,
`first_day_bg` does not read `bg.specimen` or use the `bg` specimen grouping
key; it consumes the already-derived `bg` rows and aggregates them per ICU
stay.

## 3. Join and temporal predicates

The only join is an inclusive `LEFT JOIN`:

```sql
FROM `physionet-data.mimiciv_icu.icustays` ie
LEFT JOIN `physionet-data.mimiciv_derived.bg` bg
  ON ie.subject_id = bg.subject_id
 AND bg.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
 AND bg.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

The join admits `bg` rows for the same `subject_id` whose `charttime` is from
6 hours before `ie.intime` through 1 day after `ie.intime`, inclusive at both
ends. This is a 30-hour inclusive interval relative to `intime`. There is no
join on `stay_id`, `hadm_id`, `specimen`, or any ICU encounter time other than
`intime`; consequently, the SQL's row inclusion is controlled by patient ID
and the time window, not by a stay ID carried by `bg`.

Because the join is left-sided, every `icustays` row remains represented even
when no dependency row matches. For such a stay, the aggregate measurement
columns are NULL. Multiple matching `bg` rows contribute to the same stay's
aggregates.

## 4. Filters

There is **no `WHERE` clause** and therefore no standalone row filter,
itemid filter, value constraint, code exclusion, or time filter outside the
join. The two temporal predicates in the `ON` clause above are the complete
row-inclusion window.

There are no `HAVING`, `QUALIFY`, or post-aggregation filters.

## 5. Literal code set

`first_day_bg.sql` names **no coded filters**. It contains no `itemid`,
`icd_code`/`icd_version`, LOINC, or other code literals. Therefore the literal
code set for this consumer is empty.

The dependency `bg` owns its own literal itemid filters over its raw lab and
chart sources. Those are not filters in `first_day_bg.sql`; `first_day_bg`
must consume the completed `bg` dependency rather than re-derive or
re-specify that code set. The exact dependency code specification is recorded
in `mimic-iv/concepts_fhir/carryover/bg/source-analyst.md`.

## 6. Aggregations, grouping, ordering, and windows

The query groups by:

```sql
GROUP BY ie.subject_id, ie.stay_id
```

It applies `MIN` and `MAX` independently to every consumed measurement
column. There are no SQL window functions, no `ORDER BY`, and no explicit
row-level ordering. The only “window” is the temporal range in the join.

`MIN`/`MAX` produce one aggregate pair per grouping key and ignore NULL input
values under ordinary SQL aggregate semantics. The `aado2_calc` pair retains
the dependency's `DECIMAL(38,4)` type; every other aggregate pair is `DOUBLE`.

## 7. Final output columns and types, in SQL order

| # | Output column | Type |
|---:|---|---|
| 1 | `subject_id` | `INTEGER` |
| 2 | `stay_id` | `INTEGER` |
| 3 | `lactate_min` | `DOUBLE` |
| 4 | `lactate_max` | `DOUBLE` |
| 5 | `ph_min` | `DOUBLE` |
| 6 | `ph_max` | `DOUBLE` |
| 7 | `so2_min` | `DOUBLE` |
| 8 | `so2_max` | `DOUBLE` |
| 9 | `po2_min` | `DOUBLE` |
| 10 | `po2_max` | `DOUBLE` |
| 11 | `pco2_min` | `DOUBLE` |
| 12 | `pco2_max` | `DOUBLE` |
| 13 | `aado2_min` | `DOUBLE` |
| 14 | `aado2_max` | `DOUBLE` |
| 15 | `aado2_calc_min` | `DECIMAL(38,4)` |
| 16 | `aado2_calc_max` | `DECIMAL(38,4)` |
| 17 | `pao2fio2ratio_min` | `DOUBLE` |
| 18 | `pao2fio2ratio_max` | `DOUBLE` |
| 19 | `baseexcess_min` | `DOUBLE` |
| 20 | `baseexcess_max` | `DOUBLE` |
| 21 | `bicarbonate_min` | `DOUBLE` |
| 22 | `bicarbonate_max` | `DOUBLE` |
| 23 | `totalco2_min` | `DOUBLE` |
| 24 | `totalco2_max` | `DOUBLE` |
| 25 | `hematocrit_min` | `DOUBLE` |
| 26 | `hematocrit_max` | `DOUBLE` |
| 27 | `hemoglobin_min` | `DOUBLE` |
| 28 | `hemoglobin_max` | `DOUBLE` |
| 29 | `carboxyhemoglobin_min` | `DOUBLE` |
| 30 | `carboxyhemoglobin_max` | `DOUBLE` |
| 31 | `methemoglobin_min` | `DOUBLE` |
| 32 | `methemoglobin_max` | `DOUBLE` |
| 33 | `temperature_min` | `DOUBLE` |
| 34 | `temperature_max` | `DOUBLE` |
| 35 | `chloride_min` | `DOUBLE` |
| 36 | `chloride_max` | `DOUBLE` |
| 37 | `calcium_min` | `DOUBLE` |
| 38 | `calcium_max` | `DOUBLE` |
| 39 | `glucose_min` | `DOUBLE` |
| 40 | `glucose_max` | `DOUBLE` |
| 41 | `potassium_min` | `DOUBLE` |
| 42 | `potassium_max` | `DOUBLE` |
| 43 | `sodium_min` | `DOUBLE` |
| 44 | `sodium_max` | `DOUBLE` |

Each pair is directly `MIN(bg.<field>)` / `MAX(bg.<field>)`, except the two
ID columns, which are the grouped `ie` columns.

## 8. Natural grain and comparison identity

The SQL's natural grain is one row per `(ie.subject_id, ie.stay_id)` group,
representing an ICU stay. The oracle manifest declares `stay_id` as the
comparison key, with `subject_id` retained as an output column. The output has
44 columns and 73,181 oracle rows. No source `bg` measurement row is itself a
final output row; all matching measurements are collapsed into the stay-level
min/max aggregates.

## 9. Semantically essential inputs

The following inputs can change row inclusion, the natural key/grain, or a
clinically meaningful derived value:

| Input | Controlled behavior | Affected output/branch |
|---|---|---|
| `ie.subject_id` | Groups the driving ICU stay and restricts the dependency join to the same patient. | Output `subject_id`; all 42 measurement aggregates for that group. |
| `ie.stay_id` | Defines the ICU-stay grouping and output identity. | Output `stay_id`; all aggregate columns. |
| `ie.intime` | Sets both inclusive join bounds. Changing it changes which `bg` rows contribute. | All aggregate outputs; stays with no matches remain because of the LEFT JOIN. |
| `bg.subject_id` | Must equal `ie.subject_id` for a dependency row to contribute. | All aggregate outputs for the affected stay. |
| `bg.charttime` | Determines whether each dependency row lies in the `intime - 6 hours` through `intime + 1 day` interval. | All aggregate outputs; it is not itself output. |
| Each of `bg.lactate`, `ph`, `so2`, `po2`, `pco2`, `aado2`, `aado2_calc`, `pao2fio2ratio`, `baseexcess`, `bicarbonate`, `totalco2`, `hematocrit`, `hemoglobin`, `carboxyhemoglobin`, `methemoglobin`, `temperature`, `chloride`, `calcium`, `glucose`, `potassium`, and `sodium` | Supplies the values over which that field's MIN and MAX are computed. | Its corresponding `_min` and `_max` output columns. |

The dependency's `hadm_id`, `specimen`, `fio2_chartevents`, and `fio2` cannot
change this consumer's result because they are not referenced. The SQL also
does not independently discriminate arterial, venous, or mixed specimens;
all such rows already admitted by the `bg` dependency and the time join feed
the same stay-level aggregates.

## 10. Notes and dependency evidence read

I read `MIMIC_NOTES.md` and the provisional lab-related fragments
`MIMIC_NOTES.d/chemistry.md`, `coagulation.md`,
`complete_blood_count.md`, `blood_differential.md`, and
`cardiac_marker.md`, treating fragment claims as unconfirmed leads. The
cross-concept notes relevant here are that `bg` is a derived lab/chart
measurement stream, lab encounter references are incomplete, specimen/time
and identifier behavior must not be used to alter the canonical relational
grain, and essential missing temporal/grouping inputs would affect the whole
derived concept. I also read the completed dependency analysis at
`carryover/bg/source-analyst.md` and its probe at
`carryover/bg/fhir-prober.md` to identify the exact `bg` interface; those
dependency facts do not add filters or tables to this consumer.

## Summary

`first_day_bg` is a level-1, `bg`-dependent, stay-level aggregate. It
left-joins each ICU stay to same-subject `bg` rows in the inclusive interval
from 6 hours before through 1 day after ICU `intime`, then emits min/max pairs
for 21 blood-gas fields. It has no coded filters, no WHERE clause, no SQL
window functions, and no ordering; its essential inputs are the ICU stay IDs
and `intime`, the dependency's `subject_id`/`charttime`, and the 21 consumed
measurement columns.
