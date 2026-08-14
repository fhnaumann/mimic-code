# Source analysis: `rhythm`

## Scope and DAG identity

- **Concept:** `rhythm` (`measurement/rhythm`).
- **Canonical SQL:** `mimic-iv/concepts/measurement/rhythm.sql`.
- **DAG node:** stem `rhythm`, path `measurement/rhythm.sql`, level `0`, SHA256
  `97a4b14b1d493605f91ce7587e05fdf0990e1ba1cdfe5562d2e522996219517d`.
- **DAG dependencies:** none. The SQL contains no reference to a
  `mimiciv_derived` table, so no other concept must be ported first for this
  source query. The DAG lists no dependents for `rhythm`.
- The source uses a BigQuery project-qualified table name. Its logical MIMIC
  source is `mimiciv_icu.chartevents`.
- The immutable full oracle manifest records the output shape as
  `keyed_join` with key `(subject_id, charttime)`, seven output columns, and
  `row_count: 5,873,723`. The manifest is a comparison artifact, not part of
  the canonical SQL, but confirms the SQL-defined grouped grain.

## 1. Table and relation references

Every `FROM`/`JOIN` reference in the canonical SQL is accounted for here.

| SQL location | Clause | Logical schema/table | Alias | Role |
|---|---|---|---|---|
| line 19 | `FROM` | `mimiciv_icu.chartevents` | `ce` | Raw ICU chart events; rows are filtered by non-null `stay_id` and the five selected itemids, then pivoted at patient/chart-time grain. |

There are no `JOIN` clauses, no CTEs, no dimension-table references, and no
references to `mimiciv_hosp`. The generated DuckDB/PostgreSQL dialect copies
also read only `mimiciv_icu.chartevents`; their `mimiciv_derived.rhythm` name
is the generated destination table, not an input dependency of the canonical
SQL.

## 2. Source columns and inferred types

The referenced source types below follow the MIMIC-IV v2.2 PostgreSQL DDL in
`mimic-iv/buildmimic/postgres/create.sql:370-383`.

### `mimiciv_icu.chartevents`

| Source column | DDL type/nullability | References and role |
|---|---|---|
| `ce.subject_id` | `INTEGER NOT NULL` | Selected to the final output and grouped; forms the patient portion of the output grain/key. |
| `ce.charttime` | `TIMESTAMP NOT NULL` | Selected to the final output and grouped; forms the temporal portion of the output grain/key. |
| `ce.stay_id` | `INTEGER NOT NULL` in the v2.2 DDL | `WHERE ce.stay_id IS NOT NULL`; controls row inclusion but is not selected, grouped, or output. |
| `ce.itemid` | `INTEGER NOT NULL` | Exact `IN` filter and per-output `CASE` discriminator. It is not output. The unqualified `itemid` references inside the aggregate expressions resolve to this source column. |
| `ce.value` | `VARCHAR(200)` nullable | Text input to `heart_rhythm` and all four ectopy outputs. It is not directly selected. |

The source columns `hadm_id`, `caregiver_id`, `storetime`, `valuenum`,
`valueuom`, and `warning` are not referenced by the canonical SQL. In
particular, the query uses the text `value`, not `valuenum`, and has no
store-time ordering.

### Intermediate relations

There are no CTEs or other intermediate named relations. The only
intermediate values are the row-wise `CASE` expressions inside the final
aggregates:

- `CASE WHEN itemid = 220048 THEN value ELSE NULL END` feeds
  `STRING_AGG` for `heart_rhythm`.
- `CASE WHEN itemid = 224650 THEN value ELSE NULL END` feeds `MAX` for
  `ectopy_type`.
- `CASE WHEN itemid = 224651 THEN value ELSE NULL END` feeds `MAX` for
  `ectopy_frequency`.
- `CASE WHEN itemid = 226479 THEN value ELSE NULL END` feeds `MAX` for
  `ectopy_type_secondary`.
- `CASE WHEN itemid = 226480 THEN value ELSE NULL END` feeds `MAX` for
  `ectopy_frequency_secondary`.

All five expressions are nullable `VARCHAR`-like values because their source
`value` branch is nullable and their other branch is `NULL`.

## 3. Final output schema and grain

The final `SELECT` emits exactly these columns, in this order:

