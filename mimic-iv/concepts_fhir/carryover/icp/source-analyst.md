# Source analysis: `icp`

## Scope and DAG identity

- **Concept:** `icp` (`measurement/icp`).
- **Canonical SQL:** `mimic-iv/concepts/measurement/icp.sql`.
- **DAG node:** stem `icp`, path `measurement/icp.sql`, level `0`, SHA256
  `d7a6ad8f8c455f2f177c26749a0fbf80d000e652dfda276b9782fa7dcd99f62c`.
  `uv run mimic_utils concept_dag --check` reported that the stored DAG
  artifacts match, and an independent SHA256 check matched this value.
- **DAG dependencies:** none. The SQL contains no reference to
  `mimiciv_derived`; `icp` is a level-0 concept with no listed dependents.
- The SQL uses a BigQuery project-qualified name, but its logical MIMIC source
  table is `mimiciv_icu.chartevents`.

## 1. Table and CTE references

Every `FROM`/`JOIN` clause is accounted for below.

| SQL location | Clause | Schema/table or CTE | Alias | Role |
|---|---|---|---|---|
| line 10, CTE `ce` | `FROM` | `mimiciv_icu.chartevents` | `ce` | Raw ICU chart events; only the two ICP itemids are admitted. |
| line 24, final query | `FROM` | CTE `ce` | `ce` | Reads the item-filtered and value-cleaned CTE rows for the final pivot. |

There are no `JOIN` clauses. No `mimiciv_hosp` table, dimension table, or
`mimiciv_derived` table is referenced.

## 2. Referenced columns and inferred types

The source types below follow the MIMIC-IV v2.2 PostgreSQL DDL at
`mimic-iv/buildmimic/postgres/create.sql:369-383`.

### `mimiciv_icu.chartevents`

| Source column | Source type | Use in the SQL |
|---|---|---|
| `ce.subject_id` | `INTEGER NOT NULL` | Selected into CTE `ce`, selected in the final output, and grouped in the final query. |
| `ce.stay_id` | `INTEGER NOT NULL` | Selected into CTE `ce`, selected in the final output, and grouped in the final query. |
| `ce.charttime` | `TIMESTAMP NOT NULL` | Selected into CTE `ce`, selected in the final output, and grouped in the final query. |
| `ce.itemid` | `INTEGER NOT NULL` | Exact itemid `IN` filter. |
| `ce.valuenum` | `FLOAT` (nullable) | Strict positive/less-than-100 value test and numeric input to the `icp` CASE expression. |

`hadm_id`, `caregiver_id`, `storetime`, `value`, `valueuom`, and `warning` are
not referenced by the canonical SQL. In particular, the SQL does not use a
source error column or a text-value predicate.

### CTE `ce`

The CTE has four columns:

| CTE column | Inferred type/nullability | Expression |
|---|---|---|
| `subject_id` | `INTEGER NOT NULL` | `ce.subject_id` |
| `stay_id` | `INTEGER NOT NULL` | `ce.stay_id` |
| `charttime` | `TIMESTAMP NOT NULL` | `ce.charttime` |
| `icp` | nullable `FLOAT` | `CASE WHEN valuenum > 0 AND valuenum < 100 THEN valuenum ELSE NULL END` |

The `icp` alias is created in the CTE and is the only CTE-derived value used by
the final aggregate.

## 3. Final output schema and natural grain

The final `SELECT` emits exactly these columns, in this order:

| # | Output column | SQL expression | Inferred type/nullability |
|---:|---|---|---|
| 1 | `subject_id` | `ce.subject_id` | `INTEGER NOT NULL` for eligible source groups |
| 2 | `stay_id` | `ce.stay_id` | `INTEGER NOT NULL` for eligible source groups |
| 3 | `charttime` | `ce.charttime` | `TIMESTAMP NOT NULL` for eligible source groups |
| 4 | `icp` | `MAX(icp)` | nullable `FLOAT` |

The intentional row grain is one row per `(subject_id, stay_id, charttime)`
group among source chartevents whose `itemid` is one of the two selected ICP
codes. The final query does not retain `itemid` or a source event identifier.
Both ICP monitor streams therefore feed the same output `icp`; repeated rows
at the same group are collapsed by `MAX`. A group survives even if every
selected `valuenum` is NULL or outside the valid range, in which case
`MAX(icp)` is NULL.

The SQL itself does not declare a uniqueness constraint beyond this grouped
grain. It has no `DISTINCT` or `ORDER BY`.

## 4. Filters and value constraints

### Active `WHERE` predicate

The only `WHERE` clause is in CTE `ce`:

```sql
WHERE ce.itemid IN
    (
        220765 -- Intra Cranial Pressure -- 92306
        , 227989 -- Intra Cranial Pressure #2 -- 1052
    )
```

