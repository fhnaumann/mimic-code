# Source analysis: `sepsis3`

## Scope and DAG position

- Canonical source: `mimic-iv/concepts/sepsis/sepsis3.sql` (80 lines).
- The DAG node is stem `sepsis3`, path `sepsis/sepsis3.sql`, level 3.
- DAG SHA256: `1d06e0efed85220c8a9cfd27ee9ee50e4dfbbe7a4975a7d2f7af72a92766692a`.
  The SHA256 recomputed from the canonical SQL is identical.
- DAG dependencies are exactly `sofa` and `suspicion_of_infection`, both in
  the `mimiciv_derived` namespace. Their completed candidate outputs are
  available to downstream SQL under the unqualified stems `sofa` and
  `suspicion_of_infection`; this consumer must not rederive either dependency
  from FHIR resources.
- The canonical source contains no direct `mimiciv_hosp` or `mimiciv_icu`
  table reference. Raw hospital/ICU tables used upstream by those dependencies
  are not direct inputs to `sepsis3`.

## 1. Table references and joins

The project-qualified SQL names are written as
`physionet-data.mimiciv_derived.<table>`. The relevant schema is
`mimiciv_derived`.

| SQL location | Join type | Schema/table or CTE | Alias | Condition |
|---|---|---|---|---|
| `sofa` CTE, line 19 | `FROM` | `mimiciv_derived.sofa` | none in source | None; this is the SOFA dependency. |
| `s1`, line 54 | `FROM` | `mimiciv_derived.suspicion_of_infection` | `soi` | None; this is the suspicion dependency. |
| `s1`, lines 55--62 | `INNER JOIN` | the local `sofa` CTE | `sofa` | `soi.stay_id = sofa.stay_id` AND `sofa.endtime >= DATETIME_SUB(soi.suspected_infection_time, INTERVAL '48' HOUR)` AND `sofa.endtime <= DATETIME_ADD(soi.suspected_infection_time, INTERVAL '24' HOUR)`. |

There are no other `FROM` or `JOIN` clauses, and no `LEFT JOIN`.

The temporal join is inclusive at both endpoints: a SOFA row matches when its
`endtime` is from 48 hours before through 24 hours after the suspicion time.
If `suspected_infection_time` is NULL, the range comparisons are not true and
the inner join produces no match for that suspicion row.

## 2. Columns and inferred types

Types below use the normalized oracle types where the source SQL uses BigQuery
`DATETIME`; those datetime values are represented as `TIMESTAMP` in the
concept output. Dependency `ab_id` and `ROW_NUMBER()` values are inferred as
`BIGINT`.

### `sofa` CTE schema (lines 9--21)

The CTE reads these exact columns from the completed `sofa` dependency:

| CTE column | Source expression | Inferred type | Use |
|---|---|---|---|
| `stay_id` | `stay_id` | `INTEGER` | Inner-join key, then propagated to `s1` and final output. |
| `starttime` | `starttime` | `TIMESTAMP` | Propagated into `s1` only; not in final output or a predicate. |
| `endtime` | `endtime` | `TIMESTAMP` | Temporal join condition, row-order tie-break, and final `sofa_time`. |
| `respiration` | `respiration_24hours` | `INTEGER` | SOFA respiratory component in `s1` and final output. |
| `coagulation` | `coagulation_24hours` | `INTEGER` | Coagulation component in `s1` and final output. |
| `liver` | `liver_24hours` | `INTEGER` | Liver component in `s1` and final output. |
| `cardiovascular` | `cardiovascular_24hours` | `INTEGER` | Cardiovascular component in `s1` and final output. |
| `cns` | `cns_24hours` | `INTEGER` | CNS component in `s1` and final output. |
| `renal` | `renal_24hours` | `INTEGER` | Renal component in `s1` and final output. |
| `sofa_score` | `sofa_24hours` | `INTEGER` | CTE filter, repeated threshold expression in `s1`, and final output. |

### `s1` CTE schema (lines 23--65)

The suspicion dependency fields selected by `s1` are:

| CTE column | Source expression | Inferred type | Use in `s1`/downstream |
|---|---|---|---|
| `subject_id` | `soi.subject_id` | `INTEGER` | Propagated to final output. |
| `stay_id` | `soi.stay_id` | `INTEGER` | Non-NULL filter, inner-join key, window partition, and final output. |
| `ab_id` | `soi.ab_id` | `BIGINT` | Selected into `s1` but not used by a predicate, window, join, or final output. |
| `antibiotic` | `soi.antibiotic` | `VARCHAR` | Selected into `s1` but dropped before the final output. |
| `antibiotic_time` | `soi.antibiotic_time` | `TIMESTAMP` | `ROW_NUMBER()` ordering and final output. |
| `culture_time` | `soi.culture_time` | `TIMESTAMP` | `ROW_NUMBER()` ordering and final output. The source comment notes that culture times may originate from date-only cultures, but the normalized output type is `TIMESTAMP`. |
| `suspected_infection` | `soi.suspected_infection` | `INTEGER` (0/1) | Boolean `sepsis3` expression. |
| `suspected_infection_time` | `soi.suspected_infection_time` | `TIMESTAMP`, nullable | Temporal join anchor, `ROW_NUMBER()` ordering, and final output. |
| `specimen` | `soi.specimen` | `VARCHAR`, nullable | Selected into `s1` but dropped before the final output. |
| `positive_culture` | `soi.positive_culture` | `INTEGER`, nullable | Selected into `s1` but dropped before the final output. |

The SOFA fields selected into `s1` are `starttime` (`TIMESTAMP`), `endtime`
(`TIMESTAMP`), `respiration`, `coagulation`, `liver`, `cardiovascular`, `cns`,
and `renal` (each `INTEGER`), and `sofa_score` (`INTEGER`).

`s1` also creates:

- `sepsis3`: `sofa_score >= 2 AND suspected_infection = 1`, inferred
  `BOOLEAN`.
- `rn_sus`: `ROW_NUMBER() OVER (PARTITION BY soi.stay_id ORDER BY
  suspected_infection_time, antibiotic_time, culture_time, endtime)`, inferred
  `BIGINT`.

The `s1` aliases are therefore, in source order: `subject_id`, `stay_id`,
`ab_id`, `antibiotic`, `antibiotic_time`, `culture_time`,
`suspected_infection`, `suspected_infection_time`, `specimen`,
`positive_culture`, `starttime`, `endtime`, `respiration`, `coagulation`,
`liver`, `cardiovascular`, `cns`, `renal`, `sofa_score`, `sepsis3`, and
`rn_sus`.

### Final output (lines 67--80)

The final `SELECT` emits 14 columns in this exact order:

| # | Output column | Type | Source/derivation |
|---:|---|---|---|
| 1 | `subject_id` | `INTEGER` | `s1.subject_id` |
| 2 | `stay_id` | `INTEGER` | `s1.stay_id` |
| 3 | `antibiotic_time` | `TIMESTAMP` | `s1.antibiotic_time` |
| 4 | `culture_time` | `TIMESTAMP` | `s1.culture_time` |
| 5 | `suspected_infection_time` | `TIMESTAMP` | `s1.suspected_infection_time` |
| 6 | `sofa_time` | `TIMESTAMP` | `s1.endtime AS sofa_time` |
| 7 | `sofa_score` | `INTEGER` | `s1.sofa_score` |
| 8 | `respiration` | `INTEGER` | `s1.respiration` |
| 9 | `coagulation` | `INTEGER` | `s1.coagulation` |
| 10 | `liver` | `INTEGER` | `s1.liver` |
| 11 | `cardiovascular` | `INTEGER` | `s1.cardiovascular` |
| 12 | `cns` | `INTEGER` | `s1.cns` |
| 13 | `renal` | `INTEGER` | `s1.renal` |
| 14 | `sepsis3` | `BOOLEAN` | `s1.sepsis3` |

The final output has one selected row per `stay_id` in the normal source grain:
`rn_sus = 1` keeps the first joined suspicion/SOFA row in each stay partition.
The oracle manifest declares the source comparison key as `stay_id`. Its
additional FHIR comparison key columns are `icu_encounter_key` and
`patient_key`; those are resource identity metadata, not source SQL output
columns and must not replace `stay_id`.

## 3. Filters, value constraints, and temporal windows

### Row-eliminating `WHERE` predicates

1. In the `sofa` CTE:

   ```sql
   WHERE sofa_24hours >= 2
   ```

   This filters the `mimiciv_derived.sofa.sofa_24hours` dependency column and
   feeds the retained `sofa_score` and all six component values. It retains
   only SOFA rows with score at least 2 before the join.

