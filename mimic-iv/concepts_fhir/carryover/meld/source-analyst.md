# Source analysis: `meld`

## Source identity and DAG position

- Canonical SQL: `mimic-iv/concepts/organfailure/meld.sql`
- DAG stem: `meld`
- DAG path: `organfailure/meld.sql`
- DAG SHA-256: `a7ce07eb899fcdcf5fc6e2f2200adcc0af320767acc404c7a13a6bf5de919679`
- DAG level: `2`
- DAG dependencies, in the exact DAG spelling: `first_day_lab`,
  `first_day_rrt`
- DAG topological order places `first_day_lab`, then `first_day_rrt`, then
  `meld`. Both dependency ports must be completed before this consumer is
  executed.

The candidate-side dependency names after preprocessing are the unqualified
stems `first_day_lab` and `first_day_rrt`. Candidate SQL must consume those
completed dependency temp views; it must not rederive their laboratory or RRT
values from FHIR resources or inline their upstream SQL.

## 1. Table references in the canonical MELD SQL

| SQL clause | Alias | Join type | Schema | Table | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` in `cohort` | `ie` | driving relation | `mimiciv_icu` | `icustays` | ICU-stay spine and identifiers |
| `LEFT JOIN \`physionet-data.mimiciv_derived.first_day_lab\` labs` | `labs` | LEFT | `mimiciv_derived` | `first_day_lab` | First-day laboratory extrema |
| `LEFT JOIN \`physionet-data.mimiciv_derived.first_day_rrt\` r` | `r` | LEFT | `mimiciv_derived` | `first_day_rrt` | First-day dialysis-presence flag |

There are no `mimiciv_hosp` table references and no direct raw laboratory,
chartevent, inputevent, or procedureevent references in `meld.sql`.

## 2. Dependency boundary: exact columns read

The following are the complete consumer-side column contracts. They are the
only columns to expose/use from the two derived dependencies.

| Candidate stem / source relation | Exact columns read by MELD | Consumer use |
|---|---|---|
| `first_day_lab` / `mimiciv_derived.first_day_lab` | `stay_id`, `creatinine_max`, `bilirubin_total_max`, `inr_max`, `sodium_min` | `stay_id` joins the ICU stay; the four extrema feed raw output and score branches |
| `first_day_rrt` / `mimiciv_derived.first_day_rrt` | `stay_id`, `dialysis_present` | `stay_id` joins the ICU stay; `dialysis_present` is renamed `rrt` and controls the creatinine branch and raw output |

MELD does **not** read dependency `subject_id`, `hadm_id`, `charttime`, any
other first-day laboratory extrema, `dialysis_active`, or `dialysis_type`.

### Relevant upstream context (lineage only)

This context explains the dependency columns without changing the boundary:

- `first_day_lab` is one row per `stay_id`; its own SQL left-joins
  `complete_blood_count`, `chemistry`, `blood_differential`, `coagulation`,
  and `enzyme` to `mimiciv_icu.icustays` on patient plus an inclusive
  `charttime` window from six hours before `intime` through one day after
  `intime`, then computes stay-level min/max values. The MELD-relevant values
  are chemistry `creatinine` → `creatinine_max`, enzyme `bilirubin_total` →
  `bilirubin_total_max`, coagulation `inr` → `inr_max`, and chemistry `sodium`
  → `sodium_min`.
- `first_day_rrt` is one row per `(subject_id, stay_id)`; its own SQL left-joins
  the completed `rrt` dependency to `icustays` on `stay_id` and the same
  inclusive `[-6 hours, +1 day]` window, then computes
  `MAX(dialysis_present)`. The raw `rrt` concept itself reads
  `mimiciv_icu.chartevents`, `inputevents`, and `procedureevents`, but that
  logic is upstream-owned and must not be copied into MELD.

## 3. Columns by CTE and inferred types

The direct raw columns referenced by `meld.sql` are:

```text
mimiciv_icu.icustays:
  subject_id, hadm_id, stay_id, intime, outtime

first_day_lab:
  stay_id, creatinine_max, bilirubin_total_max, inr_max, sodium_min

first_day_rrt:
  stay_id, dialysis_present
```

The MIMIC identifiers are `INTEGER`; `intime` and `outtime` are `TIMESTAMP`;
the first-day laboratory extrema are nullable `DOUBLE`; and
`dialysis_present`/`rrt` is a nullable integer flag. Nullability matters
because both dependency joins are LEFT joins.

### `cohort`

`cohort` selects, in SQL order:

| Column | Expression | Inferred type | Notes |
|---|---|---|---|
| `subject_id` | `ie.subject_id` | `INTEGER` | Patient identifier |
| `hadm_id` | `ie.hadm_id` | `INTEGER` | Hospital-admission identifier; retained to final output |
| `stay_id` | `ie.stay_id` | `INTEGER` | ICU-stay key |
| `intime` | `ie.intime` | `TIMESTAMP` | Selected here but not used after `cohort` |
| `outtime` | `ie.outtime` | `TIMESTAMP` | Selected here but not used after `cohort` |
| `creatinine_max` | `labs.creatinine_max` | nullable `DOUBLE` | First-day dependency value |
| `bilirubin_total_max` | `labs.bilirubin_total_max` | nullable `DOUBLE` | First-day dependency value |
| `inr_max` | `labs.inr_max` | nullable `DOUBLE` | First-day dependency value |
| `sodium_min` | `labs.sodium_min` | nullable `DOUBLE` | First-day dependency value |
| `rrt` | `r.dialysis_present` | nullable `INTEGER` | Alias for dependency dialysis-presence flag |

Both dependency joins are exactly:

```sql
ON ie.stay_id = dependency.stay_id
```

There is no temporal predicate, `outtime` predicate, or other filter in
MELD's joins. Since the dependencies are one row per stay, the intended result
is one cohort row per `icustays.stay_id`; the LEFT joins preserve ICU stays
with absent dependency values.

### `score`

Pass-through columns are `subject_id`, `hadm_id`, `stay_id`, `rrt`,
`creatinine_max`, `bilirubin_total_max`, `inr_max`, and `sodium_min`, with the
types above. It adds four numeric score columns, inferred as `DOUBLE` in the
source/manifest representation:

| Column | Derivation |
|---|---|
| `sodium_score` | Piecewise sodium correction input |
| `creatinine_score` | Creatinine logarithmic component, with RRT/high-value and lower-bound handling |
| `bilirubin_score` | Bilirubin logarithmic component, with lower-bound handling |
| `inr_score` | INR logarithmic component plus `0.643`, with lower-bound handling |

`intime` and `outtime` are dropped at this boundary and do not feed any score.

### `score2`

`score2` retains the eight raw/pass-through columns from `score`, then
`creatinine_score`, `sodium_score`, `bilirubin_score`, and `inr_score`, and
adds:

| Column | Expression | Inferred type |
|---|---|---|
| `meld_initial` | capped/rounded sum of creatinine, bilirubin, and INR scores | `DECIMAL(38,1)` / BigQuery `NUMERIC` with scale 1 |

The final output does not retain the four component score columns.

### Final output

The final SELECT emits exactly these ten comparison columns, in this order:

| Output column | Source/expression | Inferred/manifest type |
|---|---|---|
| `subject_id` | `score2.subject_id` | `INTEGER` |
| `hadm_id` | `score2.hadm_id` | `INTEGER` |
| `stay_id` | `score2.stay_id` | `INTEGER` |
| `meld_initial` | `score2.meld_initial` | `DECIMAL(38,1)` |
| `meld` | final sodium-adjusted CASE | `DOUBLE` |
| `rrt` | `score2.rrt` | `INTEGER` |
| `creatinine_max` | `score2.creatinine_max` | `DOUBLE` |
| `bilirubin_total_max` | `score2.bilirubin_total_max` | `DOUBLE` |
| `inr_max` | `score2.inr_max` | `DOUBLE` |
| `sodium_min` | `score2.sodium_min` | `DOUBLE` |

The manifest confirms the final types and declares `stay_id` as the natural
comparison key. Required FHIR identity columns are separate port plumbing and
are not source columns in this canonical SQL.

## 4. Filters and conditional value constraints

There is no `WHERE` clause in `meld.sql`, hence no direct row-level filter,
itemid filter, ICD filter, code exclusion, or time-window predicate. The two
LEFT join equalities are the only direct row-matching predicates.

The following CASE predicates are not row filters; they are value-selection
rules that affect the derived scores:

1. `sodium_score`:
   - `sodium_min IS NULL` → `0.0`.
   - `sodium_min > 137` → `0.0`.
   - `sodium_min < 125` → `12.0`.
   - Otherwise → `137.0 - sodium_min`.
2. `creatinine_score`:
   - `rrt = 1 OR creatinine_max > 4.0` → `0.957 * LN(4)`.
   - Else, `creatinine_max < 1` → `0.957 * LN(1)`.
   - Else → `0.957 * COALESCE(LN(creatinine_max), LN(1))`.
3. `bilirubin_score`:
   - `bilirubin_total_max < 1` → `0.378 * LN(1)`.
   - Else → `0.378 * COALESCE(LN(bilirubin_total_max), LN(1))`.
4. `inr_score`:
   - `inr_max < 1` → `1.120 * LN(1) + 0.643`.
   - Else → `1.120 * COALESCE(LN(inr_max), LN(1)) + 0.643`.
5. `meld_initial`:
   - `(creatinine_score + bilirubin_score + inr_score) > 4` → `40.0`.
   - Otherwise → `ROUND(CAST(creatinine_score + bilirubin_score + inr_score AS NUMERIC), 1) * 10`.
6. Final `meld`:
   - `meld_initial > 11` →
     `meld_initial + 1.32 * sodium_score - 0.033 * meld_initial * sodium_score`.
   - Otherwise → `meld_initial`.