This retains all raw chartevents rows with either selected `itemid`. There is
no time window, subject/stay restriction, admission restriction, unit filter,
`value IS NOT NULL` predicate, `warning`/error exclusion, or code exclusion.

The immediately preceding comment says `-- exclude rows marked as error`, but
no executable error predicate follows it. The MIMIC-IV v2.2 chartevents DDL
has `warning` but no referenced `error` column; the actual behavior is the
itemid-only filter above.

### Value constraint in the CTE `CASE`

This is not a row-eliminating `WHERE` filter:

```sql
CASE
    WHEN valuenum > 0 AND valuenum < 100 THEN valuenum ELSE NULL
END AS icp
```

The bounds are strict: values `<= 0`, `>= 100`, and NULL `valuenum` become
NULL. The source row remains in its `(subject_id, stay_id, charttime)` group;
the outer `MAX` aggregates the remaining valid values. No unit conversion or
other value constraint is present.

## 5. Literal code set, verbatim

The complete coded filter is the following exact source SQL set:

```sql
220765 -- Intra Cranial Pressure -- 92306
, 227989 -- Intra Cranial Pressure #2 -- 1052
```

The code literals are `220765` and `227989`. The trailing `92306` and `1052`
are comments in the source, not additional itemids or codes.

| Exact literal | Source table/column filtered | CTE expression(s) fed | Final output fed |
|---:|---|---|---|
| `220765` | `mimiciv_icu.chartevents.itemid` | `ce.icp` after the `valuenum` range CASE | `icp` via `MAX(icp)` |
| `227989` | `mimiciv_icu.chartevents.itemid` | `ce.icp` after the `valuenum` range CASE | `icp` via `MAX(icp)` |

The SQL names no ICD code, `icd_version`, LOINC code, or other standard coded
set. Under the read-only coding policy and notes, these are proprietary ICU
chartevents itemids. The corresponding served Observation coding system is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, with
the source itemids carried verbatim as code strings; this is a representation
fact from the notes/ETL, not a translation or expansion of the SQL code set.

## 6. Joins

There are no joins, so there are no INNER or LEFT join conditions, join
multiplication, or join-induced row loss in the canonical query. `FROM ce` is
a CTE read, not a join.

## 7. Aggregations and windows

- `GROUP BY ce.subject_id, ce.stay_id, ce.charttime` is the only grouping.
- `MAX(icp)` is the only aggregate and produces the final value.
- There are no window functions, `MIN`, `AVG`, `SUM`, `ARRAY_AGG`, or other
  value aggregations.
- The outer `MAX` is applied after the CTE's per-row range cleaning, so it
  selects the maximum valid ICP across both selected itemids and all matching
  raw rows at the same subject/stay/time group.

## 8. Dependencies and relevant dataset notes

There are no `mimiciv_derived` dependencies. The only raw dependency is
`mimiciv_icu.chartevents`.

The read-only `MIMIC_NOTES.md` and relevant provisional fragments were checked.
They establish the following downstream-relevant facts without changing the
source SQL specification:

- chartevents itemids are written verbatim to
  `Observation.code.coding.code` under the proprietary
  `mimic-chartevents-d-items` system; discrimination should use system plus
  exact code, not `meta.profile`.
- Chartevents Observations can retain repeated same-item rows at one
  stay/time, so the source `MAX` grouping is load-bearing rather than an
  assumption that the FHIR stream is already unique.
- The chartevents ETL applies a global `value IS NOT NULL` condition and a
  hard-coded duplicate-row exclusion before creating Observations, while this
  canonical SQL has no such conditions. That ETL-level coverage difference is
  recorded in the owned provisional fragment
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/icp.md`; no ICP-specific row-count
  probe was performed here.
- FHIR datetime and Quantity materialization have type/time handling caveats
  recorded in the notes; those affect later representation, not the source
  columns, filters, or output grain described above.

## Evidence of source checks

- Read `AGENTS.md`, including the coding policy, carryover rules, immutable
  attempt rules, and the requirement to preserve literal source codes.
- Read `mimic-iv/concepts/measurement/icp.sql` line by line.
- Read `mimic-iv/concept_dag/concept_dag.json`; checked the `icp` node's path,
  level, dependency list, and SHA256. The stored DAG passed
  `uv run mimic_utils concept_dag --check`.
- Read `mimic-iv/buildmimic/postgres/create.sql:369-383` for the referenced
  chartevents source types and nullability.
- Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`, plus the relevant
  chartevents findings in `gcs.md`, `height.md`, `crrt.md`, and
  `code_status.md` and the related numeric observation findings.
- Read `mimic-fhir/sql/fhir_observation_chartevents.sql:6-38,58-80` only to
  verify the dataset-wide chartevents ETL behavior noted above; no SQL was
  executed.
- No ViewDefinition, `concept.sql`, attempt artifact, or implementation
  artifact was authored.
