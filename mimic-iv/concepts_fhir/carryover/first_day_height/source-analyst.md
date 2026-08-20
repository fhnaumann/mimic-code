# Source analysis: `first_day_height`

## Source and DAG identity

- Concept stem: `first_day_height`.
- Canonical SQL: `mimic-iv/concepts/firstday/first_day_height.sql`.
- The SQL on disk was checked against the DAG-resolved node. Its SHA256 is
  `4ac0656fe4336995f39871093a445b2b46df86dda3d81ff791575bc4d3a98352`, which
  matches `mimic-iv/concept_dag/concept_dag.json`.
- DAG node: level `1`, dependency `height`, no listed dependents.
- Dependency node: stem `height`, path `measurement/height.sql`, level `0`, no
  dependencies. The DAG edge is `first_day_height -> height`.
- The SQL uses BigQuery-style project-qualified names. The logical MIMIC
  schemas are `mimiciv_icu` and `mimiciv_derived`.

The comment says that the query extracts heights for adult ICU patients and
uses the first ICU day, but the executable SQL has no adult-age predicate. Its
population is every row in `mimiciv_icu.icustays`, with the height aggregate
possibly NULL when the left-side stay has no matching height rows in the
specified window.

## Oracle manifest and natural grain

The `first_day_height` entry in
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` records:

- output columns and types: `subject_id INTEGER`, `stay_id INTEGER`, and
  `height DECIMAL(38,2)`;
- comparison mode: `keyed_join`;
- empirical natural key: `stay_id`;
- comparator key columns: `icu_encounter_key` and `patient_key`;
- `key_probes`: `2`;
- full-oracle row count: `73,181`;
- content hash: `672726114199549723280053`.

The relational grain is one grouped row per ICU stay, identified by
`(subject_id, stay_id)` in the SQL. The manifest establishes `stay_id` as the
unique comparison key in the full oracle. This is not one row per height
measurement: all qualifying height values for a stay in the interval are
averaged. The separate `icu_encounter_key` and `patient_key` manifest columns
are FHIR identity/join metadata; resource and reference IDs are opaque and are
not source-value witnesses.

## 1. Physical and derived table references

Every table reference in the target SQL is:

| SQL clause | Logical schema | Table | Alias | Role |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_icu.icustays\` ie` | `mimiciv_icu` | `icustays` | `ie` | Left-side ICU-stay spine, output identifiers, and admission time |
| `LEFT JOIN \`physionet-data.mimiciv_derived.height\` ht` | `mimiciv_derived` | `height` | `ht` | Previously derived height measurements consumed by the aggregate |

There are no `mimiciv_hosp` references and no other physical tables in
`first_day_height.sql`. The `mimiciv_derived.height` reference is an explicit
DAG dependency, not a request to rebuild `height` from FHIR resources or raw
`chartevents` in this concept. After dependency preprocessing, the candidate
consumer must see this dependency under its unqualified concept stem,
`height`.

The dependency's own canonical SQL,
`mimic-iv/concepts/measurement/height.sql`, reads
`mimiciv_icu.chartevents` twice (the `ht_in` and `ht_cm` CTEs), but that
`chartevents` reference belongs to the level-0 `height` concept and is not a
direct table reference of `first_day_height`.

## 2. Columns and types

`first_day_height.sql` has no CTEs. Its complete set of selected or referenced
columns is:

| Source/derived column | Inferred type | Use in this SQL |
|---|---|---|
| `ie.subject_id` | `INTEGER` | Final `subject_id` output and `GROUP BY` grouping key |
| `ie.stay_id` | `INTEGER` | Final `stay_id` output, equality join key, and `GROUP BY` grouping key |
| `ie.intime` | timestamp/datetime | Lower and upper time-window anchor for the join |
| `ht.stay_id` | `INTEGER` | Equality join key; it is not selected directly |
| `ht.charttime` | timestamp/datetime / `TIMESTAMP` | Inclusive time-window membership predicate; it is not selected directly |
| `ht.height` | numeric/decimal, dependency output in centimetres | Input to `AVG`; it is not selected directly before aggregation |
| `AVG(ht.height)` | numeric aggregate, nullable when there are no matched values | Per-stay aggregate before the explicit cast |
| `CAST(AVG(ht.height) AS NUMERIC)` | `NUMERIC` | Explicit numeric type for rounding |
| `ROUND(CAST(AVG(ht.height) AS NUMERIC), 2)` | `DECIMAL(38,2)` in the oracle manifest | Final `height` output |

