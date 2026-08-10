# Source analysis: `blood_differential`

## Sources read and source identity

- Canonical SQL: `mimic-iv/concepts/measurement/blood_differential.sql` (203
  lines; source of truth).
- DAG: `mimic-iv/concept_dag/concept_dag.json`, node `blood_differential`.
  The node records path `measurement/blood_differential.sql`, SHA-256
  `a93f21dfb29e00b1450fabff5572830a2a5930f1229dbe43f816dd1b8b8235f1`,
  level `0`, no dependencies, and dependent `first_day_lab`.
- Port contract and coding/mapping notes:
  `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` and
  `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- The `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` directory contains only
  `README.md`; there is no blood-differential-specific fragment to apply.
- Raw source schema: `mimic-iv/buildmimic/postgres/create.sql`, specifically
  the `mimiciv_hosp.labevents` definition at lines 165--184 and the
  `mimiciv_hosp.d_labitems` definition at lines 78--85. The latter is not
  referenced by this SQL.
- Read-only generated dialect forms for type/materialization confirmation:
  `mimic-iv/concepts_duckdb/measurement/blood_differential.sql`,
  `mimic-iv/concepts_postgres/measurement/blood_differential.sql`, and the
  `blood_differential` entry in
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`.
- Read the downstream consumer
  `mimic-iv/concepts/firstday/first_day_lab.sql`; it confirms that
  `blood_differential` is consumed downstream, not used as an input by this
  concept.

The canonical SQL reads one raw hospital laboratory table, aggregates it into
one row per `specimen_id`, then applies rounded absolute-count imputation in the
outer SELECT. It does not make a clinical decision or use a diagnosis/code
translation.

## Exact query shape and text semantics

The only CTE is `blood_diff`:

1. It reads eligible `labevents` rows.
2. It groups **only** by `le.specimen_id`.
3. It retains `MAX(subject_id)`, `MAX(hadm_id)`, and `MAX(charttime)` for the
   specimen, independently of one another.
4. It pivots itemids into WBC, absolute-count, percentage, and other-cell
   columns using conditional `MAX` expressions.
5. It computes `impute_abs` as `1` only when the specimen has a WBC maximum
   strictly greater than zero and the sum of six differential-percentage item
   values is strictly greater than zero; otherwise it computes `0`.

The outer SELECT returns the grouped identifiers, `wbc`, five absolute-count
columns after optional imputation, five primary percentage columns, and five
other percentage/count columns. Absolute imputation is only attempted when the
absolute result is NULL, its corresponding percentage is non-NULL, and
`impute_abs = 1`; the value is `percentage * wbc / 100`. Each of those five
absolute outputs is cast to `NUMERIC` and rounded to four decimal places,
including values that were already measured. The percentage columns are not
divided by 100; their source `valuenum` is emitted as the percentage number.

The SQL comments state the intended unit convention: `10^9/L == K/uL ==
10^3/uL`; count inputs expressed as `#/uL` are divided by `1000.0` to produce
the normalized K/uL-like value. The SQL itself uses itemid branches, not
`valueuom`, to select those conversions. `granulocytes_abs` is calculated in
the CTE (with the same `/1000.0` conversion for itemid `51218`) but is not
selected by the final query. The final comment `-- impute bands/blasts?` is
only a comment; no bands/blasts imputation is performed.

Because the grouping is by specimen and the aggregate is `MAX`, multiple
eligible rows for one specimen are collapsed. The chosen maximum for each
analyte and the maximum chart time need not come from the same input row. A
specimen with only one eligible item can still produce an output row, with
other analytes NULL. A specimen can be admitted to the CTE only through the
itemid allowlist and the numeric-value predicates below.

## Physical table references

| SQL occurrence | Type | Schema | Table/CTE | Condition |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_hosp.labevents\` le` (line 104) | physical table | `mimiciv_hosp` | `labevents` | none |
| outer `FROM blood_diff` (line 202) | CTE | n/a | `blood_diff` | none |

