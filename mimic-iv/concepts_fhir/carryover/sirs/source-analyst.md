# Source analysis: `sirs`

## Source and DAG identity

- Concept stem: `sirs`.
- Canonical SQL: `mimic-iv/concepts/score/sirs.sql`.
- DAG path: `score/sirs.sql`.
- DAG SHA256: `0d5f398c452de2b9d1e4718f912042e8831bd7370c4f52ebd453d5adddcf2355`.
- DAG level: `2`.
- DAG dependencies, exactly as recorded: `first_day_bg_art`, `first_day_lab`,
  and `first_day_vitalsign`.
- The DAG edges confirm the three dependency edges
  `sirs -> first_day_bg_art`, `sirs -> first_day_lab`, and
  `sirs -> first_day_vitalsign`.

The source comments say that the score is calculated for all ICU patients and
that callers may subselect appropriate `stay_id` values. The SQL itself has no
such sub-selection predicate: its driving relation is all rows of
`mimiciv_icu.icustays`.

## Query structure and table references

The query has two CTEs followed by a final select.

### `scorecomp` (source lines 29-46)

Every `FROM`/`JOIN` relation in this CTE is:

| SQL relation | Schema/table or CTE | Alias | Join type | Exact condition | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` | schema `mimiciv_icu`, table `icustays` | `ie` | driving relation | — | ICU-stay spine |
| `LEFT JOIN \`physionet-data.mimiciv_derived.first_day_bg_art\` bg` | schema `mimiciv_derived`, table `first_day_bg_art` | `bg` | `LEFT` | `ie.stay_id = bg.stay_id` | arterial blood-gas first-day dependency |
| `LEFT JOIN \`physionet-data.mimiciv_derived.first_day_vitalsign\` v` | schema `mimiciv_derived`, table `first_day_vitalsign` | `v` | `LEFT` | `ie.stay_id = v.stay_id` | first-day vital-sign dependency |
| `LEFT JOIN \`physionet-data.mimiciv_derived.first_day_lab\` l` | schema `mimiciv_derived`, table `first_day_lab` | `l` | `LEFT` | `ie.stay_id = l.stay_id` | first-day laboratory dependency |

There are no `mimiciv_hosp` table references. The three derived tables are
consumer boundaries. In candidate SQL after preprocessing they are available
under their unqualified stems `first_day_bg_art`, `first_day_lab`, and
`first_day_vitalsign`; they must be consumed as completed dependencies, not
inlined or rederived from FHIR resources.

### `scorecalc` (source lines 48-85)

| SQL relation | Relation kind | Condition |
|---|---|---|
| `FROM scorecomp` | CTE `scorecomp` | none |

This CTE has no join, filter, grouping, or aggregation.

### Final query (source lines 87-100)

| SQL relation | Schema/table or CTE | Alias | Join type | Exact condition | Role |
|---|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` | schema `mimiciv_icu`, table `icustays` | `ie` | driving relation | — | final ICU-stay output spine |
| `LEFT JOIN scorecalc s` | CTE `scorecalc` | `s` | `LEFT` | `ie.stay_id = s.stay_id` | attach the four component scores |

All joins are equality joins on `stay_id` and all joins to dependency/CTE
relations are `LEFT JOIN`s. There is no final join on `subject_id` or
`hadm_id`.

## Exact dependency boundary and consumer columns

The source SIRS query reads exactly the following columns from the three
`mimiciv_derived` dependencies. No other dependency fields are part of this
consumer specification.

| Qualified dependency column | Use in SIRS | CTE/output trace | Inferred type |
|---|---|---|---|
| `bg.stay_id` from `mimiciv_derived.first_day_bg_art` | equality join to `ie.stay_id` | `scorecomp` row association | integer ICU-stay identifier |
| `bg.pco2_min` from `mimiciv_derived.first_day_bg_art` | selected as `paco2_min` | `scorecomp.paco2_min` → `scorecalc.resp_score` → final `resp_score`, `sirs` | nullable numeric, inherited from dependency aggregate |
| `v.stay_id` from `mimiciv_derived.first_day_vitalsign` | equality join to `ie.stay_id` | `scorecomp` row association | integer ICU-stay identifier |
| `v.temperature_min` | selected into `scorecomp` | `scorecomp.temperature_min` → `scorecalc.temp_score` → final `temp_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `v.temperature_max` | selected into `scorecomp` | `scorecomp.temperature_max` → `scorecalc.temp_score` → final `temp_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `v.heart_rate_max` | selected into `scorecomp` | `scorecomp.heart_rate_max` → `scorecalc.heart_rate_score` → final `heart_rate_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `v.resp_rate_max` | selected into `scorecomp` | `scorecomp.resp_rate_max` → `scorecalc.resp_score` → final `resp_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `l.stay_id` from `mimiciv_derived.first_day_lab` | equality join to `ie.stay_id` | `scorecomp` row association | integer ICU-stay identifier |
| `l.wbc_min` | selected into `scorecomp` | `scorecomp.wbc_min` → `scorecalc.wbc_score` → final `wbc_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `l.wbc_max` | selected into `scorecomp` | `scorecomp.wbc_max` → `scorecalc.wbc_score` → final `wbc_score`, `sirs` | nullable numeric; dependency output is an aggregate |
| `l.bands_max` | selected into `scorecomp` | `scorecomp.bands_max` → `scorecalc.wbc_score` → final `wbc_score`, `sirs` | nullable numeric; dependency output is an aggregate |