| # | Output column | SQL expression | Inferred/oracle type | Nullability implication |
|---:|---|---|---|---|
| 1 | `subject_id` | `ce.subject_id` | `INTEGER` | Non-null for every surviving source group because the source column is non-null. |
| 2 | `charttime` | `ce.charttime` | `TIMESTAMP` | Non-null for every surviving source group because the source column is non-null. |
| 3 | `heart_rhythm` | `STRING_AGG(DISTINCT CASE WHEN itemid = 220048 THEN value ELSE NULL END, '; ' ORDER BY CASE WHEN itemid = 220048 THEN value ELSE NULL END)` | `VARCHAR` | Nullable; `STRING_AGG` has no non-NULL input when a group has no non-NULL heart-rhythm value. |
| 4 | `ectopy_type` | `MAX(CASE WHEN itemid = 224650 THEN value ELSE NULL END)` | `VARCHAR` | Nullable; `MAX` ignores NULL values and is NULL if no non-NULL value for this item exists in the group. |
| 5 | `ectopy_frequency` | `MAX(CASE WHEN itemid = 224651 THEN value ELSE NULL END)` | `VARCHAR` | Nullable; same aggregate behavior. |
| 6 | `ectopy_type_secondary` | `MAX(CASE WHEN itemid = 226479 THEN value ELSE NULL END)` | `VARCHAR` | Nullable; same aggregate behavior. |
| 7 | `ectopy_frequency_secondary` | `MAX(CASE WHEN itemid = 226480 THEN value ELSE NULL END)` | `VARCHAR` | Nullable; same aggregate behavior. |

The intentional grain is one output row for every distinct
`(subject_id, charttime)` among source rows satisfying the `WHERE` clause.
`stay_id` is deliberately **not** part of the `GROUP BY` and is not an output
column. Thus source events from more than one non-null ICU stay for the same
patient and timestamp would be combined into one result row. The manifest's
comparison key is exactly `(subject_id, charttime)`; downstream code must not
add `stay_id` or `itemid` to that key.

The query has no `DISTINCT` on the final rows and no `ORDER BY` on the final
result. The only distinct operation is inside `STRING_AGG`.

## 4. Filters and value predicates

The only `WHERE` clause is at lines 20-28:

```sql
WHERE ce.stay_id IS NOT NULL
    AND ce.itemid IN
    (
        220048 -- Heart Rhythm
        , 224650 -- Ectopy Type 1
        , 224651 -- Ectopy Frequency 1
        , 226479 -- Ectopy Type 2
        , 226480  -- Ectopy Frequency 2
    )
```

Predicate details:

1. `ce.stay_id IS NOT NULL` admits only rows with a non-null ICU stay ID. The
   checked v2.2 raw DDL declares `stay_id INTEGER NOT NULL`, so this is
   logically redundant for schema-conformant raw rows, but it remains an
   executable source predicate and must not be dropped from the source
   specification.
2. `ce.itemid IN (...)` is the positive itemid allow-list. It is the only
   coded row filter.

There is no time window, admission restriction, subject restriction,
`value IS NOT NULL` predicate, `valuenum` constraint, unit constraint,
warning/error exclusion, or code exclusion. A selected source row with a NULL
`value` still contributes to the grouped row; it simply contributes NULL to
each applicable aggregate.

The `CASE` expressions are value-routing predicates rather than row-eliminating
filters. They route item-specific `value` strings into the five output
aggregates. No text value is compared against a literal in this SQL.

## 5. Literal code set, verbatim

The complete active itemid set is copied verbatim from the source SQL,
including its comments and source ordering:

```sql
220048 -- Heart Rhythm
, 224650 -- Ectopy Type 1
, 224651 -- Ectopy Frequency 1
, 226479 -- Ectopy Type 2
, 226480  -- Ectopy Frequency 2
```

Every literal is an `itemid` in `mimiciv_icu.chartevents`; the same itemids
also occur in the row-routing `CASE` expressions. No ICD code, ICD version,
LOINC code, or other coded system is named.