The project qualifier `physionet-data` does not change the source schema/table
identity: the physical source is `mimiciv_hosp.labevents`. There are no JOIN
clauses, no INNER JOIN, no LEFT JOIN, and no join conditions. There is no
reference to `mimiciv_icu`, `mimiciv_derived`, `d_labitems`, admissions, or any
other table. The generated DuckDB/Postgres build wraps the result as
`mimiciv_derived.blood_differential`; that is the materialized output name, not
a dependency read by this canonical SQL.

## Source columns and schema types

The source DDL declares `mimiciv_hosp.labevents` as follows for columns used by
this concept:

| Source column | DDL type/nullability | How the SQL uses it |
|---|---|---|
| `subject_id` | `INTEGER NOT NULL` | `MAX(subject_id)` → output `subject_id` |
| `hadm_id` | `INTEGER` nullable | `MAX(hadm_id)` → output `hadm_id` |
| `specimen_id` | `INTEGER NOT NULL` | grouping key and output `specimen_id` |
| `itemid` | `INTEGER NOT NULL` | WHERE allowlist and every conditional pivot |
| `charttime` | `TIMESTAMP(0)` nullable | `MAX(charttime)` → output `charttime` |
| `valuenum` | `DOUBLE PRECISION` nullable | non-NULL/nonnegative filter, pivots, unit conversion, sums, and imputation |

Other `labevents` columns (`labevent_id`, `order_provider_id`, `storetime`,
`value`, `valueuom`, reference ranges, `flag`, `priority`, and `comments`) are
not selected or referenced. `d_labitems` is not joined, so its `label`,
`fluid`, and `category` cannot affect this concept.

## CTE columns and inferred types

The following are all columns selected or referenced in `blood_diff`, including
the intermediate column that is dropped by the outer query:

| CTE column | Expression/source | Inferred type | Final status |
|---|---|---|---|
| `subject_id` | `MAX(subject_id)` | `INTEGER` | output |
| `hadm_id` | `MAX(hadm_id)` | `INTEGER` | output |
| `charttime` | `MAX(charttime)` | `TIMESTAMP` | output |
| `specimen_id` | `le.specimen_id` / `GROUP BY` | `INTEGER` | output and natural key |
| `wbc` | `MAX(CASE WHEN itemid IN (51300, 51301, 51755) THEN valuenum ...)` | `DOUBLE` | output |
| `basophils_abs` | `MAX` of itemid `52069` `valuenum` | `DOUBLE` in CTE | output after numeric cast/round |
| `eosinophils_abs` | itemid `52073` as-is or `51199 / 1000.0` | `DOUBLE` in CTE | output after numeric cast/round |
| `lymphocytes_abs` | itemid `51133` as-is or `52769 / 1000.0` | `DOUBLE` in CTE | output after numeric cast/round |
| `monocytes_abs` | itemid `52074` as-is or `51253 / 1000.0` | `DOUBLE` in CTE | output after numeric cast/round |
| `neutrophils_abs` | `MAX` of itemid `52075` `valuenum` | `DOUBLE` in CTE | output after numeric cast/round |
| `granulocytes_abs` | itemid `51218` `valuenum / 1000.0` | `DOUBLE` | **CTE-only; dropped by final SELECT** |
| `basophils` | itemid `51146` `valuenum` | `DOUBLE` | output |
| `eosinophils` | itemid `51200` `valuenum` | `DOUBLE` | output |
| `lymphocytes` | itemids `51244` or `51245` `valuenum` | `DOUBLE` | output |
| `monocytes` | itemid `51254` `valuenum` | `DOUBLE` | output |
| `neutrophils` | itemid `51256` `valuenum` | `DOUBLE` | output |
| `atypical_lymphocytes` | itemid `51143` `valuenum` | `DOUBLE` | output |
| `bands` | itemid `51144` `valuenum` | `DOUBLE` | output |
| `immature_granulocytes` | itemid `52135` `valuenum` | `DOUBLE` | output |
| `metamyelocytes` | itemid `51251` `valuenum` | `DOUBLE` | output |
| `nrbc` | itemid `51257` `valuenum` | `DOUBLE` | output |
| `impute_abs` | two aggregate predicates, `THEN 1 ELSE 0` | integer | CTE-only control flag |