The dependency tables' upstream item filters, time windows, and aggregate
calculations belong to those dependency concepts. SIRS consumes only the
listed already-produced columns and must not reproduce those upstream rules.

## Column inventory and inferred types

### Direct `icustays` columns

The query references these columns from
`mimiciv_icu.icustays`:

- `ie.subject_id`: selected in the final output; integer-valued MIMIC patient
  identifier (`INT64`/integer in the source dialect).
- `ie.hadm_id`: selected in the final output; integer-valued hospital-admission
  identifier (`INT64`/integer).
- `ie.stay_id`: selected in `scorecomp` and the final output, and used in every
  join condition; integer-valued ICU-stay identifier (`INT64`/integer).

No other `icustays` column is referenced. In particular, SIRS does not read
`intime`, `outtime`, or any event timestamp; temporal selection is already
inside the first-day dependency outputs.

### `scorecomp` CTE schema

The CTE selects the following columns, in SQL order:

1. `stay_id` — `ie.stay_id`, integer identifier.
2. `temperature_min` — `v.temperature_min`, nullable numeric.
3. `temperature_max` — `v.temperature_max`, nullable numeric.
4. `heart_rate_max` — `v.heart_rate_max`, nullable numeric.
5. `resp_rate_max` — `v.resp_rate_max`, nullable numeric.
6. `paco2_min` — `bg.pco2_min AS paco2_min`, nullable numeric.
7. `wbc_min` — `l.wbc_min`, nullable numeric.
8. `wbc_max` — `l.wbc_max`, nullable numeric.
9. `bands_max` — `l.bands_max`, nullable numeric.

The numeric types are not cast by this query and therefore retain the precision
and scale/type of the completed dependency outputs. The `LEFT JOIN`s make the
dependency-derived columns nullable when no matching dependency row exists.

### `scorecalc` CTE schema

`scorecalc` selects:

- `stay_id`: integer identifier from `scorecomp`.
- `temp_score`: nullable integer (`INT64`/integer) from a `CASE` returning
  `1`, `0`, or `NULL`.
- `heart_rate_score`: nullable integer from a `CASE` returning `1`, `0`, or
  `NULL`.
- `resp_score`: nullable integer from a `CASE` returning `1`, `0`, or `NULL`.
- `wbc_score`: nullable integer from a `CASE` returning `1`, `0`, or `NULL`.

### Final output schema

The final output columns, in exact SQL order, are:

1. `subject_id` — `ie.subject_id`; integer (`INT64`).
2. `hadm_id` — `ie.hadm_id`; integer (`INT64`).
3. `stay_id` — `ie.stay_id`; integer (`INT64`).
4. `sirs` — the sum of four integer `COALESCE` expressions; integer
   (`INT64`). Each missing component is replaced with integer `0` in this
   expression.
5. `temp_score` — `s.temp_score`; nullable integer.
6. `heart_rate_score` — `s.heart_rate_score`; nullable integer.
7. `resp_score` — `s.resp_score`; nullable integer.
8. `wbc_score` — `s.wbc_score`; nullable integer.

The final component columns are selected without a further `COALESCE`, so the
component outputs retain the `NULL` values produced by `scorecalc` (or by a
missing final `scorecalc` match). The `sirs` expression itself uses
`COALESCE(..., 0)` for every component.

## Filters and row-inclusion predicates

There is no `WHERE` clause in `sirs.sql`, and therefore no `WHERE` predicate,
`HAVING` predicate, time-window predicate, value exclusion, or code exclusion
to report. There is also no explicit stay cohort filter. The only row-inclusion
predicates are the four equality conditions in the `LEFT JOIN`s:

```sql
ie.stay_id = bg.stay_id
ie.stay_id = v.stay_id
ie.stay_id = l.stay_id
ie.stay_id = s.stay_id
```

