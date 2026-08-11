# Source analysis: `gcs`

## Scope and authoritative inputs

- **Concept:** `gcs` (`measurement/gcs`)
- **Canonical SQL:** `mimic-iv/concepts/measurement/gcs.sql`
- **DAG node:** stem `gcs`, path `measurement/gcs.sql`, level `0`, SHA256
  `77d14660a8322928069c049cd1aa28eb8f356b7751f73eba2625358266f3039e`.
  The SHA256 was checked against the file on disk.
- **DAG dependencies:** none. The SQL has no `mimiciv_derived` reference.
  The DAG lists `first_day_gcs`, `sapsii`, and `sofa` as dependents; those are
  downstream concepts, not inputs to this port.
- **Oracle manifest shape:** `comparison: keyed_join`, `key: ["stay_id",
  "charttime"]`, `key_probes: 5`, `row_count: 1,637,763`.

The canonical SQL is BigQuery-qualified (`physionet-data.mimiciv_icu`) but the
logical source table is `mimiciv_icu.chartevents`.

## 1. Table and CTE references

Every `FROM`/`JOIN` reference is listed here. There is one physical source
table and one logical self-join over the `base` CTE.

| SQL location | Join type | Schema/table or CTE | Alias | Condition / use |
|---|---|---|---|---|
| `base`, line 50 | `FROM` | `mimiciv_icu.chartevents` | `ce` | Raw ICU chart events; item rows are pivoted by `(subject_id, stay_id, charttime)`. |
| `gcs`, line 90 | `FROM` | CTE `base` | `b` | Current pivoted stay/time row. |
| `gcs`, line 92 | `LEFT JOIN` | CTE `base` | `b2` | Immediate preceding pivoted row in the same stay, if it is within six hours; exact condition is recorded below. |
| `gcs_stg`, line 114 | `FROM` | CTE `gcs` | `gs` | Coalesces current and previous component values and computes `components_measured`. |
| final query, line 126 | `FROM` | CTE `gcs_stg` | `gs` | Projects the eight output columns. |

No `mimiciv_hosp` table is referenced. No dimension table (`d_items`) is
referenced by the canonical SQL.

## 2. Referenced source columns and inferred types

The source types below are from the MIMIC-IV v2.2 PostgreSQL DDL at
`mimic-iv/buildmimic/postgres/create.sql:369-383`; nullable results follow the
SQL expression rather than the source NOT NULL declaration.

### `mimiciv_icu.chartevents`

| Source column | Source type | References and role |
|---|---|---|
| `subject_id` | `INTEGER NOT NULL` | Selected into `base`; grouped; carried through `gcs`, `gcs_stg`, and final output. |
| `stay_id` | `INTEGER NOT NULL` | Selected/grouped; partitions the `ROW_NUMBER`; self-join key; carried through to output. |
| `charttime` | `TIMESTAMP NOT NULL` | Selected/grouped; `ROW_NUMBER` ordering; six-hour self-join window; carried through to output. |
| `itemid` | `INTEGER NOT NULL` | `WHERE ... IN (...)`; CASE discriminators for each component and the ETT flag. |
| `valuenum` | `FLOAT` | Numeric source for motor, verbal (except ETT text), and eye pivots; nullable in each aggregate result. |
| `value` | `VARCHAR(200)` | Exact text comparison to `'No Response-ETT'` for the verbal sentinel and ETT flag. |

`hadm_id`, `storetime`, `valueuom`, `warning`, and `caregiver_id` are not
referenced. No source column from another table is used.

### CTE `base` schema

`base` groups raw chart rows by `ce.subject_id`, `ce.stay_id`, and
`ce.charttime`, producing one pivot row per selected stay/time group:

| Column | Inferred type | Derivation |
|---|---|---|
| `subject_id` | `INTEGER` | `ce.subject_id` |
| `stay_id` | `INTEGER` | `ce.stay_id` |
| `charttime` | `TIMESTAMP` | `ce.charttime` |
| `gcsmotor` | nullable `FLOAT` | `MAX(CASE WHEN ce.itemid = 223901 THEN ce.valuenum ELSE NULL END)` |
| `gcsverbal` | nullable `FLOAT` | `MAX` of `0` for the exact ETT text, otherwise `ce.valuenum` for item `223900`, otherwise NULL. The integer sentinel is promoted to the numeric type of `valuenum`. |
| `gcseyes` | nullable `FLOAT` | `MAX(CASE WHEN ce.itemid = 220739 THEN ce.valuenum ELSE NULL END)` |
| `endotrachflag` | `INTEGER` | `MAX(CASE WHEN ce.itemid = 223900 AND ce.value = 'No Response-ETT' THEN 1 ELSE 0 END)`. It is 1 if any matching verbal row in the group has that text. |
| `rn` | window-row-number integer (`BIGINT` in PostgreSQL/Spark-like engines) | `ROW_NUMBER() OVER (PARTITION BY ce.stay_id ORDER BY ce.charttime ASC)` |

### CTE `gcs` schema and calculation

`b.*` carries every `base` column above. The self-join adds:

| Column | Inferred type | Derivation |
|---|---|---|
| `gcsverbalprev` | nullable `FLOAT` | `b2.gcsverbal` |
| `gcsmotorprev` | nullable `FLOAT` | `b2.gcsmotor` |
| `gcseyesprev` | nullable `FLOAT` | `b2.gcseyes` |
| `gcs` | `FLOAT` | A CASE expression: ETT current or previous verbal sentinel gives literal `15`; otherwise sums current/previous/default component values. It is logically non-NULL because every sum component has a normal default. |

The `gcs` CASE is evaluated in this order:

1. If `b.gcsverbal = 0`, output `15`.
2. If current verbal is NULL and `b2.gcsverbal = 0`, output `15`.
3. If `b2.gcsverbal = 0` but the first two cases did not apply, sum only
   current components, defaulting missing motor/verbal/eyes to `6`, `5`,/`4`;
   previous component values are deliberately not used in this branch.
4. Otherwise, for each component use current, then previous, then the normal
   default (`6` motor, `5` verbal, `4` eyes), and sum the three values.

The component columns selected later are not the same as the scalar GCS
calculation's defaults: they are only `COALESCE(current, previous)` and can be
NULL when neither current nor the immediately preceding in-window row has a
component.

### CTE `gcs_stg` schema

`gcs_stg` selects/derives:

| Column | Inferred type | Derivation / final fate |
|---|---|---|
| `subject_id` | `INTEGER` | From `gcs`; final output. |
| `stay_id` | `INTEGER` | From `gcs`; final output. |
| `charttime` | `TIMESTAMP` | From `gcs`; final output. |
| `gcs` | `FLOAT` | From `gcs`; final output. |
| `gcsmotor` | nullable `FLOAT` | `COALESCE(gcsmotor, gcsmotorprev)`; final alias `gcs_motor`. |
| `gcsverbal` | nullable `FLOAT` | `COALESCE(gcsverbal, gcsverbalprev)`; final alias `gcs_verbal`. |
| `gcseyes` | nullable `FLOAT` | `COALESCE(gcseyes, gcseyesprev)`; final alias `gcs_eyes`. |
| `components_measured` | `INTEGER` | Sum of three 0/1 CASE expressions, one for each coalesced component; not selected by the final query. |
| `endotrachflag` | `INTEGER` | From the current `gcs` row's `base` value; final alias `gcs_unable`. |

## 3. Final output schema

The final SELECT has exactly these columns, in this order. Types are confirmed
by `oracle_manifest.full.json` lines 2184-2226.

| # | Output column | SQL expression | Type |
|---:|---|---|---|
| 1 | `subject_id` | `gs.subject_id` | `INTEGER` |
| 2 | `stay_id` | `gs.stay_id` | `INTEGER` |
| 3 | `charttime` | `gs.charttime` | `TIMESTAMP` |
| 4 | `gcs` | `gcs` | `FLOAT` |
| 5 | `gcs_motor` | `gcsmotor` | `FLOAT` (nullable at component level) |
| 6 | `gcs_verbal` | `gcsverbal` | `FLOAT` (nullable at component level) |
| 7 | `gcs_eyes` | `gcseyes` | `FLOAT` (nullable at component level) |
| 8 | `gcs_unable` | `endotrachflag` | `INTEGER` |

`components_measured`, `rn`, and all `*prev` columns are intermediate only and
are not output. There is no final `WHERE`, `DISTINCT`, or `ORDER BY`.

## 4. Filters, windows, and value constraints

### WHERE predicate

The only WHERE clause in the canonical SQL is in `base`:

```sql
WHERE ce.itemid IN
    (
        -- GCS components, Metavision
        223900, 223901, 220739
    )
```

It admits all rows from `mimiciv_icu.chartevents` whose itemid is one of the
three listed values. There is no source time restriction, ICU-stay time
restriction, `value IS NOT NULL` predicate, `valuenum` range/positivity check,
subject filter, or exclusion predicate.

### Self-join time window

The `LEFT JOIN base b2` condition is:

```sql
ON b.stay_id = b2.stay_id
   AND b.rn = b2.rn + 1
   AND b2.charttime > DATETIME_SUB(b.charttime, INTERVAL '6' HOUR)
```

This is a strict lower-bound six-hour window. `rn = b2.rn + 1` selects only the
immediately preceding `base` row in the same `stay_id`; it does not search
backwards for an older qualifying row if that immediate predecessor is outside
the window. There is no separately written upper-bound predicate; the ascending
row number makes `b2` the previous row under the source data's non-NULL
`charttime` ordering.

### CASE predicates and special literals

These are not WHERE filters, but they alter the values that feed the output:

- `ce.itemid = 223901` selects the motor value for `gcsmotor`.
- `ce.itemid = 223900 AND ce.value = 'No Response-ETT'` maps verbal to numeric
  sentinel `0` and sets `endotrachflag` to `1`.
- `ce.itemid = 223900` otherwise supplies `ce.valuenum` to `gcsverbal`.
- `ce.itemid = 220739` selects the eye value for `gcseyes`.
- `b.gcsverbal = 0`, `b.gcsverbal IS NULL AND b2.gcsverbal = 0`, and
  `b2.gcsverbal = 0` control the special GCS calculation described above.
- Missing component defaults are the exact numeric literals `6`, `5`, and `4`;
  the ETT result is the exact literal `15`. The flag CASE uses exact literals
  `1` and `0`.

## 5. Literal code set, verbatim

This is the complete coded source specification. The SQL names no ICD code,
LOINC code, or other code system. The numeric itemids are from
`mimiciv_icu.chartevents.itemid` and feed the following intermediate and final
columns:

```sql
223900, 223901, 220739
```

| Exact literal | Source table/column | CTE expression(s) fed | Final output(s) fed |
|---|---|---|---|
| `223900` | `mimiciv_icu.chartevents.itemid` | `base.gcsverbal`; `base.endotrachflag` when paired with the ETT text | `gcs_verbal`, `gcs_unable`, and the scalar `gcs` calculation |
| `223901` | `mimiciv_icu.chartevents.itemid` | `base.gcsmotor` | `gcs_motor` and the scalar `gcs` calculation |
| `220739` | `mimiciv_icu.chartevents.itemid` | `base.gcseyes` | `gcs_eyes` and the scalar `gcs` calculation |

The exact non-numeric source-value literal used by the SQL is:

```sql
'No Response-ETT'
```

It filters `mimiciv_icu.chartevents.value` inside CASE expressions, not a
WHERE clause. It feeds `base.gcsverbal = 0` and `base.endotrachflag = 1`, which
then feed `gcs`, `gcs_verbal`, and `gcs_unable` as described above. The string is
recorded verbatim, including capitalization and hyphenation.

The source code set is therefore only the three itemids above plus this exact
text sentinel; no code has been expanded, translated, deduplicated, or replaced
with a label.

## 6. Joins and row multiplicity

There is one join, a `LEFT JOIN` of `base` to itself in CTE `gcs`. It preserves
every current `base` row even when no previous row qualifies. The equality on
`stay_id` prevents cross-stay carry-forward. The `rn` condition makes the right
side the immediately prior pivot row, and the strict six-hour predicate controls
whether its component values are available.

The `base` GROUP BY collapses all selected raw chartevents sharing
`(subject_id, stay_id, charttime)` into one row. Each component uses `MAX`, so
multiple raw rows for one item in the same group are not retained as separate
events. The self-join is expected to be at most one previous row per current
row because `rn` identifies the preceding grouped row; there is no join to a
dimension or encounter table and no join condition on `subject_id` beyond the
stay identifier.

## 7. Aggregation and window functions

- `GROUP BY ce.subject_id, ce.stay_id, ce.charttime` in `base`.
- Four `MAX` aggregates in `base`: motor pivot, verbal/ETT pivot, eye pivot,
  and ETT flag pivot.