The SQL writes `AVG(height)` without a qualifier; because `ie` has no height
column in this query, it resolves to `ht.height`. The dependency manifest for
`height` records its source output as `(subject_id INTEGER, stay_id INTEGER,
charttime TIMESTAMP, height DECIMAL(38,2))`. The target consumer reads exactly
these dependency columns and only these three: `ht.stay_id`, `ht.charttime`,
and `ht.height`. It does **not** read `height.subject_id`, `height_orig`, an
itemid, a unit, or a source text value.

Final output order and exact manifest types are:

1. `subject_id` — `INTEGER`, from `ie.subject_id`.
2. `stay_id` — `INTEGER`, from `ie.stay_id`.
3. `height` — `DECIMAL(38,2)`, the rounded average of matching dependency
   heights.

The height values supplied by the dependency are already converted to
centimetres, rounded per dependency row to two decimal places, and restricted
to the dependency's plausibility interval before this query averages them.

## 3. Filters and time predicates

There is no `WHERE` clause in `first_day_height.sql`. There are no direct
itemid, ICD, code-version, value, unit, adult-age, or explicit stay filters.

The `LEFT JOIN ... ON` clause contains the complete row-matching predicate:

```sql
ON ie.stay_id = ht.stay_id
    AND ht.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
    AND ht.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

The time window is inclusive at both ends. A dependency height row is included
for a stay only when its `stay_id` equals the ICU stay and its `charttime` is
between six hours before `ie.intime` and one day after `ie.intime`, inclusive.
The executable interval therefore spans a 30-hour wall-clock range around
intime, not merely the 24 hours after admission. A stay with no matching rows
is retained by the left join and receives a NULL aggregate height.

The upstream dependency `height` has its own filters. They are not re-applied
by `first_day_height`, but they define the exact rows and values available to
this consumer:

- in `ht_in`: `c.valuenum IS NOT NULL` and `c.itemid = 226707`;
- in `ht_cm`: `c.valuenum IS NOT NULL` and `c.itemid = 226730`;
- after the dependency's merge: `height IS NOT NULL`, `height > 120`, and
  `height < 230`.

The final bounds are strict. The source SQL contains no coded filter that is
identified as expected-absent/dead for `first_day_height`; no itemid is named
in the target SQL itself. The two dependency itemids are present-in-SQL code
specification and are not to be replaced by labels or inferred codes.

## 4. Joins

There is one target join:

```sql
FROM `physionet-data.mimiciv_icu.icustays` ie
LEFT JOIN `physionet-data.mimiciv_derived.height` ht
  ON ie.stay_id = ht.stay_id
 AND ht.charttime >= DATETIME_SUB(ie.intime, INTERVAL '6' HOUR)
 AND ht.charttime <= DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