2. In `s1`:

   ```sql
   WHERE soi.stay_id IS NOT NULL
   ```

   This removes suspicion rows without an ICU stay identifier. The surviving
   `stay_id` is then also required by the inner join and by the partitioning
   window.

3. In the final query:

   ```sql
   WHERE rn_sus = 1
   ```

   This selects the earliest row according to the source window ordering for
   each `soi.stay_id` partition. It makes the result at most one row per ICU
   stay.

### Join-time value constraint

The `INNER JOIN` has these exact predicates:

```sql
soi.stay_id = sofa.stay_id
AND sofa.endtime >= DATETIME_SUB(
    soi.suspected_infection_time, INTERVAL '48' HOUR
)
AND sofa.endtime <= DATETIME_ADD(
    soi.suspected_infection_time, INTERVAL '24' HOUR
)
```

The lower and upper bounds are both inclusive. This is a `[-48 hours, +24
hours]` window around `suspected_infection_time`, applied to `sofa.endtime`.

### Derived Boolean constraint (not a `WHERE` predicate)

The source creates the output flag with the exact expression:

```sql
sofa_score >= 2 AND suspected_infection = 1 AS sepsis3
```

The first conjunct is already guaranteed by the `sofa` CTE filter, but it is
still part of the source expression and must be recorded as such. The second
conjunct uses the dependency's integer `suspected_infection` discriminator;
this expression does not itself remove rows.

There are no direct `itemid`, `icd_code`, diagnosis, or other coded filters in
this SQL. There are no code systems and no literal code set to port for
`sepsis3`. The numeric/time literals named by the SQL are the SOFA threshold
`2`, the Boolean discriminator value `1`, `INTERVAL '48' HOUR`,
`INTERVAL '24' HOUR`, and the row-selection value `rn_sus = 1`; none is an
itemid or ICD code. No dead coded filter is present.

## 4. `mimiciv_derived` dependencies and exact consumed columns

The dependency boundary is exactly the following. Candidate SQL should consume
the completed dependency views as `sofa` and `suspicion_of_infection`, using
these columns; it should not reconstruct them from FHIR resources.

### Dependency `sofa`

Exact columns read from `mimiciv_derived.sofa`:

- `stay_id` (`INTEGER`): selected by the local CTE and used as the inner-join
  key.
- `starttime` (`TIMESTAMP`): selected and propagated through `s1`, but then
  dropped; it does not affect a predicate, window, or final output here.
- `endtime` (`TIMESTAMP`): selected, used in the temporal join and
  `ROW_NUMBER()` ordering, and emitted as final `sofa_time`.
- `respiration_24hours` (`INTEGER`), renamed `respiration`: final output.
- `coagulation_24hours` (`INTEGER`), renamed `coagulation`: final output.
- `liver_24hours` (`INTEGER`), renamed `liver`: final output.
- `cardiovascular_24hours` (`INTEGER`), renamed `cardiovascular`: final
  output.
- `cns_24hours` (`INTEGER`), renamed `cns`: final output.
- `renal_24hours` (`INTEGER`), renamed `renal`: final output.
- `sofa_24hours` (`INTEGER`), renamed `sofa_score`: filtered at `>= 2`, used
  by the Boolean expression, and emitted as final `sofa_score`.

### Dependency `suspicion_of_infection`

Exact columns read from `mimiciv_derived.suspicion_of_infection`:

- `subject_id` (`INTEGER`): final output.
- `stay_id` (`INTEGER`): non-NULL filter, inner-join key, window partition,
  and final output.
- `ab_id` (`BIGINT`): selected into `s1` only; not used after that projection.
- `antibiotic` (`VARCHAR`): selected into `s1` only; not used after that
  projection.
- `antibiotic_time` (`TIMESTAMP`): `ROW_NUMBER()` ordering and final output.
- `culture_time` (`TIMESTAMP`, nullable): `ROW_NUMBER()` ordering and final
  output.
- `suspected_infection` (`INTEGER`, 0/1): second operand of the `sepsis3`
  Boolean expression.
- `suspected_infection_time` (`TIMESTAMP`, nullable): temporal join anchor,
  `ROW_NUMBER()` ordering, and final output.
- `specimen` (`VARCHAR`, nullable): selected into `s1` only; not used after
  that projection.
