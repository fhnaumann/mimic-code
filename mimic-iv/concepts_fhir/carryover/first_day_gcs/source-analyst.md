# Source analysis: `first_day_gcs`

This is a description of the canonical source SQL, not a ViewDefinition or a
terminal representability decision.

## Source and DAG checks

- Canonical SQL read: `mimic-iv/concepts/firstday/first_day_gcs.sql`.
- DAG metadata read: `mimic-iv/concept_dag/concept_dag.json`.
- Curated dataset/IG notes read: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- The DAG node is `first_day_gcs`, path `firstday/first_day_gcs.sql`, level 1,
  SHA256
  `ebbabc9c407dcea8acc5363636ee6218723192aa6122e49e2e4d553ce958a4a5`.
  Its only DAG dependency is `gcs`; the DAG places `gcs` immediately before
  `first_day_gcs` in the relevant topological order.
- The stored DAG check passed: `uv run mimic_utils concept_dag --check`
  reported that the DAG matches its JSON and Markdown artifacts.
- The oracle manifest was also read for the recorded output schema and key;
  the source DDL was read to confirm the raw column types. No immutable
  attempt artifact was edited.

## Table references

Direct references in the canonical `first_day_gcs.sql` are:

| SQL clause | Alias | Schema | Table | Directly used columns |
|---|---|---|---|---|
| `FROM` in `gcs_final` | `ie` | `mimiciv_icu` | `icustays` | `subject_id`, `stay_id`, `intime` |
| `LEFT JOIN` in `gcs_final` | `g` | `mimiciv_derived` | `gcs` | `stay_id`, `charttime`, `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs_unable` |
| outer `FROM` | `ie` | `mimiciv_icu` | `icustays` | `subject_id`, `stay_id` |
| outer `LEFT JOIN` | `gs` | CTE `gcs_final` | — | `stay_id`, `gcs_seq`, `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, `gcs_unable` |

There is no direct `mimiciv_hosp` table reference. The `physionet-data.`
prefixes in the canonical SQL are deployment qualifiers; the schemas and
tables are the ones shown above.

The `gcs` dependency itself is the level-0 concept at
`mimic-iv/concepts/measurement/gcs.sql`. Its raw source table is
`mimiciv_icu.chartevents`; that is dependency provenance, not an additional
direct table reference that this consumer may rederive. The DAG's external
table metadata correspondingly lists `mimiciv_icu.icustays` for
`first_day_gcs` and `mimiciv_icu.chartevents` for `gcs`.

## Columns and inferred types

### Direct target SQL

The raw `mimiciv_icu.icustays` DDL defines `subject_id` and `stay_id` as
`INTEGER` and `intime` as `TIMESTAMP`. The dependency output's `stay_id` is an
`INTEGER` and `charttime` is a `TIMESTAMP`.

`gcs_final` has these columns:

1. `ie.subject_id` — `INTEGER`; retained as the stay's subject identifier.
2. `ie.stay_id` — `INTEGER`; joins to `g` and partitions the selected GCS
   rows.
3. `g.gcs` — `FLOAT` numeric GCS total.
4. `g.gcs_motor` — `FLOAT` numeric motor component.
5. `g.gcs_verbal` — `FLOAT` numeric verbal component.
6. `g.gcs_eyes` — `FLOAT` numeric eye component.
7. `g.gcs_unable` — `INTEGER` 0/1 flag.
8. `gcs_seq` — integer-valued `ROW_NUMBER()` result (an engine may materialize
   a window ordinal as a wider integer); it is only used to select `1` and is
   not an output column.

The outer query outputs the following seven columns. These types agree with
the `first_day_gcs` entry in `oracle_manifest.full.json`:

| Output column | Expression | Type |
|---|---|---|
| `subject_id` | `ie.subject_id` | `INTEGER` |
| `stay_id` | `ie.stay_id` | `INTEGER` |
| `gcs_min` | `gs.gcs` (written unqualified as `gcs`) | `FLOAT` |
| `gcs_motor` | `gs.gcs_motor` | `FLOAT` |
| `gcs_verbal` | `gs.gcs_verbal` | `FLOAT` |
| `gcs_eyes` | `gs.gcs_eyes` | `FLOAT` |
| `gcs_unable` | `gs.gcs_unable` | `INTEGER` |

`gcs` is not a dependency column that may be reconstructed from FHIR by this
consumer. The exact dependency columns read by this SQL are `stay_id`,
`charttime`, `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable`.
The dependency's `subject_id` exists in `gcs.sql` but is not read here; the
outer query takes `subject_id` from `icustays`.

### Relevant upstream dependency columns

The canonical `gcs.sql` reads these raw `mimiciv_icu.chartevents` fields:

- `subject_id`, `stay_id`, and `charttime` identify and group chart rows.
- `itemid` selects and pivots the three GCS streams.
- `valuenum` supplies the numeric component values.
- `value` supplies the special verbal-response discriminator
  `'No Response-ETT'`.

It emits `stay_id`, `charttime`, `gcs`, `gcs_motor`, `gcs_verbal`,
`gcs_eyes`, and `gcs_unable` among its final columns. The upstream
`subject_id` is not consumed by `first_day_gcs`.

## Filters and literal code specification

### Filters in `first_day_gcs.sql`

There is no `WHERE` clause, no ICD filter, no value-range predicate, and no
explicit null exclusion in the target SQL. The inclusion/time predicates are
join predicates:

- A dependency row must have the same `stay_id` as the ICU stay.
- `g.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)` is inclusive.
- `g.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)` is inclusive.
- The outer join retains only the `gcs_final` row where `gs.gcs_seq = 1`, but
  because this is in the `ON` clause of a `LEFT JOIN`, every `icustays` row is
  retained even when it has no qualifying GCS row.

The source comment calls this the first 24 hours, but the literal window is
from six hours before `intime` through one day after `intime` (an inclusive
30-hour span relative to `intime`).

### Exact item/code literals from the dependency

The target has no direct coded filter. The only itemid filter feeding its
`gcs` dependency is copied verbatim from `gcs.sql`:

```sql
WHERE ce.itemid IN
    (
        -- GCS components, Metavision
        223900, 223901, 220739
    )