The SQL comments state that this implementation checks any first-day dialysis,
not the policy's two treatments/24 hours of CVVHD rule, and that corrected
sodium, etiology, and glucose adjustment remain TODOs. Those comments are not
executable filters or additional inputs; the actual executable discriminator
is only `rrt = 1`.

## 5. Literal code set — verbatim

The direct MELD literal code set is empty. `meld.sql` names no `itemid`,
`icd_code`/`icd_version`, LOINC code, coding system, or other coded filter, so
there is no source table/code set feeding a MELD CTE or output column and no
dead coded filter to report.

The literal `rrt = 1` is a numeric dependency flag discriminator, not an
item/code-system filter. Upstream itemid sets belong to the completed
`first_day_lab`/`first_day_rrt` and their dependencies; they are not MELD
filters and must not be reintroduced into the MELD candidate SQL.

## 6. Joins and dependency behavior

`cohort` has two LEFT joins:

```sql
FROM `physionet-data.mimiciv_icu.icustays` ie
LEFT JOIN `physionet-data.mimiciv_derived.first_day_lab` labs
  ON ie.stay_id = labs.stay_id
LEFT JOIN `physionet-data.mimiciv_derived.first_day_rrt` r
  ON ie.stay_id = r.stay_id
```

There are no joins in `score`, `score2`, or the final SELECT; those CTEs are
projections/calculations over the preceding CTE. The LEFT-join null behavior
is part of the result: an ICU stay remains present when either dependency has
no matching row, and the associated raw fields/score behavior follows SQL
NULL semantics.

## 7. Aggregations and grain

`meld.sql` has no `GROUP BY`, window function, `MIN`, `MAX`, `AVG`,
`ARRAY_AGG`, `STRING_AGG`, or other row aggregation. Its only aggregate-like
inputs are already aggregated dependency columns (`*_max`, `sodium_min`, and
`dialysis_present`) consumed at the dependency boundary.

The natural grain is one row per ICU stay, keyed by `stay_id`, with
`subject_id` and `hadm_id` carried as identifiers. This follows the unique
`mimiciv_icu.icustays` driving relation and the intended one-row-per-stay
shapes of both dependencies. `stay_id` controls both dependency joins and the
final identity; it is also the manifest key.

## 8. Semantically essential inputs

| Input | What it controls | Trace to output/branch |
|---|---|---|
| `icustays.stay_id` | Natural grain and both dependency joins | Output `stay_id`; determines which lab/RRT row can contribute to every derived value |
| `icustays.subject_id` | Patient identity | Output `subject_id`; does not itself filter rows or affect the score |
| `icustays.hadm_id` | Admission identity carried through CTEs | Output `hadm_id`; not used in either join or calculation |
| `first_day_lab.stay_id` | Match to ICU stay | Inclusion of that dependency row in the cohort's lab inputs |
| `first_day_lab.creatinine_max` | High-value/lower-bound/logarithmic creatinine branch | `creatinine_score`, `meld_initial`, `meld`, and raw `creatinine_max` |
| `first_day_lab.bilirubin_total_max` | Lower-bound/logarithmic bilirubin branch | `bilirubin_score`, `meld_initial`, `meld`, and raw `bilirubin_total_max` |
| `first_day_lab.inr_max` | Lower-bound/logarithmic INR branch | `inr_score`, `meld_initial`, `meld`, and raw `inr_max` |
| `first_day_lab.sodium_min` | Sodium cap/floor and correction amount | `sodium_score`, final `meld`, and raw `sodium_min` |
| `first_day_rrt.stay_id` | Match to ICU stay | Inclusion of the dependency dialysis flag |
| `first_day_rrt.dialysis_present` | Actual dialysis discriminator `rrt = 1` | Forces creatinine component to use `LN(4)`; also emitted as raw `rrt` |
| Dependency row null/match state | LEFT-join preservation and NULL score semantics | Keeps the ICU row while allowing nullable raw inputs and fallback logarithms |

`icustays.intime` and `icustays.outtime` are selected into `cohort` but are
dead after that CTE: neither controls inclusion, grouping, carry-forward, or a
derived output in this SQL. There is no temporal carry-forward logic in MELD;
all first-day temporal selection was performed upstream by the two dependency
concepts.

At the dependency boundary, the upstream `charttime` and source analyte/RRT
discriminators are semantically important to the dependency results, but they
are not MELD consumer columns. Preserve the boundary rather than attempting
to recover those upstream fields from FHIR.

## Evidence boundary

This is a source-SQL analysis only. No SQL was run, no ViewDefinition or
attempt artifact was authored, and no clinical or terminal representability
decision was made. The canonical source, DAG metadata/hash, the two dependency
SQL files, relevant upstream `chemistry`, `coagulation`, `enzyme`,
`blood_differential`, `complete_blood_count`, and `rrt` source context, the
dependency carryover analyses, the MIMIC DDL, and the MELD oracle manifest
entry were read to establish the facts above.