Because these are left joins, the ICU-stay driving rows are retained even when
one or more dependency-derived component inputs are absent. The source does
not constrain the dependency values before scoring; the `CASE` branches below
are value tests that produce scores, not `WHERE` filters.

## Literal code-set specification

The literal coded-filter set for this consumer is **empty**. The SQL names no
`itemid`, `icd_code`, `icd_version`, LOINC code, coding-system URI, or other
coded value. Consequently:

- there is no exact code set to associate with a source table;
- there is no code set feeding `scorecomp`, `scorecalc`, or any final output
  column; and
- there is no dead coded filter present in this SQL.

The decimal threshold literals in the score `CASE` expressions are numeric
value tests, not coded filters; they are copied verbatim in the score-branch
section below. Any itemid/code filters used by `first_day_bg_art`,
`first_day_lab`, `first_day_vitalsign`, or their upstream concepts are outside
the SIRS SQL and remain owned by those dependencies.

## Score branches and exact value semantics

The following expressions are copied verbatim from the source SQL, including
their order. `CASE` order is significant: the first true branch wins.

### Temperature (`temp_score`, source lines 55-60)

```sql
CASE
    WHEN temperature_min < 36.0 THEN 1
    WHEN temperature_max > 38.0 THEN 1
    WHEN temperature_min IS NULL THEN NULL
    ELSE 0
END AS temp_score
```

`temperature_min` controls both the low-value branch and the explicit missing
branch. `temperature_max` controls the high-value branch. Because the low and
high tests precede the null test, a qualifying non-NULL opposite extrema can
produce `1` even when `temperature_min` is NULL; otherwise a NULL
`temperature_min` reaches the explicit NULL branch when the earlier tests are
not true.

### Heart rate (`heart_rate_score`, source lines 63-67)

```sql
CASE
    WHEN heart_rate_max > 90.0 THEN 1
    WHEN heart_rate_max IS NULL THEN NULL
    ELSE 0
END AS heart_rate_score
```

`heart_rate_max` controls the high-value score and missingness result.

### Respiratory (`resp_score`, source lines 69-74)

```sql
CASE
    WHEN resp_rate_max > 20.0 THEN 1
    WHEN paco2_min < 32.0 THEN 1
    WHEN COALESCE(resp_rate_max, paco2_min) IS NULL THEN NULL
    ELSE 0
END AS resp_score
```

`resp_rate_max` and `paco2_min` are independent positive branches. The
missingness branch tests `COALESCE(resp_rate_max, paco2_min)`, so it is NULL
only when both inputs are NULL. A non-qualifying non-NULL value in either
input can therefore lead to `0` if neither threshold branch is true.

### White blood cell/bands (`wbc_score`, source lines 76-82)

```sql
CASE
    WHEN wbc_min < 4.0 THEN 1
    WHEN wbc_max > 12.0 THEN 1
    WHEN bands_max > 10 THEN 1-- > 10% immature neurophils (band forms)
    WHEN COALESCE(wbc_min, bands_max) IS NULL THEN NULL
    ELSE 0
END AS wbc_score
```

`wbc_min`, `wbc_max`, and `bands_max` each have a score branch. The
missingness test is exactly `COALESCE(wbc_min, bands_max) IS NULL`; it does not
test `wbc_max`. Thus the SQL's null behavior follows the expression as written,
including its branch ordering.

### Final SIRS sum (source lines 87-96)

```sql
COALESCE(temp_score, 0)
+ COALESCE(heart_rate_score, 0)
+ COALESCE(resp_score, 0)
+ COALESCE(wbc_score, 0)
AS sirs
```

The final numeric output sums the four component scores after replacing each
NULL component with integer `0`. The component columns themselves are also
emitted separately without this imputation.

## Aggregations, windows, and carry-forward

SIRS itself has no aggregation:

- no `GROUP BY`;
- no `MIN`, `MAX`, `AVG`, `SUM`, `COUNT`, `ARRAY_AGG`, or other value
  aggregation in the query;
- no window functions;
- no `DISTINCT`; and
- no temporal carry-forward or ordering operation.

The names `temperature_min`, `temperature_max`, `heart_rate_max`,
`resp_rate_max`, `pco2_min`, `wbc_min`, `wbc_max`, and `bands_max` are already
aggregated outputs of the three dependency concepts. SIRS only tests those
dependency outputs and combines the resulting four score integers.

## Natural grain and dependency cardinality boundary

The intended natural grain is one result row per ICU stay, keyed by
`stay_id`, with `subject_id` and `hadm_id` carried from the corresponding
`icustays` row. `scorecomp` is driven by `icustays` and has the same intended
stay-level grain; `scorecalc` preserves it; and the final `icustays` relation
reattaches the four component scores by `stay_id`.