```

This set filters `mimiciv_icu.chartevents.itemid` in the dependency's `base`
CTE. The exact literals and their downstream feeds are:

| Exact itemid | SQL comment label | Dependency feed | `first_day_gcs` output(s) reached |
|---|---|---|---|
| `223900` | `GCS - Verbal Response` | `gcsverbal`; also `endotrachflag` when its value is the ETT literal | `gcs_verbal`, `gcs_min`, `gcs_unable` |
| `223901` | `GCS - Motor Response` | `gcsmotor` | `gcs_motor`, `gcs_min` |
| `220739` | `GCS - Eye Opening` | `gcseyes` | `gcs_eyes`, `gcs_min` |

The exact non-itemid literal discriminator in the dependency is:

```sql
ce.value = 'No Response-ETT'
```

It is evaluated only for itemid `223900` in two `CASE` expressions. In the
`gcsverbal` pivot it produces numeric `0`; otherwise item `223900` uses
`ce.valuenum`. In the `endotrachflag` pivot it produces `1`; otherwise the
flag is `0`. It therefore feeds `gcs_verbal`, `gcs_unable`, and the total
`gcs`, which becomes this target's `gcs_min` after row selection. The SQL does
not name a literal `'No Response'` filter; that label is distinguished only by
not matching the exact ETT literal and consequently taking the ordinary
`valuenum` branch.

No other coded literals, ICD codes, code exclusions, or invented/expanded
itemids occur in the target or its direct dependency.

For downstream FHIR coding context, `MIMIC_NOTES.md` identifies itemid-derived
chartevents as the proprietary `mimic-chartevents-d-items` code system and
states that the code is the source itemid verbatim. The canonical SQL itself
names only the relational `itemid` column and does not name a FHIR URI.

## Joins and row selection

1. **CTE `gcs_final`: LEFT JOIN.**
   `mimiciv_icu.icustays ie` is left joined to `mimiciv_derived.gcs g` on
   `ie.stay_id = g.stay_id` plus the inclusive `-6 hour` to `+1 day` charttime
   window relative to `ie.intime`. This preserves ICU stays with no GCS
   dependency row, with the GCS columns null in the eventual output.
2. **Outer query: LEFT JOIN.**
   `mimiciv_icu.icustays ie` is left joined to `gcs_final gs` on
   `ie.stay_id = gs.stay_id AND gs.gcs_seq = 1`. This again preserves every
   ICU stay and attaches at most the selected GCS row.

The relational grain is one output row per `mimiciv_icu.icustays.stay_id`.
`stay_id` is the source natural/comparison key (the oracle manifest records
`key: ["stay_id"]`); `subject_id` is an identifying attribute and is not
unique because a subject may have multiple ICU stays. The FHIR comparator's
resource-key companions are metadata for the port, not source columns in this
SQL.

## Windows and aggregations

The target SQL has no `GROUP BY` and no value aggregate. It has one window:

```sql
ROW_NUMBER() OVER
(
    PARTITION BY g.stay_id
    ORDER BY g.gcs ASC NULLS LAST, g.charttime DESC NULLS LAST
) AS gcs_seq
```

Within each stay's time-windowed dependency rows, `gcs_seq = 1` selects the
lowest total GCS. Null totals sort after non-null totals. If totals tie, the
latest `charttime` wins. The selected row's motor, verbal, eyes, and unable
columns are taken as a coherent set from that same dependency row.

The upstream dependency operations that create the values consumed here are
also semantically relevant:

- `base` groups by `ce.subject_id, ce.stay_id, ce.charttime`.
- `base` uses `MAX(CASE...)` to pivot motor, verbal, eyes, and the ETT flag.
- Its `ROW_NUMBER()` partitions by stay and orders by ascending `charttime`.
- A self `LEFT JOIN` pairs each row with the immediately preceding row
  (`b.rn = b2.rn + 1`) when `b2.charttime` is within six hours before the
  current row.
- `gcs` uses `COALESCE` carry-forward/default logic and a `CASE` that sets the
  total to `15` when the current or previous verbal value is the ETT sentinel
  `0`; otherwise it sums current, previous, or normal defaults.
- `gcs_stg` coalesces component values with their previous values and emits
  `endotrachflag` as `gcs_unable`. There is no additional aggregate in the
  final dependency projection.

## Semantically essential inputs

These inputs can change target inclusion, keying, grouping, temporal selection,
or a clinically meaningful output:

- `icustays.stay_id`: natural key, join key, and dependency partition key.
- `icustays.subject_id`: output identity paired with the stay.
- `icustays.intime`: controls the inclusive dependency time window and thus
  whether a GCS row can enter the target at all.
- Dependency `gcs.stay_id`: associates a measurement with the ICU stay and
  controls the upstream grouping/carry-forward partition.
- Dependency `gcs.charttime`: controls the target window, the minimum-GCS
  tie-break, and the upstream temporal ordering/carry-forward.
- Dependency `gcs.gcs`: controls the `gcs_seq = 1` row choice and supplies
  `gcs_min`.
- Dependency `gcs.gcs_motor`, `gcs.gcs_verbal`, `gcs.gcs_eyes`, and
  `gcs.gcs_unable`: the selected row's clinically meaningful component and
  flag outputs.
- Upstream `chartevents.itemid`, `valuenum`, and `value`: `itemid` controls
  stream inclusion and pivot destination; `valuenum` controls component and
  total values; and the exact value discriminator controls the ETT special
  branch. Upstream `chartevents.stay_id` and `charttime` control grouping,
  carry-forward, and target timing. `chartevents.subject_id` is retained by
  `gcs` but is not read by this consumer.

### GCS No Response versus No Response-ETT

The authoritative `MIMIC_NOTES.md` records that for chartevents rows with
non-NULL `valuenum`, the upstream FHIR ETL writes `valueQuantity` and drops
source `value`. Consequently, source `No Response` and `No Response-ETT` can
both arrive as Quantity `1`; the resource id is opaque and cannot recover the
discarded label. This is directly material to this SQL, not an ancillary text
field:

- `No Response-ETT` takes the `gcsverbal = 0` branch and sets
  `endotrachflag = 1`.
- A non-ETT `No Response` row does not match that literal and takes the
  `ce.valuenum` branch, commonly producing verbal `1` and flag `0`.
- The distinction changes the dependency's `gcs`, `gcs_verbal`, and
  `gcs_unable`; through the target's minimum-GCS window selection it can also
  change `gcs_min` and which component row supplies `gcs_motor`/`gcs_eyes`.
- The target therefore depends on the exact discarded source discriminator
  even though it never directly reads `chartevents.value`.

This analysis records the loss and its propagation only. It does not decide
whether the eventual FHIR port is exact, divergent, or blocked.

## Evidence references

- `mimic-iv/concepts/firstday/first_day_gcs.sql:14-54` — target CTE, joins,
  time window, window ordering, and output.
- `mimic-iv/concepts/measurement/gcs.sql:24-127` — dependency columns,
  itemids, ETT value discriminator, pivot aggregates, and six-hour
  carry-forward.
- `mimic-iv/concept_dag/concept_dag.json:240-253,357-367,1144-1169` — node,
  dependency, and topological order.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md:241-275` — essential source-loss
  policy and the GCS No Response/No Response-ETT representability issue.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md:759-801` — itemid preservation and
  chartevents coding-system context.
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json:1597-1634` — output
  types and source comparison key.
- `mimic-iv/buildmimic/postgres/create.sql:369-383,414-425` — raw
  chartevents and icustays types.