The output manifest confirms these target types and names: IDs are `INTEGER`,
`charttime` is `TIMESTAMP`, `wbc` and all non-absolute measurements are
`DOUBLE`, and the five rounded absolute outputs are `DECIMAL(38,4)` in the
DuckDB oracle. The manifest records 3,171,906 rows and natural key
`["specimen_id"]`; its comparison mode is `keyed_join`. The SQL's grouping and
the non-null source `specimen_id` explain why `specimen_id` is the natural
source key, but the manifest key is the authoritative comparator key.

Final output column order is exactly:

```text
subject_id, hadm_id, charttime, specimen_id,
wbc,
basophils_abs, eosinophils_abs, lymphocytes_abs, monocytes_abs,
neutrophils_abs,
basophils, eosinophils, lymphocytes, monocytes, neutrophils,
atypical_lymphocytes, bands, immature_granulocytes, metamyelocytes, nrbc
```

There are 20 output columns. `subject_id` and `specimen_id` originate from
non-NULL source fields; `hadm_id`, `charttime`, and all pivoted measurement
columns can be NULL under the SQL semantics. The result has no declared SQL
constraints in the concept text.

## Filters and conditional predicates

### Row filter

The only WHERE clause is:

- `le.itemid IN (...)`: exact active literal set reproduced below.
- `valuenum IS NOT NULL`: removes rows without a numeric value.
- `valuenum >= 0`: removes all negative numeric values, with no exception by
  itemid. There is no upper-bound, text-value, unit, admission, patient, or
  time predicate.

The query therefore has no time window. It does not use `charttime` to select
or deduplicate input rows; `charttime` is only aggregated with `MAX`.

### Imputation/control predicates

These are not row filters; they control conditional aggregates or the final
absolute-value fallback:

- WBC availability: the maximum of itemids `(51300, 51301, 51755)` must be
  strictly `> 0`.
- Percentage availability: the sum of itemids
  `(51146, 51200, 51244, 51245, 51254, 51256)` must be strictly `> 0`.
- Each absolute fallback additionally requires its own absolute CTE value to
  be `NULL`, its own percentage to be non-NULL, and `impute_abs = 1`.
- A zero WBC does not enable imputation; an all-zero differential percentage
  set does not enable imputation. Because the WHERE clause already excludes
  negative values and NULLs, the percentage sum is over nonnegative numeric
  values.

## Literal code specification

The source table for every code below is `mimiciv_hosp.labevents`; the code
column is its integer `itemid`. On the FHIR side, the applicable itemid-derived
Observation system is the proprietary
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, and the code is
the itemid value verbatim as text. No label or LOINC substitution is specified
by this SQL.

### Active WHERE allowlist, verbatim

This is the exact active literal list in the canonical SQL, including its
source comments and order. It is the port's complete row-selection code set:

```sql
(
            51146 -- basophils
            , 52069 -- Absolute basophil count
            , 51199 -- Eosinophil Count
            , 51200 -- Eosinophils
            , 52073 -- Absolute Eosinophil count
            , 51244 -- Lymphocytes
            , 51245 -- Lymphocytes, Percent
            , 51133 -- Absolute Lymphocyte Count
            , 52769 -- Absolute Lymphocyte Count
            , 51253 -- Monocyte Count
            , 51254 -- Monocytes
            , 52074 -- Absolute Monocyte Count
            , 51256 -- Neutrophils
            , 52075 -- Absolute Neutrophil Count
            , 51143 -- Atypical lymphocytes
            , 51144 -- Bands (%)
            , 51218 -- Granulocyte Count
            , 52135 -- Immature granulocytes (%)
            , 51251 -- Metamyelocytes
            , 51257  -- Nucleated Red Cells

            -- wbc totals measured in K/uL
            -- 52220 (wbcp) is percentage
            , 51300, 51301, 51755

            -- below are point of care tests which are extremely infrequent
            -- and usually low quality
            -- 51697, -- Neutrophils (mmol/L)

            -- below itemid do not have data as of MIMIC-IV v1.0
            -- 51536, -- Absolute Lymphocyte Count
            -- 51537, -- Absolute Neutrophil
            -- 51690, -- Lymphocytes
            -- 52151, -- NRBC

        )
```

