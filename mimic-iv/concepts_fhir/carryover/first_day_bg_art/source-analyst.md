# Source analysis: `first_day_bg_art`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_bg_art.sql`.
- DAG stem: `first_day_bg_art`.
- DAG path: `firstday/first_day_bg_art.sql`.
- DAG SHA256: `f3ef6de5f9b071736c19bc27eedeb2509173d9084019ced555ac8dc882683fac`.
- DAG level: `1`.
- DAG dependency: `bg` (`measurement/bg.sql`, level `0`). The DAG also lists
  `sirs` as a dependent.
- The DAG checker reported that the stored DAG matches the generated artifacts,
  and `depcheck first_day_bg_art` reported that `bg` is completed.

The target SQL is a single aggregate query: it has no CTEs, subqueries, or
intermediate result relations. The comment describes highest/lowest values for
arterial blood specimens.

## Table references

Every relation in the target SQL is:

1. `FROM physionet-data.mimiciv_icu.icustays AS ie` (raw schema
   `mimiciv_icu`, table `icustays`; source line 29).
2. `LEFT JOIN physionet-data.mimiciv_derived.bg AS bg` (derived dependency
   schema `mimiciv_derived`, table `bg`; source line 30).

There are no `mimiciv_hosp` tables and no other raw tables. In the candidate,
the dependency must be consumed as the completed unqualified Spark view
`bg` (for example, `FROM bg`); do not rederive this dependency from FHIR or
inline the producer's labevents/chartevents logic.

## Join and row-inclusion predicates

The only join is a `LEFT JOIN`, with the complete `ON` condition (source lines
31-35):

