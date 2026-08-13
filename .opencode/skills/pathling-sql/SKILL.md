---
name: pathling-sql
description: How a FHIR ViewDefinition and the concept.sql that selects from it are structured and authored for embedded Pathling on Spark, including the label-is-the-table-name invariant and the Spark SQL dialect notes the MIMIC-on-FHIR warehouse requires. Trigger phrases include "register ViewDefinition", "pathling SQL", "concept.sql", "ViewDefinition label", "Spark SQL dialect".
---

# pathling-sql

How ViewDefinitions and their `concept.sql` are structured and authored for the
concept-port loop.

Pair this with `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, which records the
data-side quirks the SQL has to absorb — most notably that FHIR datetimes are
ISO-8601 strings Spark's default parser rejects, so every time computation needs
an explicit format string. New dataset-wide findings are appended to this
concept's own `mimic-iv/concepts_fhir/MIMIC_NOTES.d/<concept>.md`, never to
`MIMIC_NOTES.md`, which is read-only while a loop is running.

## One engine: embedded Pathling on Spark

Both legs — `mimic_utils run-demo` locally and `run-full` on the HPC — run
**embedded Pathling on Spark** over a Delta warehouse. There is no FHIR server
anywhere in the loop, no HTTP provisioning flow, and no `$sqlquery-run`. The
full leg has no choice (compute nodes have no FHIR server), and a second local
path would only mean the Spark leg's first real execution happened on the HPC.

If you find a document describing `PUT ViewDefinition` + a `sql-view` Library +
`$sqlquery-run`, or a `--engine server` flag, it is stale. The server was
removed rather than demoted: it served different data from the Delta warehouse,
so a disagreement between it and Spark could never tell "Spark bug" apart from
"different dataset".

**The invariant that matters is the label.** The ViewDefinition's filename label
*is* the SQL table name, bound through `createOrReplaceTempView(label)`, and it
must equal the ViewDefinition's own `name` — the runner rejects the attempt
otherwise. Get it wrong and `concept.sql` selects from a table that was never
registered.

## Attempt artifacts

An attempt directory holds exactly two hand-authored things:

```
ViewDefinition.<label>.json    one or more; <label> is the SQL table name
concept.sql                    Spark SQL selecting from those labels
```

The ViewDefinition JSON uses the `select[].column[].{path, name}` format with
optional `forEach`/`forEachOrNull` — see the `fhir-mapping` skill for the exact
structure, and
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`
for a canonical example.

The runner writes `candidate.demo.parquet` from the resulting Spark DataFrame.
Parquet, not text, because Parquet carries the Spark schema: a column emitted as
`CAST(NULL AS SMALLINT)` reaches the shape gate as `SMALLINT`, where through
NDJSON it would infer as `JSON` and fail. This means a type mismatch reported by
the gate is a real one — write your `CAST`s to match the manifest's types
deliberately rather than assuming a serialisation artifact will be forgiven.

## Cast every output column from the manifest

A ViewDefinition hands SQL almost everything as a Spark **STRING** — identifiers,
dates, numbers alike. The manifest
(`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`, per concept, under
`columns`) declares what each output column must be. Those two facts do not meet
by themselves.

**Read the manifest entry before writing the final `SELECT`, and give every
column in it an explicit `CAST` to its declared type.** Not the ones that look
risky — every one. This costs a line each and removes the entire class of
shape-gate failure:

```sql
SELECT
    CAST(p.subject_id_str AS INTEGER)                 AS subject_id,   -- manifest: INTEGER
    CAST(e.hadm_id_str    AS INTEGER)                 AS hadm_id,      -- manifest: INTEGER
    CAST(e.period_start   AS TIMESTAMP_NTZ)           AS admittime,    -- manifest: TIMESTAMP
    CAST(NULL             AS SMALLINT)                AS anchor_age,   -- manifest: SMALLINT
    CAST(v.value          AS DOUBLE)                  AS valuenum      -- manifest: DOUBLE
FROM ...
```

The gate allows numeric widening (`INTEGER` where the manifest says `BIGINT` is
fine) and date/datetime interchange. It does **not** forgive string-vs-number:
`VARCHAR` against a declared `INTEGER` is a `shape_fail`, and it is the single
most common one. If a column reaches the gate as `VARCHAR` and the manifest says
otherwise, the cast is missing — that diagnosis needs no probing.

Identifier columns have a second failure mode stacked on the cast: `subject_id`,
`hadm_id`, `stay_id` must come from `identifier.value`, not `getResourceKey()`,
or the cast is applied to a UUID. See "Identifier spine" in the `fhir-mapping`
skill and the identifier entry in `MIMIC_NOTES.md`.

### Datetimes: `CAST(… AS TIMESTAMP_NTZ)`, and nothing wrapped around it

For a datetime column that cast is not merely the recommended form — it is the
whole mapping. Do **not** add a parser, a fallback, or a fixed format string
next to it. The two constructions below keep appearing in ports and both are
defects, not defensive coding:

```sql
-- WRONG: the fallback re-renders the instant in spark.sql.session.timeZone.
COALESCE(
    TRY_CAST(effective_text AS TIMESTAMP_NTZ),
    CAST(TRY_TO_TIMESTAMP(effective_text, "yyyy-MM-dd'T'HH:mm:ssXXX") AS TIMESTAMP_NTZ)
)

-- WRONG: a pinned format silently yields NULL on every shape it does not match.
CAST(
    TRY_TO_TIMESTAMP(
        REGEXP_REPLACE(starttime_str, '(Z|[+-][0-9]{2}:[0-9]{2})$', ''),
        "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
    ) AS TIMESTAMP_NTZ
)

-- RIGHT.
TRY_CAST(effective_text AS TIMESTAMP_NTZ)
```

Why each is worse than the bare cast:

- **The offset-aware parser scored 0/275** against the oracle at session zones
  `Australia/Sydney` and `UTC`, and 275/275 only at `America/New_York`. Demo runs
  on a laptop and the full leg runs on Petrichor, so a fallback that fires on
  either engine makes one concept produce two answers. A branch that is dead
  whenever `TRY_CAST` succeeds is *live* exactly when it is least observable.
- **A pinned format returns NULL** on any shape it does not match — date-only
  values, unexpected fractional-second widths — and `TRY_` converts that into
  silence rather than a crash. Those NULLs then land in `differing_null_only`,
  which is `gap_shaped`: the port's own parse failure arrives at the judge
  disguised as a FHIR coverage gap, at the *lower* evidentiary bar. This is the
  worst failure mode in the loop, because it is the one that gets accepted.
- The bare cast already handles every shape the IG emits, fractional seconds
  and date-only included. There is nothing left for a fallback to catch.

Use `TRY_CAST` when a malformed value should become NULL instead of failing the
run, and plain `CAST` otherwise. Full derivation, the measured comparison table
and the DST-gap consequence: `MIMIC_NOTES.md`, "FHIR datetimes carry an offset".

## SQL authoring patterns

### Polymorphic field coalescing

When a ViewDefinition extracts multiple variants of a polymorphic field,
the derived SQL must COALESCE them:

```sql
SELECT
    encounter_id,
    COALESCE(effective_datetime, effective_period_start) AS charttime,
    value AS valuenum,
    unit AS valueuom
FROM v_concept
```

### JOIN patterns

Concepts that reference multiple FHIR resources require JOINs:

```sql
SELECT o.patient_id, o.encounter_id, e.period_start
FROM v_observation_concept o
LEFT JOIN v_encounter_concept e ON o.encounter_id = e.encounter_id
```

### ICU stay filtering

Join against the ICU-stay Encounter view:

```sql
SELECT v.*
FROM v_vitalsign v
INNER JOIN v_icustay_detail d ON v.encounter_id = d.encounter_id
```

### Itemid / code filtering

```sql
WHERE system = '<source coding system>'
  AND code IN ('220045', '220050', '220052')
```

### Value constraints

```sql
WHERE
    value IS NOT NULL
    AND CAST(value AS DOUBLE) > 0
    AND TRY_TO_TIMESTAMP(effective_datetime) IS NOT NULL
```

### Spark SQL dialect notes

- `TRY_TO_TIMESTAMP(col)` for nullable FHIR datetime parsing (from
  `MIMIC_NOTES.md` — safer than `to_timestamp`, which throws on null/malformed).
- `CAST(value AS DOUBLE)` for FHIR Quantity values.
- `DATE_TRUNC('DAY', ts)` for day-level bucketing.
- Pass the **explicit format** either way —
  `TRY_TO_TIMESTAMP(col, "yyyy-MM-dd'T'HH:mm:ssXXX")`. The offset-bearing
  ISO-8601 strings this warehouse serves do not parse under the default.
- Check `mimic-iv/concepts_fhir/MIMIC_NOTES.md` and the `MIMIC_NOTES.d/`
  fragments for dataset-specific quirks (datetime parsing, code system
  flatness, etc.); append new ones to your own fragment. Fragments are other
  loops' unconfirmed hypotheses — verify before relying on one.

## Output requirements

`concept.sql` must be self-contained: it selects only from the registered
ViewDefinition labels, and must produce the column **names and types** the
oracle manifest declares for the concept. Row count is deliberately not part of
this — MIMIC-on-FHIR does not carry everything relational MIMIC-IV carries, so a
faithful port can legitimately return fewer rows, and neither gate treats a
count difference as a failure on its own.

Where the manifest declares a column MIMIC-on-FHIR cannot populate, emit it
explicitly as `CAST(NULL AS <type>)` rather than omitting it. The shape is part
of the contract, and Parquet carries the declared type through to the gate. If
the column is not merely unpopulated but genuinely *unrepresentable*, declare it
in the attempt's `unrepresentable.json` — the full comparator verifies every
declared column really is 100% NULL, and a declared column holding values is a
blocking failure.

That column-level mechanism does not make essential source loss acceptable. If
an absent source field can change row inclusion, keys, grouping, temporal
carry-forward, or a clinically meaningful derived output, do not manufacture a
best-effort table. Preserve the literal non-inverting mapping needed for the
full comparison and flag the essential loss for the judge, which alone decides
whether the entire concept is `BLOCKED_REPRESENTATION`.

## Warehouse configuration

The Delta warehouse path comes from `MIMIC_FHIR_WAREHOUSE`, or `--warehouse`.
The demo runner falls back to a laptop default; the full runner deliberately has
none, so demo data can never decide a correctness verdict.