The active integer literals are therefore exactly the 23 values named in that
block: `51146`, `52069`, `51199`, `51200`, `52073`, `51244`, `51245`, `51133`,
`52769`, `51253`, `51254`, `52074`, `51256`, `52075`, `51143`, `51144`,
`51218`, `52135`, `51251`, `51257`, `51300`, `51301`, and `51755`. The
commented values `52220`, `51697`, `51536`, `51537`, `51690`, and `52151` are
not executable filter literals and must not be added to the active port code
set. The SQL comments describe them as a percentage item or infrequent/
no-data candidates; they are not evidence here that any of them is an active
MIMIC-IV 2.2 filter.

### Code branches and output/CTE destinations

The active allowlist is reused by the following exact conditional code sets;
these sets are recorded separately because they determine which output or
intermediate column each code feeds:

| Exact SQL code expression | Source | Destination(s) |
|---|---|---|
| `itemid IN (51300, 51301, 51755)` | `mimiciv_hosp.labevents.itemid` | CTE `wbc`; also the WBC half of CTE `impute_abs` |
| `itemid = 52069` | same | CTE `basophils_abs` → final `basophils_abs` |
| `itemid = 52073` | same | CTE `eosinophils_abs` → final `eosinophils_abs` |
| `itemid = 51199` | same | CTE `eosinophils_abs`, divided by `1000.0` → final `eosinophils_abs` |
| `itemid = 51133` | same | CTE `lymphocytes_abs` → final `lymphocytes_abs` |
| `itemid = 52769` | same | CTE `lymphocytes_abs`, divided by `1000.0` → final `lymphocytes_abs` |
| `itemid = 52074` | same | CTE `monocytes_abs` → final `monocytes_abs` |
| `itemid = 51253` | same | CTE `monocytes_abs`, divided by `1000.0` → final `monocytes_abs` |
| `itemid = 52075` | same | CTE `neutrophils_abs` → final `neutrophils_abs` |
| `itemid = 51218` | same | CTE-only `granulocytes_abs`, divided by `1000.0`; not in final output |
| `itemid = 51146` | same | CTE `basophils` and percentage-sum half of `impute_abs` → final `basophils` |
| `itemid = 51200` | same | CTE `eosinophils` and percentage-sum half of `impute_abs` → final `eosinophils` |
| `itemid IN (51244, 51245)` | same | CTE `lymphocytes` and percentage-sum half of `impute_abs` → final `lymphocytes` |
| `itemid = 51254` | same | CTE `monocytes` and percentage-sum half of `impute_abs` → final `monocytes` |
| `itemid = 51256` | same | CTE `neutrophils` and percentage-sum half of `impute_abs` → final `neutrophils` |
| `itemid = 51143` | same | CTE/final `atypical_lymphocytes` |
| `itemid = 51144` | same | CTE/final `bands` |
| `itemid = 52135` | same | CTE/final `immature_granulocytes` |
| `itemid = 51251` | same | CTE/final `metamyelocytes` |
| `itemid = 51257` | same | CTE/final `nrbc` |
| `itemid IN (51146, 51200, 51244, 51245, 51254, 51256)` | same | percentage-sum predicate in CTE `impute_abs` |