```sql
ie.subject_id = bg.subject_id
AND bg.specimen = 'ART.'
AND bg.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
AND bg.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

All four predicates are in `ON`, not `WHERE`. Therefore every ICU stay in
`icustays` remains in the pre-aggregation join result, including stays with no
matching arterial blood gas row; such a stay produces NULL aggregate values.
The blood-gas time window is inclusive on both ends: from six hours before
`ie.intime` through one day after `ie.intime`.

There is no `WHERE` clause in this concept and no other value or time filter.
There are no window functions or temporal carry-forward operations.

## Literal code/discriminator specification

The target names no `itemid`, `icd_code`, or other numeric code and names no
coding system. Its only coded/discrete literal is:

| Exact SQL literal | Source table and column | Feeds |
|---|---|---|
| `'ART.'` | completed dependency `mimiciv_derived.bg.specimen` | the `LEFT JOIN` row-inclusion branch; consequently all aggregate output columns |

The literal is copied verbatim, including the period. The `itemid` literals
used by the producer `measurement/bg.sql` belong to the `bg` dependency's own
code specification; they are not filters in this consumer and must not be
reimplemented here.

## Dependency boundary and exact columns consumed from `bg`

The consumer reads exactly these dependency columns (the measure names are
unqualified in the source SELECT but resolve to `bg`):

- `bg.subject_id`: join key.
- `bg.specimen`: arterial discriminator used by the literal filter above.
- `bg.charttime`: temporal join key/window input.
- `bg.lactate` → `lactate_min`, `lactate_max`.
- `bg.ph` → `ph_min`, `ph_max`.
- `bg.so2` → `so2_min`, `so2_max`.
- `bg.po2` → `po2_min`, `po2_max`.
- `bg.pco2` → `pco2_min`, `pco2_max`.
- `bg.aado2` → `aado2_min`, `aado2_max`.
- `bg.aado2_calc` → `aado2_calc_min`, `aado2_calc_max`.
- `bg.pao2fio2ratio` → `pao2fio2ratio_min`, `pao2fio2ratio_max`.
- `bg.baseexcess` → `baseexcess_min`, `baseexcess_max`.
- `bg.bicarbonate` → `bicarbonate_min`, `bicarbonate_max`.
- `bg.totalco2` → `totalco2_min`, `totalco2_max`.
- `bg.hematocrit` → `hematocrit_min`, `hematocrit_max`.
- `bg.hemoglobin` → `hemoglobin_min`, `hemoglobin_max`.
- `bg.carboxyhemoglobin` → `carboxyhemoglobin_min`,
  `carboxyhemoglobin_max`.
- `bg.methemoglobin` → `methemoglobin_min`, `methemoglobin_max`.
- `bg.temperature` → `temperature_min`, `temperature_max`.
- `bg.chloride` → `chloride_min`, `chloride_max`.
- `bg.calcium` → `calcium_min`, `calcium_max`.
- `bg.glucose` → `glucose_min`, `glucose_max`.
- `bg.potassium` → `potassium_min`, `potassium_max`.
- `bg.sodium` → `sodium_min`, `sodium_max`.

The consumer does **not** read `bg.hadm_id`, `bg.storetime`, `bg.specimen_id`,
or any other producer column. The producer's specimen-level grain and its
itemid filtering/calculations are upstream dependency behavior, not logic to
rederive in this target.

## Source columns and inferred types

Columns read from `mimiciv_icu.icustays`:

- `ie.subject_id`: integer identifier; selected, grouped, and used in the
  dependency join.
- `ie.stay_id`: integer ICU-stay identifier; selected and grouped.
- `ie.intime`: datetime/timestamp; not selected, but supplies both inclusive
  time-window bounds in the join.

Columns read from the completed `bg` view are listed above. Inferred types are:

- `bg.subject_id`: integer identifier.
- `bg.specimen`: string/text discriminator.
- `bg.charttime`: datetime/timestamp.
- All 21 measurement columns (`lactate`, `ph`, `so2`, `po2`, `pco2`, `aado2`,
  `aado2_calc`, `pao2fio2ratio`, `baseexcess`, `bicarbonate`, `totalco2`,
  `hematocrit`, `hemoglobin`, `carboxyhemoglobin`, `methemoglobin`,
  `temperature`, `chloride`, `calcium`, `glucose`, `potassium`, and `sodium`):
  nullable numeric values. Exact precision/scale is inherited from the
  completed `bg` dependency.

## Output schema and aggregation

The query groups by `ie.subject_id, ie.stay_id` (source line 36), so the
natural grain/key is one row per `(subject_id, stay_id)` ICU stay. `MIN` and
`MAX` ignore NULL input values and preserve the numeric type of each input;
every aggregate is nullable, including for a stay with no qualifying arterial
rows. There are no `GROUP BY` expressions beyond the two key columns and no
window, `DISTINCT`, or other aggregation.

The final output has 44 columns: two integer key columns followed by 42
nullable numeric extrema columns, in this order:

1. `subject_id` — `ie.subject_id`, integer.
2. `stay_id` — `ie.stay_id`, integer.
3. `lactate_min`, `lactate_max` — `MIN(bg.lactate)`, `MAX(bg.lactate)`.
4. `ph_min`, `ph_max` — `MIN(bg.ph)`, `MAX(bg.ph)`.
5. `so2_min`, `so2_max` — `MIN(bg.so2)`, `MAX(bg.so2)`.
6. `po2_min`, `po2_max` — `MIN(bg.po2)`, `MAX(bg.po2)`.
7. `pco2_min`, `pco2_max` — `MIN(bg.pco2)`, `MAX(bg.pco2)`.
8. `aado2_min`, `aado2_max` — `MIN(bg.aado2)`, `MAX(bg.aado2)`.
9. `aado2_calc_min`, `aado2_calc_max` — `MIN(bg.aado2_calc)`,
   `MAX(bg.aado2_calc)`.
10. `pao2fio2ratio_min`, `pao2fio2ratio_max` — `MIN(bg.pao2fio2ratio)`,
    `MAX(bg.pao2fio2ratio)`.
11. `baseexcess_min`, `baseexcess_max` — `MIN(bg.baseexcess)`,
    `MAX(bg.baseexcess)`.
12. `bicarbonate_min`, `bicarbonate_max` — `MIN(bg.bicarbonate)`,
    `MAX(bg.bicarbonate)`.
13. `totalco2_min`, `totalco2_max` — `MIN(bg.totalco2)`, `MAX(bg.totalco2)`.
14. `hematocrit_min`, `hematocrit_max` — `MIN(bg.hematocrit)`,
    `MAX(bg.hematocrit)`.
15. `hemoglobin_min`, `hemoglobin_max` — `MIN(bg.hemoglobin)`,
    `MAX(bg.hemoglobin)`.
16. `carboxyhemoglobin_min`, `carboxyhemoglobin_max` —
    `MIN(bg.carboxyhemoglobin)`, `MAX(bg.carboxyhemoglobin)`.
17. `methemoglobin_min`, `methemoglobin_max` — `MIN(bg.methemoglobin)`,
    `MAX(bg.methemoglobin)`.
18. `temperature_min`, `temperature_max` — `MIN(bg.temperature)`,
    `MAX(bg.temperature)`.
19. `chloride_min`, `chloride_max` — `MIN(bg.chloride)`, `MAX(bg.chloride)`.
20. `calcium_min`, `calcium_max` — `MIN(bg.calcium)`, `MAX(bg.calcium)`.
21. `glucose_min`, `glucose_max` — `MIN(bg.glucose)`, `MAX(bg.glucose)`.
22. `potassium_min`, `potassium_max` — `MIN(bg.potassium)`,
    `MAX(bg.potassium)`.
23. `sodium_min`, `sodium_max` — `MIN(bg.sodium)`, `MAX(bg.sodium)`.

## Semantically essential inputs

The following source values can change inclusion, grain, or clinically
meaningful output:

- `ie.subject_id` and `ie.stay_id`: define the output natural key and grouping;
  `subject_id` also controls which dependency rows can join.
- `ie.intime`: controls the inclusive `[-6 hours, +1 day]` arterial blood-gas
  window and therefore which rows contribute to every extrema.
- `bg.subject_id`: controls the patient/stay join and row inclusion.
- `bg.specimen`: controls the arterial-only branch through the exact literal
  `'ART.'`; it is not emitted.
- `bg.charttime`: controls temporal inclusion at both inclusive window bounds.
- Each of the 21 numeric `bg` measure columns: its non-NULL values can change
  the corresponding MIN/MAX pair; if all qualifying values are NULL, that
  pair remains NULL. The output is not a single selected measurement but an
  aggregate over all qualifying dependency rows.
- The `LEFT JOIN` type itself is semantically essential: changing it to an
  inner join would remove ICU stays with no qualifying arterial blood gas and
  change row inclusion.

There is no carry-forward, window ranking, code translation, clinical rule, or
additional derived calculation in this consumer. The only temporal behavior is
the join window; all blood-gas pivoting and value calculations are owned by the
completed `bg` dependency.

## Notes consulted

Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, including the notes on lab
specimen/time joins and labevents DST normalization. Read
`MIMIC_NOTES.d/first_day_bg.md` only as a provisional sibling lead; it was not
used as verdict evidence and does not alter the source-SQL facts above. The
notes reinforce that a time-window aggregate is sensitive to the upstream
`bg.charttime` representation, but this analysis makes no FHIR
representability or terminal-equivalence decision.