The SQL contains no grouping or deduplication that would repair duplicate
dependency rows. It assumes each completed first-day dependency is at its
declared stay-level grain. If a dependency relation has multiple matching rows
for one `stay_id`, the ordinary SQL left join can fan out `scorecomp` and the
final join can attach multiple score rows. That is a relation-cardinality
property of the source SQL, not a license to add `DISTINCT` or aggregation.

## Semantically essential inputs

These are the source fields and relation properties whose values can alter row
association, output identity, score branches, NULL behavior, or the clinically
meaningful derived `sirs` value. The trace is limited to what this SQL reads;
upstream source fields that created the dependency aggregates remain behind the
dependency boundary.

| Essential input | What it controls | Affected branch/output |
|---|---|---|
| `mimiciv_icu.icustays.stay_id` | All three dependency joins, `scorecomp.stay_id`, final join, and natural row identity | Whether each dependency row is associated; final `stay_id`; all component and `sirs` values attached to that stay |
| Each dependency `stay_id` | Equality against the ICU-stay key | Dependency row inclusion and all score inputs from that dependency |
| `mimiciv_icu.icustays.subject_id` | Emitted patient identity; it is not used in a SIRS join predicate | Final `subject_id` output and row identity metadata, but not dependency inclusion in this consumer |
| `mimiciv_icu.icustays.hadm_id` | Emitted hospital-admission identity only | Final `hadm_id` output; it does not control scoring or joins |
| `first_day_vitalsign.temperature_min` | Low-temperature test and missingness branch | `temp_score`, final `temp_score`, and `sirs` |
| `first_day_vitalsign.temperature_max` | High-temperature test | `temp_score`, final `temp_score`, and `sirs` |
| `first_day_vitalsign.heart_rate_max` | High-heart-rate test and missingness branch | `heart_rate_score`, final `heart_rate_score`, and `sirs` |
| `first_day_vitalsign.resp_rate_max` | High-respiratory-rate test and one side of the missingness `COALESCE` | `resp_score`, final `resp_score`, and `sirs` |
| `first_day_bg_art.pco2_min` (renamed `paco2_min`) | Low-PaCO2 test and one side of the missingness `COALESCE` | `resp_score`, final `resp_score`, and `sirs` |
| `first_day_lab.wbc_min` | Low-WBC test and one side of the missingness `COALESCE` | `wbc_score`, final `wbc_score`, and `sirs` |
| `first_day_lab.wbc_max` | High-WBC test | `wbc_score`, final `wbc_score`, and `sirs` |
| `first_day_lab.bands_max` | High-bands test and one side of the missingness `COALESCE` | `wbc_score`, final `wbc_score`, and `sirs` |
| `temp_score`, `heart_rate_score`, `resp_score`, `wbc_score` | Four addends of the final imputed sum and separately emitted component values | Final `sirs`; corresponding final component columns |
| Dependency relation cardinality at `stay_id` | Whether the assumed stay-level row association is one-to-one or fans out | Result row multiplicity and score attachment; no source operation collapses duplicates |

No datetime field, event discriminator, temporal carry-forward key, or raw
item/code field is read by SIRS itself. The first-day temporal windows and raw
item/value discriminators are semantically essential to producing the
dependency columns, but they are not re-read or re-applied by this consumer.

## Context read, without changing the source specification

I read the authoritative `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and the
provisional fragment leads relevant to these dependencies, including
`MIMIC_NOTES.d/first_day_bg.md`,
`MIMIC_NOTES.d/first_day_vitalsign.md`,
`MIMIC_NOTES.d/complete_blood_count.md`, and
`MIMIC_NOTES.d/blood_differential.md`. The notes provide context that upstream
lab/chartevent timestamps and aggregates can be affected by FHIR ETL
normalization, and that MIMIC identifiers are emitted as identifier values
rather than resource keys. Those facts do not add tables, filters, joins, or
codes to `sirs.sql`; resource/reference IDs remain opaque and are not parsed or
inverted here. No FHIR mapping or representability decision is made in this
source analysis.

## Evidence boundary

This artifact describes only the canonical SIRS SQL and its DAG dependency
boundary. It does not author a ViewDefinition or candidate SQL, run SQL, map
FHIR fields, resolve codes, or make a clinical/terminal equivalence decision.
The implementer handoff must preserve the three unqualified dependency stems,
the exact stay-only LEFT joins, the no-filter behavior, the eight-column
dependency input set, the four ordered CASE branches, final NULL-to-zero sum,
and one-row-per-stay intended grain.