The final five absolute columns additionally use the following source-to-output
fallback semantics: `basophils_abs` uses `basophils`; `eosinophils_abs` uses
`eosinophils`; `lymphocytes_abs` uses `lymphocytes`; `monocytes_abs` uses
`monocytes`; and `neutrophils_abs` uses `neutrophils`. Each fallback multiplies
the selected percentage by `wbc`, divides by `100`, casts to numeric, and
rounds to four places.

## Aggregations and absence of joins/windows

- `GROUP BY le.specimen_id` is the only GROUP BY.
- CTE aggregations: `MAX` for subject, admission, chart time, WBC, each
  conditional analyte, and the CTE-only granulocyte count; `SUM` for the six
  percentage values used by `impute_abs`.
- Final value aggregation/transformation: `ROUND(CAST(... AS NUMERIC), 4)`
  for the five absolute outputs.
- There are no window functions, `AVG`, `MIN`, `ARRAY_AGG`, `DISTINCT`,
  `HAVING`, `ORDER BY`, or time-bucketing operations.

## Dependency and downstream implications

The DAG says this is a level-0 concept with no `mimiciv_derived` dependencies.
Its generated result is named `mimiciv_derived.blood_differential`, and
`first_day_lab` is the listed downstream consumer. In `first_day_lab`, the
consumer joins this derived result to `mimiciv_icu.icustays` by `subject_id`
and a `charttime` window of six hours before through one day after ICU
`intime`; that window belongs to `first_day_lab`, not to this concept and must
not be added to the blood-differential source analysis.

## Mapping implications for the later FHIR stages

These are source-faithful constraints for a prober/implementer; no
ViewDefinition or SQL is authored here:

1. The likely source stream is labevents-derived `Observation`. Use the exact
   itemid code values and the lab-item code system named above. The curated
   notes state that labevents ETL writes `CAST(itemid AS TEXT)` verbatim and
   uses `d_labitems` only for display; there is no source-SQL basis for mapping
   these itemids to LOINC or replacing them with labels.
2. The output key is the lab `specimen_id`, not `(subject_id, charttime)`.
   Lab `Observation.specimen` and the lab `Specimen` identifier are therefore
   the important grouping spine. The notes report that the specimen reference
   and `identifier.system =
   http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab` preserve this
   source identifier; downstream code must cast the identifier string back to
   integer for the target shape.
3. `subject_id` comes from the patient identifier value and must be emitted as
   an integer rather than using the FHIR UUID resource key. The source
   `hadm_id` is nullable and the curated notes warn that lab Observation
   encounter references are incomplete. A later mapping should not use an
   INNER JOIN to Encounter to manufacture the source relation; if Encounter
   is consulted, preserve the row with a LEFT JOIN and verify the specific
   itemid population. Patient-plus-time admission re-derivation is a heuristic,
   not an exact inversion of this source column.
4. `charttime` is the maximum effective time among eligible rows in the
   specimen group. FHIR datetimes carry offsets; the notes require preserving
   the de-identified wall-clock value with a timezone-neutral timestamp cast in
   later Spark SQL rather than converting it through the machine timezone.
5. Numeric FHIR Quantity values may need explicit numeric casting when a
   materialized ViewDefinition alias is string-like. The source semantics
   require filtering NULL/negative numeric values before pivoting and applying
   the exact itemid-specific `/1000.0` conversions. Do not infer units from a
   display string or from a terminology mapping.
6. Preserve all 20 output columns, including columns that may be NULL. Do not
   add `granulocytes_abs` to that output: it is not an output of this concept,
   only a CTE intermediate. Do not let the presence of itemid `51218` be
   treated as a final granulocyte column. Conversely, itemid `51218` remains
   in the source allowlist and can create a specimen group even though its
   computed value is discarded.
7. The source SQL does not expose `value`, `valueuom`, reference ranges, or
   comments. A port should reproduce only the named numeric outputs and the
   source grouping/filter/aggregation behavior, not add those unselected
   fields.

No attempt artifact was read or modified: the active directory
`mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0001/`
was empty when inspected.