| Exact literal | Source table/column filtered or discriminated | Intermediate expression fed | Final output fed |
|---:|---|---|---|
| `220048` | `mimiciv_icu.chartevents.itemid`, in `ce.itemid IN (...)` and `CASE WHEN itemid = 220048` | Heart-rhythm `CASE` value expression | `heart_rhythm` via `STRING_AGG(DISTINCT ..., '; ' ORDER BY ...)` |
| `224650` | `mimiciv_icu.chartevents.itemid`, in `ce.itemid IN (...)` and `CASE WHEN itemid = 224650` | Ectopy type 1 `CASE` value expression | `ectopy_type` via `MAX(...)` |
| `224651` | `mimiciv_icu.chartevents.itemid`, in `ce.itemid IN (...)` and `CASE WHEN itemid = 224651` | Ectopy frequency 1 `CASE` value expression | `ectopy_frequency` via `MAX(...)` |
| `226479` | `mimiciv_icu.chartevents.itemid`, in `ce.itemid IN (...)` and `CASE WHEN itemid = 226479` | Ectopy type 2 `CASE` value expression | `ectopy_type_secondary` via `MAX(...)` |
| `226480` | `mimiciv_icu.chartevents.itemid`, in `ce.itemid IN (...)` and `CASE WHEN itemid = 226480` | Ectopy frequency 2 `CASE` value expression | `ectopy_frequency_secondary` via `MAX(...)` |

The comments (`Heart Rhythm`, `Ectopy Type 1`, `Ectopy Frequency 1`, `Ectopy
Type 2`, and `Ectopy Frequency 2`) are source comments only; the numeric
literals above are the complete code specification. No dead coded filter is
present in this SQL.

Under the read-only coding policy and curated notes, the corresponding served
chartevents Observation coding system is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, with
the exact itemid values carried as code strings. That is a downstream
representation fact, not a translation or expansion of the source code set.

## 6. Joins

There are no joins. Therefore there are no INNER/LEFT join conditions,
join-induced row multiplication, or join-induced row loss in the canonical
query. `FROM ce` is the single base-table read.

## 7. Aggregations and windows

The only grouping is:

```sql
GROUP BY ce.subject_id, ce.charttime
```

The aggregates are:

1. `STRING_AGG(DISTINCT ..., '; ' ORDER BY ...)` for `heart_rhythm`.
   The expression is NULL for all non-`220048` rows, so those rows are
   ignored by the aggregate. Non-NULL `220048` text values are deduplicated,
   sorted by the same text expression, and joined using the exact delimiter
   `'; '`.
2. `MAX(...)` for `ectopy_type` (`224650`). This is a lexical maximum of the
   source text values within the group, not a latest-by-time selection.
3. `MAX(...)` for `ectopy_frequency` (`224651`), also lexical over text.
4. `MAX(...)` for `ectopy_type_secondary` (`226479`), also lexical over text.
5. `MAX(...)` for `ectopy_frequency_secondary` (`226480`), also lexical over
   text.

There are no window functions, `MIN`, `AVG`, `SUM`, `ARRAY_AGG`, temporal
carry-forward operations, or post-aggregation filters.

## 8. Semantically essential source inputs

These are the source fields/discriminators whose values can change row
inclusion, the natural key/grouping, or a clinically meaningful output:

- **`subject_id`:** controls final grouping, is part of the natural output key,
  and is emitted unchanged as `subject_id`.
- **`charttime`:** controls final grouping, is part of the natural output key,
  and is emitted unchanged as `charttime`. It is the temporal value shared by
  all five output aggregates in a row.
- **`stay_id`:** controls row inclusion through `IS NOT NULL`. It is not part of
  the output key, not grouped, and not emitted. Its absence/presence can still
  determine whether a source row participates in a `(subject_id, charttime)`
  group.
- **`itemid`:** controls admission to the query and routes each row to exactly
  one of the five item-specific aggregate expressions. The itemid is not
  emitted, so its role is represented only through the selected output
  columns and aggregate behavior.
- **`value`:** supplies every clinically meaningful output value. For
  `220048`, its distinct set and lexical order determine the semicolon-joined
  `heart_rhythm`; for each ectopy item, its lexical maximum determines the
  corresponding output. A NULL value is not a row filter in the source SQL,
  but it is ignored by the relevant aggregate and can leave an output field
  NULL.

The following source fields are not semantically used by this query:
`hadm_id`, `caregiver_id`, `storetime`, `valuenum`, `valueuom`, and `warning`.
In particular, there is no source temporal carry-forward or latest-value rule
that would make `storetime` relevant.

## 9. MIMIC-on-FHIR representability risks

These are descriptive risks for the FHIR prober and later equivalence judge;
they are not a terminal representability decision.

1. **Chartevents code filtering must preserve the exact five itemids.** The
   curated notes state that itemid-derived chartevents Observations carry the
   source itemid verbatim in `Observation.code.coding.code` under the
   `mimic-chartevents-d-items` system. Filter on system plus the exact code,
   not on a profile or a translated label. The five output branches are
   categorical item streams and should be probed through the served value
   representation rather than assuming a numeric Quantity.