- `positive_culture` (`INTEGER`, nullable): selected into `s1` only; not used
  after that projection.

No `hadm_id` or raw microbiology/antibiotic field is read directly by this
consumer.

## 5. Aggregations and window functions

- There is no `GROUP BY`, `DISTINCT`, or scalar aggregate (`MIN`, `MAX`, `AVG`,
  `ARRAY_AGG`, or similar) in `sepsis3.sql`.
- The only window function is:

  ```sql
  ROW_NUMBER() OVER (
      PARTITION BY soi.stay_id
      ORDER BY suspected_infection_time, antibiotic_time, culture_time, endtime
  ) AS rn_sus
  ```

  The partition is by ICU `stay_id`. The ordering is ascending by the four
  named fields using the SQL engine's ordinary NULL ordering; there is no
  additional tie-breaker. The final `rn_sus = 1` predicate selects the first
  row of each partition.

## 6. Semantically essential inputs and trace

These are the source values that can change row inclusion, row identity,
temporal selection, or a clinically meaningful output of this SQL:

| Essential input | Branches/operations controlled | Outputs affected |
|---|---|---|
| `soi.stay_id` | `IS NOT NULL` filter; inner join; `ROW_NUMBER()` partition | Inclusion, one-row-per-stay selection, `stay_id` output/key. |
| `sofa.stay_id` | Inner join to suspicion stay | Inclusion and the matched stay identity. |
| `sofa.sofa_24hours` | `WHERE sofa_24hours >= 2`; repeated `sofa_score >= 2` Boolean conjunct | Inclusion, `sofa_score`, and the `sepsis3` flag. |
| `sofa.endtime` | Inclusive `-48/+24` temporal join; final window tie-break | Inclusion, selected row, and `sofa_time`. |
| `soi.suspected_infection_time` | Inclusive temporal join anchor; first `ROW_NUMBER()` ordering field | Inclusion, selected row, and final `suspected_infection_time`. NULL prevents the temporal join from matching. |
| `soi.antibiotic_time` | Second `ROW_NUMBER()` ordering field | Selected row and final `antibiotic_time`. |
| `soi.culture_time` | Third `ROW_NUMBER()` ordering field | Selected row and final `culture_time`. |
| `soi.suspected_infection` | Second conjunct of `sofa_score >= 2 AND suspected_infection = 1` | Final `sepsis3` Boolean. |
| `sofa.respiration_24hours`, `coagulation_24hours`, `liver_24hours`, `cardiovascular_24hours`, `cns_24hours`, `renal_24hours` | Propagated through the selected `s1` row | The six clinically meaningful component output columns. |
| `soi.subject_id` | Propagated identifier | Final `subject_id` output and patient association. |

The following fields are read and selected into an intermediate CTE but do not
control any target predicate, key, grouping, window ordering, or final value:
`sofa.starttime`, `soi.ab_id`, `soi.antibiotic`, `soi.specimen`, and
`soi.positive_culture`. They must still be recognized as dependency columns
read by the consumer, but their values are not semantically used by the final
`sepsis3` table.

`rn_sus` is a generated selection discriminator, not a source field. Its value
depends on the four ordering inputs above and controls which joined row is
retained for each `stay_id`.

## Evidence

Concept: `sepsis3`. Canonical SQL read:
`/Users/nau025/Documents/mimic-code/mimic-iv/concepts/sepsis/sepsis3.sql`.
Also checked the DAG node and edges in
`mimic-iv/concept_dag/concept_dag.json` and the relevant generated DAG section,
the dependency canonical SQLs `mimic-iv/concepts/score/sofa.sql` and
`mimic-iv/concepts/sepsis/suspicion_of_infection.sql`, the normalized
`sepsis3` entry in
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`,
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and the provisional fragments
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sofa.md`,
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/suspicion_of_infection.md`, and
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`. The fragments were treated as
leads, not as verdict evidence.

Checked every `FROM`/`JOIN`, join type and predicate, intermediate and final
column, inferred type, `WHERE` predicate, temporal boundary, Boolean
discriminator, window expression, dependency column, source key, and coded
filter. Result: `sepsis3` is a two-dependency, ICU-stay-grain query with no
direct raw-table references, no coded literal set, one inclusive temporal
inner join, and one per-stay `ROW_NUMBER()` selection.

Reusable artifact: `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/carryover/sepsis3/source-analyst.md`.
