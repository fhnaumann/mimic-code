# Source analysis: `icustay_times`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/demographics/icustay_times.sql`.
- The SQL contains one CTE (`t1`) and one final `SELECT`; there are no
  `mimiciv_derived` references.
- DAG node: `icustay_times`, path `demographics/icustay_times.sql`, level 0,
  SHA-256
  `a26457b40e30eb4d6dbd98809ab0a39044d014806554c3f2c065262d6cb14bcc`.
- DAG dependencies: none. The DAG lists `icustay_hourly` as the sole
  dependent; this concept must therefore be available before
  `icustay_hourly`.
- The full oracle manifest identifies a keyed comparison with natural key
  `stay_id`, five output columns, and 73,181 rows. The manifest types are
  `INTEGER` for `subject_id`, `hadm_id`, and `stay_id`, and `TIMESTAMP` for
  `intime_hr` and `outtime_hr`.

## Tables and references

Every physical table reference is in the following list. The SQL uses the
BigQuery-style project prefix `physionet-data`; its MIMIC schema/table identity
is as shown.

1. `FROM \`physionet-data.mimiciv_icu.chartevents\` ce`
   - Schema: `mimiciv_icu`.
   - Table: `chartevents`.
   - Used by CTE `t1`.
2. `FROM \`physionet-data.mimiciv_icu.icustays\` ie`
   - Schema: `mimiciv_icu`.
   - Table: `icustays`.
   - Used by the final query.
3. `LEFT JOIN t1`
   - `t1` is the CTE result, not a physical table and not a
     `mimiciv_derived` dependency.

The source DDL confirms the relevant physical column types: in
`mimiciv_icu.chartevents`, `stay_id` and `itemid` are `INTEGER` and
`charttime` is `TIMESTAMP`; in `mimiciv_icu.icustays`, `subject_id`, `hadm_id`,
and `stay_id` are `INTEGER`.

## CTE, columns, and transformations

### CTE `t1`

```sql
SELECT
    ce.stay_id,
    MIN(ce.charttime) AS intime_hr,
    MAX(ce.charttime) AS outtime_hr
FROM mimiciv_icu.chartevents ce
WHERE ce.itemid = 220045
GROUP BY ce.stay_id
```

Referenced columns and inferred types:

- `ce.stay_id`: source `INTEGER`; grouping key and CTE output `stay_id`
  (`INTEGER`).
- `ce.charttime`: source `TIMESTAMP`; input to `MIN` and `MAX`.
- `ce.itemid`: source `INTEGER`; used only by the item filter.
- `intime_hr`: `MIN(ce.charttime)`, therefore `TIMESTAMP`; earliest chart time
  for the filtered heart-rate stream within each `stay_id`.
- `outtime_hr`: `MAX(ce.charttime)`, therefore `TIMESTAMP`; latest chart time
  for the filtered heart-rate stream within each `stay_id`.

The only transformation in `t1` is aggregation of heart-rate chart timestamps:
one row per `stay_id` is produced. `MIN` and `MAX` do not use `valuenum`,
`value`, `valueuom`, or any other measurement field.

### Final output

The final query selects:

1. `ie.subject_id`: `mimiciv_icu.icustays.subject_id`, `INTEGER`.
2. `ie.hadm_id`: `mimiciv_icu.icustays.hadm_id`, `INTEGER`.
3. `ie.stay_id`: `mimiciv_icu.icustays.stay_id`, `INTEGER`; natural key.
4. `t1.intime_hr`: aggregated timestamp, `TIMESTAMP`; NULL when the stay has
   no matching filtered chartevents row.
5. `t1.outtime_hr`: aggregated timestamp, `TIMESTAMP`; NULL under the same
   condition.

There is no arithmetic, cast, date truncation, timezone operation, string
operation, CASE expression, or other value transformation. The SQL comments
describe fuzzy admission boundaries, but the executable query does not read
`admissions`, `intime`, or `outtime`; it derives only first/last heart-rate
`charttime` per ICU stay.

## Filters and literal code specification

There is exactly one `WHERE` predicate:

```sql
ce.itemid = 220045
```

Literal code set, verbatim:

- Source table: `mimiciv_icu.chartevents`.
- Coded column: `itemid`.
- Exact literal set: `220045`.
- Predicate: equality (`ce.itemid = 220045`).
- Meaning in this SQL's operation: the rows contributing to CTE `t1` and
  consequently to output columns `intime_hr` and `outtime_hr`.
- This is the complete code set; there are no ICD codes, code-version filters,
  exclusion lists, value constraints, or time-window predicates.

The SQL itself does not name a FHIR coding-system URI. Under the repository's
itemid policy, this is an ICU `chartevents` itemid stream; the shared curated
dataset note records the chart-event system as
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`. That
URI is not a literal in this canonical SQL and must not be substituted for the
numeric source code `220045`.

## Join

The final query has one join:

```sql
LEFT JOIN t1
  ON ie.stay_id = t1.stay_id
```

- Join type: `LEFT JOIN` (left outer join).
- Left input: all rows from `mimiciv_icu.icustays` (`ie`).
- Right input: the aggregated CTE `t1`.
- Join condition: equality of `ie.stay_id` and `t1.stay_id`.
- Effect: every ICU stay remains in the output; `intime_hr` and `outtime_hr`
  are NULL for stays without a filtered heart-rate chart row.
- No join uses `subject_id` or `hadm_id`, and there is no join to a dimension
  table or to any derived concept.

## Aggregations and key

- `GROUP BY ce.stay_id` in `t1`.
- Aggregate functions: `MIN(ce.charttime)` and `MAX(ce.charttime)`.
- No window functions, `DISTINCT`, `HAVING`, array aggregation, or final-query
  aggregation.
- The source output's natural key is `stay_id`, confirmed by the full oracle
  manifest. The CTE is also one row per `stay_id`; `icustays.stay_id` is the
  left-side ICU-stay identifier that preserves the final one-row-per-stay
  shape.

## Dependencies and downstream mapping implications

- `mimiciv_derived` dependency: none.
- Raw dependencies: `mimiciv_icu.chartevents` and
  `mimiciv_icu.icustays` only.
- The port must preserve all five output columns and their declared types.
- The heart-rate code filter must remain exactly `itemid = 220045` on the
  chartevents stream. No label-based or inferred replacement is specified by
  the source SQL.
- Because the final join is left outer, absence of a heart-rate Observation
  should produce the stay with typed NULL timestamp outputs rather than remove
  the stay.

## Dataset-wide quirk note for the orchestrator

No new dataset-wide quirk is established by this source-only analysis, so there
is nothing to append to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_times.md`
on the basis of these findings. The already-curated `MIMIC_NOTES.md` datetime
handling note (FHIR datetimes carry offsets and should be read as wall-clock
values with `TIMESTAMP_NTZ`) is relevant for a downstream FHIR mapping of
`charttime`, but it is existing shared knowledge rather than a new finding from
this analysis. The sibling `MIMIC_NOTES.d/icustay_detail.md` was read as
requested, but its provisional claims are not used as established evidence
here.