2. **Categorical text is carried as `Observation.valueString`.** The curated
   notes specifically state that categorical chartevents values are strings,
   not CodeableConcepts. Since this source uses `chartevents.value` and never
   `valuenum`, losing `valueString` would lose the values that feed all five
   aggregates. The exact target item-level presence and text fidelity still
   require a rhythm-specific probe.
3. **The FHIR ETL has a global NULL-value omission that the source SQL does
   not.** The canonical query has no `value IS NOT NULL` predicate, while the
   chartevents ETL documented in the notes excludes NULL-valued rows before
   creating Observations. If a selected patient/time group consists only of
   rows whose source values are NULL, the source still emits a grouped row
   (with nullable aggregate outputs), but the FHIR stream may have no row to
   represent it. The magnitude and exact effect for these five itemids were
   not established by this source analysis.
4. **The temporal key is transformed by the FHIR ETL.** The source groups on
   naive `charttime`. Curated notes state that chartevents
   `Observation.effectiveDateTime` is written after a `TIMESTAMPTZ` cast and
   that spring-forward DST-gap wall times are irreversibly normalized by one
   hour. Because `charttime` is both a grouping key and output column, the
   transformation can create missing source keys, candidate-only shifted
   keys, or collisions with genuine 03:xx rows; collisions can change the
   `STRING_AGG` and `MAX` results, not merely the displayed timestamp. Resource
   IDs are opaque and must not be parsed or regenerated to recover the source
   time.
5. **The SQL groups by patient/time, not ICU stay.** A FHIR implementation
   that groups by `Encounter`/`stay_id` would change the source grain. The
   source only requires non-null `stay_id` and then discards it. The prober
   must check how ICU stay context is represented, while preserving the
   output key `(subject_id, charttime)` rather than adding stay identity.
6. **Repeated chartevents must remain available until the source aggregates
   are replayed.** The curated fragments report that the ETL can preserve
   repeated same-item Observations at one patient/time. This matters because
   `heart_rhythm` uses a distinct value set and each ectopy field uses a
   maximum over all values; pre-deduplicating by patient/time/item without
   preserving all differing text values can change the result. Conversely,
   the source itself deliberately deduplicates equal heart-rhythm text values
   inside `STRING_AGG`.
7. **Identifier and datetime type conversions remain shape concerns.** The
   notes state that MIMIC identifiers arrive in FHIR `identifier.value` as
   strings and that offset-bearing FHIR datetimes should be cast to
   `TIMESTAMP_NTZ` to preserve the de-identified wall-clock value. Those facts
   affect later output typing and timestamp comparison, while the source
   types remain `INTEGER` and `TIMESTAMP` as documented above.

No source field is used for a temporal carry-forward, and no missing source
discriminator beyond the fields listed above was inferred. The prober must
verify whether the value, code, subject identifier, stay inclusion, and
effective time survive sufficiently for this exact grouped derivation.

## Files read and checks performed

- Read `AGENTS.md` for the source-analysis, carryover, coding, and
  representability rules.
- Read the canonical source SQL
  `mimic-iv/concepts/measurement/rhythm.sql` line by line.
- Read `mimic-iv/concept_dag/concept_dag.json`; checked the `rhythm` node path,
  level, dependency list, and stored SHA256.
- Read `mimic-iv/buildmimic/postgres/create.sql:370-383` for raw
  `mimiciv_icu.chartevents` types and nullability.
- Read `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` at the
  `rhythm` entry for the seven-column schema, `(subject_id, charttime)` key,
  comparison mode, and row count.
- Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`.
- Read the relevant provisional fragments
  `MIMIC_NOTES.d/crrt.md`, `MIMIC_NOTES.d/oxygen_delivery.md`, and
  `MIMIC_NOTES.d/icustay_times.md` for repeated chartevents, `issued`, and
  aggregation/time-transformation leads. These fragments were treated as
  provisional findings, not as terminal evidence.
- Read the generated dialect copies
  `mimic-iv/concepts_duckdb/measurement/rhythm.sql` and
  `mimic-iv/concepts_postgres/measurement/rhythm.sql` only as corroborating
  expansions of the same logical query; the canonical source remains the
  authority.
- No SQL was executed. No ViewDefinition, derived `concept.sql`, or attempt
  artifact was authored or modified.