- `ROW_NUMBER() OVER (PARTITION BY ce.stay_id ORDER BY ce.charttime ASC)` in
  `base`; there is no secondary tie-breaker.
- No `GROUP BY`, aggregate, or window function occurs after `base`.
- `gcs_stg.components_measured` is a row-wise sum of three CASE-derived 0/1
  values, not an aggregate.
- The final query does not sort or deduplicate rows.

## 8. Natural-key implications

The query's intentional row grain is one row per selected ICU `stay_id` and
`charttime` after the three item streams are pivoted. The final projection has
no source chartevent identifier and no itemid column, so raw event identity is
not preserved. Repeated raw observations at the same stay/time/item are folded
by `MAX`; repeated observations at different charttimes remain separate.

The immutable full oracle empirically records the smallest comparison key as
`(stay_id, charttime)` and uses `keyed_join`. The candidate should preserve that
key shape and must not add `itemid`, `rn`, or the intermediate component-count
column to the output. `subject_id` is an output identity column but is not part
of the manifest key. The source SQL itself does not declare uniqueness; the key
statement comes from the full-data oracle manifest, not from a demo-derived
assumption.

## 9. Coding-system implications from the read-only dataset notes

The canonical SQL itself names no FHIR URI. Under the coding policy, these are
proprietary ICU chartevents itemids. The read-only MIMIC-on-FHIR notes state that
the ETL carries an itemid verbatim as the Observation code under:

`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`

The exact code values remain the decimal strings corresponding to the SQL
itemids; no terminology service or label substitution is part of this source
analysis. The notes also require discrimination by `code.coding.system` plus
exact code rather than `meta.profile`. The categorical-chartevents note is
relevant to the exact verbal text sentinel because non-numeric chart values are
served as `valueString`; the numeric `valuenum` branch is a Quantity in the
FHIR representation, to be confirmed by the prober.

Other read-only notes relevant to later mapping are the identifier-string rule
for `subject_id`/`stay_id` and the `TIMESTAMP_NTZ` rule for offset-bearing FHIR
datetimes. These do not change the canonical SQL facts above.

## 10. Dataset-wide quirk to carry in the owned fragment

The FHIR chartevents ETL applies `value IS NOT NULL` before creating an
Observation (`mimic-fhir/sql/fhir_observation_chartevents.sql:34-38`), while
the canonical GCS query filters only itemid and therefore retains any selected
source row with a NULL `value` (`gcs.sql:50-57`). This is a dataset/ETL-wide
coverage quirk relevant to GCS, not a GCS-specific clinical rule; its actual
GCS item-level magnitude was not probed in this source-analysis stage. It was
recorded in the owned provisional fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/gcs.md`.

The existing `crrt` fragment also reports that repeated same-item chartevents
at one stay/time can be retained by the FHIR ETL; this is a relevant lead for
the GCS MAX pivot, but it remains provisional until a GCS-specific probe.
The existing `code_status` fragment reports the ETL's hard-coded duplicate-row
exclusion and the chartevents DST-gap time normalization; the latter is already
covered by the curated `MIMIC_NOTES.md` datetime entry. No new clinical or
coding interpretation was made here.

## Files and checks performed

- Read `AGENTS.md`, including the coding policy and carryover rules.
- Read `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` for comparison/key and
  representability implications.
- Read `mimic-iv/concept_dag/concept_dag.json`; checked the `gcs` node path,
  level, dependency list, dependents, and SHA256. The file hash matched.
- Read the canonical `mimic-iv/concepts/measurement/gcs.sql` line by line.
- Read `mimic-iv/buildmimic/postgres/create.sql:369-383` for source column
  types and nullability.
- Read `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` for output
  schema, row count, comparison mode, and natural key.
- Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`.
- Inspected all existing concept fragments under `MIMIC_NOTES.d` (the
  chartevents-relevant findings are in `code_status.md` and `crrt.md`; the
  itemid filtering safeguard is in `cardiac_marker.md`).
- Read `mimic-fhir/sql/fhir_observation_chartevents.sql:1-80` to verify the
  dataset-wide NULL-value omission and the verbatim chartevents code system.
- Confirmed `mimic-iv/concepts_fhir/concepts/measurement/gcs/attempt_0001/` was
  empty and did not create or edit any attempt implementation artifact.