```

- Type: `LEFT JOIN` / left outer join.
- Left input: every row of `mimiciv_icu.icustays`.
- Right input: the dependency output `mimiciv_derived.height`.
- Equality condition: `ie.stay_id = ht.stay_id`.
- Additional range conditions: inclusive lower and upper `ht.charttime`
  comparisons against `ie.intime`.
- There is deliberately no `subject_id` condition in the target join, even
  though the dependency output contains `subject_id`.
- A stay can match multiple `height` rows; those rows feed one grouped AVG.

For context, the dependency's own physical merge is a separate `FULL OUTER
JOIN` between its two CTEs on `subject_id` and `charttime` only. It does not
join on `stay_id`; the centimetre branch (`itemid = 226730`) has `COALESCE`
precedence over the inches branch (`itemid = 226707`). That upstream behavior
is part of the values delivered through the dependency and must not be
silently replaced with a target-level join on `stay_id`.

## 5. `mimiciv_derived` dependency and exact consumed columns

The sole derived dependency is:

```sql
mimiciv_derived.height
```

The target reads exactly:

- `height.stay_id` — join key;
- `height.charttime` — inclusive temporal filter;
- `height.height` — clinically meaningful numeric input to the AVG.

`height.subject_id` exists in the dependency's output but is not read by this
consumer. The implementer must consume the completed dependency under the
unqualified stem `height`; it must not inline the `height.sql` derivation,
rederive height from FHIR resources, or use resource IDs as a substitute for
any of these source fields.

## 6. Aggregation and row construction

The target has one aggregation:

```sql
GROUP BY ie.subject_id, ie.stay_id
```

and one value aggregate:

```sql
ROUND(CAST(AVG(height) AS NUMERIC), 2) AS height
```

There are no window functions, `MIN`, `MAX`, `SUM`, `ARRAY_AGG`, `DISTINCT`,
`HAVING`, or ordering clauses. `AVG` ignores NULL measurement values. Because
the dependency normally exposes only non-NULL, plausibility-filtered heights,
the aggregate is over the matched dependency rows; for a left-join miss it is
NULL. The final round occurs after averaging the dependency's already
two-decimal centimetre values.

## 7. Literal code set — verbatim

### Target SQL

`first_day_height.sql` names no coded literal. There is no `itemid`, `icd_code`,
ICD version, LOINC code, or other coded filter in the target query. Its only
literal filters are the interval quantities `INTERVAL '6' HOUR` and
`INTERVAL '1' DAY`, the latter being temporal bounds rather than a code set.

### Required dependency code specification

Because the target consumes the already derived `height` table, its upstream
code specification is recorded here without changing the target's own filter
inventory:

| Source table and column | Exact literal, verbatim | Predicate/branch | Feeds |
|---|---:|---|---|
| `mimiciv_icu.chartevents.itemid` | `226707` | `c.itemid = 226707` in CTE `ht_in` | `ht_in.height` after inches-to-centimetres conversion and `ht_in.height_orig`; then the inches input to `ht_stg0.height` and the dependency's final `height` |
| `mimiciv_icu.chartevents.itemid` | `226730` | `c.itemid = 226730` in CTE `ht_cm` | `ht_cm.height` after centimetre rounding; then the centimetre input to `ht_stg0.height` and the dependency's final `height` |

The dependency also applies, verbatim, `c.valuenum IS NOT NULL` in both source
branches, `height IS NOT NULL` after coalescing, and strict `height > 120 AND
height < 230` in its final output. No ICD code or alternate coding system is
named by either the target SQL or the dependency SQL. The source itemids are
not normalized, expanded, deduplicated, or substituted with labels.

## 8. Semantically essential inputs and their effects

### Direct target inputs

- `ie.stay_id`: determines the relational natural key, the equality join to
  dependency rows, the grouping partition, and the final `stay_id` output.
  Changing it can change which height rows are averaged and which output row
  receives the result.
- `ie.subject_id`: is a final output and a grouping column. It identifies the
  patient alongside the stay and can change grouped row identity if altered.
- `ie.intime`: supplies both inclusive window boundaries. It controls whether
  each `ht.charttime` is included and therefore controls the set of values
  contributing to the clinically meaningful average.
- `ht.stay_id`: controls whether a dependency measurement can join to the
  ICU-stay spine. It is essential even though it is not selected directly.
- `ht.charttime`: controls temporal row inclusion through both inclusive
  range predicates. It is not a final column, but its value can change the
  aggregate and whether a stay has a non-NULL result.
- `ht.height`: supplies the numeric measurement values to `AVG` and thereby
  controls the final rounded `height` output. NULL values do not contribute to
  `AVG`.

There is no temporal carry-forward, window partition, or order-dependent
selection in this target. Its temporal behavior is range inclusion followed by
an unordered per-stay average.

### Upstream dependency inputs that remain semantically essential

The target must consume the dependency output rather than rederive it, but the
following upstream fields/discriminators explain what those three consumed
columns mean:

- `chartevents.itemid`: exact `226707` versus `226730` selects the inches or
  centimetres branch and controls the conversion/rounding path that feeds
  dependency `height`.
- `chartevents.valuenum`: non-NULL status controls upstream row inclusion and
  its numeric value supplies the converted/rounded dependency height, which is
  later subject to the strict 120–230 cm bounds.
- `chartevents.subject_id` and `chartevents.charttime`: control the upstream
  full-outer merge key and which cm/inches rows are paired. The cm branch wins
  on a paired key. `subject_id` is not consumed by `first_day_height`, but the
  resulting paired dependency row can change the target's available values.
- `chartevents.stay_id`: is carried into dependency output and then controls
  the target stay join, even though it is not part of the dependency's own
  cm/inches merge key.
- `chartevents.charttime` as delivered by `height.charttime`: is subsequently
  tested against the target's `ie.intime` window, so any upstream time change
  can change target row inclusion and the final AVG.

## 9. Relevant notes and likely representability risks

I read `AGENTS.md`, the machine-readable and human-readable DAG entries, the
full oracle manifest entry, curated `MIMIC_NOTES.md`, and the requested
`MIMIC_NOTES.d` leads `height.md`, `weight_durations.md`, and
`icustay_times.md`. I also checked the reusable `height` source/prober
carryover, because it describes the level-0 dependency that this concept must
consume.

The following are risks or constraints for downstream probing and judging, not
clinical decisions and not terminal equivalence decisions:

1. **The derived dependency is essential and has a strict source shape.** The
   target cannot be implemented faithfully by using an arbitrary FHIR height
   resource or by recomputing a new height stream. It needs the completed
   `height` dependency's `stay_id`, `charttime`, and converted/filtered
   `height` columns. Replacing the dependency with an independently filtered
   stream risks changing cm precedence, strict bounds, or the source
   `subject_id + charttime` merge behavior.

2. **Exact itemid discrimination is required upstream.** The coding policy in
   `AGENTS.md` says that source codes are lifted verbatim. The dependency's
   exact itemids are `226707` and `226730` on
   `mimiciv_icu.chartevents.itemid`; no label or invented code is equivalent.
   The relevant height carryover identifies the ICU chartevents coding system
   as the exact system-plus-code discriminator and warns not to use
   `meta.profile`. This is an upstream dependency risk, not a new target
   filter.

3. **The target's time window is semantically essential.** It uses raw
   `icustays.intime` and raw derived `height.charttime` with inclusive bounds.
   Curated datetime notes document that the FHIR ETL can serialize
   spring-forward-gap wall times one hour later through a `TIMESTAMPTZ` cast,
   and the `height.md` lead reports this behavior for height Observations.
   The original wall time is not recoverable from the served effective time.
   In this concept, a shifted `charttime` can do more than change a displayed
   timestamp: if it crosses either `intime - 6 hours` or `intime + 1 day`, it
   can change membership in the AVG; it can also inherit any upstream change
   in the dependency's cm/inches pairing. No such boundary consequence is
   asserted here without a target run.

4. **ICU admission-time representation is another boundary risk.** The
   `weight_durations.md` lead reports DST normalization of ICU Encounter
   period endpoints derived from `icustays.intime`. If `ie.intime` is obtained
   through that FHIR representation, the window anchor itself may be shifted.
   The `icustay_times.md` lead specifically shows that aggregates over
   transformed chartevent timestamps can be non-commutative; this target uses
   `AVG` rather than `MIN`/`MAX`, so that lead is contextual rather than a
   direct claim about this query. Together these leads warrant checking both
   sides of the target range join, especially at DST-gap boundaries.

5. **Quantity and effective-choice materialization can lose native types.**
   The height dependency's reusable probe records that the served effective
   dateTime alias is string-like and that Quantity value aliases can also be
   string-like even when raw Quantity values are decimal. Downstream SQL must
   preserve wall-clock timestamp semantics and numeric conversion before
   applying the dependency's arithmetic; a type mismatch can otherwise alter
   the dependency output before this AVG is evaluated.

6. **Identifier recovery must use FHIR identifier values, not resource IDs.**
   `subject_id` and `stay_id` are semantically essential grouping/join/output
   values. The curated identifier notes say they come from the Patient and ICU
   Encounter identifier systems and need numeric casts. `patient_key`,
   `icu_encounter_key`, and observation/encounter reference keys may be used
   only for equality joins and identity. Per `AGENTS.md`, they must not be
   parsed, regenerated, compared with guessed source times, or used to recover
   `subject_id`, `stay_id`, `intime`, `charttime`, or height.

7. **Left-join null behavior is part of the shape.** A missing dependency
   measurement must not remove the ICU stay. It yields a retained stay row
   with a NULL `height`; turning the left join into an inner join changes row
   inclusion and is not a harmless representation choice.

No source-only finding establishes a new dataset-wide quirk, so no
`MIMIC_NOTES.d` fragment was modified. No ViewDefinition, candidate SQL,
attempt artifact, or git commit was authored.

## Summary

`first_day_height` is a level-1, one-row-per-ICU-stay aggregate over the
level-0 `height` dependency. It left-joins dependency heights by `stay_id`
within the inclusive interval `[ie.intime - 6 hours, ie.intime + 1 day]`,
averages all matching centimetre values, rounds the result to two decimals,
and emits `subject_id INTEGER`, `stay_id INTEGER`, and `height DECIMAL(38,2)`.
The target has no coded filter of its own; its exact upstream itemids are
`226707` and `226730`, and the main representability concern is preservation
of identifiers plus both sides of the FHIR-transformed time window without
using opaque resource IDs as semantic witnesses.
