# Upstream bug — chartevents `value` text is discarded whenever `valuenum` is set

**Target:** `mimic-fhir` (MIMIC-on-FHIR ETL)
**File:** `sql/fhir_observation_chartevents.sql`
**Verified against:** local checkout at commit `4327224` (`main`)
**Status:** draft — confirm the counts in "Tests to run" before filing.

---

## Summary

`Observation.valueQuantity` and `Observation.valueString` are written from
mutually exclusive branches keyed on the same predicate, so a `chartevents` row
that has **both** a numeric `valuenum` and a semantically distinct `value` text
loses the text entirely. The resulting Observation is not merely lossy — it is
**ambiguous**: two source rows meaning different things collapse onto the same
served resource content.

The clearest instance is `itemid = 223900` (GCS - Verbal Response), where
`'No Response-ETT'` (patient is intubated, cannot speak) and `'No Response'`
(patient is unresponsive) both carry `valuenum = 1` and therefore both serialise
as `valueQuantity = 1`. The distinction is clinically significant and is used by
the official derived concept, and it cannot be recovered from the served
resource.

---

## The code

```sql
-- sql/fhir_observation_chartevents.sql:69-80
, 'valueQuantity',
    CASE WHEN ce_VALUENUM IS NOT NULL THEN
        jsonb_build_object(
            'value', ce_VALUENUM
            , 'unit', ce_VALUEUOM
            , 'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units'
            , 'code', ce_VALUEUOM
    ) ELSE NULL END
, 'valueString',
    CASE WHEN ce_VALUENUM IS NULL THEN
        ce_VALUE
    ELSE NULL END
```

`ce_VALUENUM IS NOT NULL` and `ce_VALUENUM IS NULL` partition the rows, so
exactly one of the two elements is ever populated. `ce.value` survives only when
there is no number — i.e. precisely when it carries no additional information
over the number.

## Why this is a bug rather than a modelling choice

The ETL **already treats `ce.value` as identity-bearing**. Twelve lines above the
branch that discards it:

```sql
-- sql/fhir_observation_chartevents.sql:20-21
-- chartevents uuid dependent on 'value' to be unique (stay_id and itemid should be enough but a couple cases break this)
, uuid_generate_v5(ns_observation_ce.uuid, ce.stay_id || '-' || ce.charttime || '-' || ce.itemid || '-' || ce.value) AS uuid_CHARTEVENTS
```

So `value` is significant enough that the resource **id** depends on it, and yet
it is not preserved anywhere in the resource body. Two rows that differ only in
`value` get two distinct Observations with byte-identical content. That is
self-inconsistent: the ETL asserts the field distinguishes rows and then declines
to serve it.

It also has an unpleasant second-order effect. Because the id is a UUIDv5 over
the source text, the discarded value is *technically* recoverable by
brute-forcing candidate strings against `Observation.id`. We know this because a
port in this repo did exactly that before we removed it. Nobody should be able to
recover a clinical value by inverting a hash of the primary key, and the fact
that it is possible is a good argument for serving the field properly.

---

## Concrete impact: the official `gcs` derived concept

`mimic-code`'s `mimic-iv/concepts/measurement/gcs.sql` depends on the exact text
in two places:

```sql
-- :33  verbal score
WHEN ce.itemid = 223900 AND ce.value = 'No Response-ETT' THEN 0
WHEN ce.itemid = 223900 THEN ce.valuenum
-- :45  intubation flag
WHEN ce.itemid = 223900 AND ce.value = 'No Response-ETT' THEN 1
```

Three of the concept's eight output columns depend on that sentinel:

| output | dependency |
|---|---|
| `gcs_unable` | entirely — it *is* the flag |
| `gcs_verbal` | ETT rows are scored `0` rather than `valuenum` (= 1) |
| `gcs` | a verbal of `0` forces the total score to the literal `15` |

and the effect propagates: the concept carries components forward across a
6-hour window (`COALESCE(gcsverbal, gcsverbalprev)`), so a misread ETT row also
corrupts subsequent rows in the same window.

Against MIMIC-on-FHIR, `gcs_unable` is therefore not derivable at all, and
`gcs_verbal` / `gcs` are wrong on every intubated observation.

### Measured so far

From a probe over the **demo** Delta warehouse plus the demo DuckDB source
(recorded in `mimic-iv/concepts_fhir/carryover/gcs/fhir-prober.md:99-113`).
These are our numbers, not upstream's — re-measure before filing:

| fact | count |
|---|---|
| `itemid=223900` rows | 3,266 |
| …with non-NULL `valuenum` | 3,266 / 3,266 |
| …with `value = 'No Response-ETT'`, all `valuenum = 1` | 1,348 |
| …with `value = 'No Response'`, also `valuenum = 1` | 78 |
| served Observations for `223900` with `valueQuantity` | 3,266 / 3,266 |
| served Observations for `223900` with `valueString` | **0 / 3,266** |
| served Observations carrying the ambiguous `valueQuantity = 1` | 1,426 |

So ~44% of verbal-response observations land on a value that means two different
things, and ~41% of them are intubated patients whose GCS the served data cannot
reproduce.

---

## Tests to run before filing

The demo numbers above establish the mechanism; these establish the scope. Run
against full MIMIC-IV 2.2 and the full served warehouse.

### 1. The general class — every ambiguous `(itemid, valuenum)` pair

This is the query that decides whether the report is "GCS is broken" or
"chartevents is lossy in general". Any pair where one number maps to more than
one label is an item whose meaning the FHIR layer cannot express.

```sql
SELECT ce.itemid,
       di.label,
       ce.valuenum,
       count(DISTINCT ce.value)   AS n_distinct_text,
       array_agg(DISTINCT ce.value) AS texts,
       count(*)                   AS n_rows
FROM mimiciv_icu.chartevents ce
JOIN mimiciv_icu.d_items di ON di.itemid = ce.itemid
WHERE ce.valuenum IS NOT NULL
GROUP BY ce.itemid, di.label, ce.valuenum
HAVING count(DISTINCT ce.value) > 1
ORDER BY n_rows DESC;
```

### 2. Rows whose text is not merely a rendering of the number

A weaker but broader signal: numeric rows whose `value` is not just the number
written out. These are the rows where the text plausibly carries meaning.

```sql
SELECT ce.itemid, di.label,
       count(*) AS n_rows,
       count(DISTINCT ce.value) AS n_distinct_text
FROM mimiciv_icu.chartevents ce
JOIN mimiciv_icu.d_items di ON di.itemid = ce.itemid
WHERE ce.valuenum IS NOT NULL
  AND ce.value IS NOT NULL
  AND ce.value !~ '^\s*-?[0-9]*\.?[0-9]+\s*$'
GROUP BY ce.itemid, di.label
ORDER BY n_rows DESC
LIMIT 100;
```

### 3. GCS specifically, on full data

```sql
SELECT value, valuenum, count(*) AS n
FROM mimiciv_icu.chartevents
WHERE itemid = 223900
GROUP BY value, valuenum
ORDER BY n DESC;
```

Expect `No Response-ETT` and `No Response` to share `valuenum = 1`. Confirm the
full-data proportions; the demo split (1,348 vs 78) may not be representative.

### 4. Served-side confirmation

Against the served warehouse, for `code.coding.code = '223900'` in system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, confirm
`valueString` is populated on **zero** rows and that `valueQuantity.value = 1`
covers the union of both labels. A ViewDefinition projecting both
`(value).ofType(Quantity).value` and `(value).ofType(string)` is enough.

### 5. Other concepts in the same class

These official concepts also match `chartevents.value` as text. For each, check
whether its itemids populate `valuenum`; if they do, the concept has the same
defect and the report gets stronger:

| concept | line | itemid(s) |
|---|---|---|
| `measurement/gcs.sql` | 33, 45 | `223900` — **confirmed affected** |
| `treatment/rrt.sql` | 100 | `225965` (Peritoneal Dialysis Catheter Status), `value = 'In use'` — **unverified, most likely candidate** |
| `treatment/crrt.sql` | 65-88 | `224146` etc. — believed unaffected (`valuenum` is NULL, so `valueString` is written; our `crrt` port reproduces it exactly) |
| `treatment/code_status.sql` | 21-31 | `223758` — believed unaffected, same reason |

`rrt` is the one to check: if `225965` carries a `valuenum`, then `'In use'` is
lost the same way and the bug reaches a second official concept.

---

## Suggested fixes

In rough order of preference.

**1. Write both.** Drop the `ELSE NULL` exclusivity and populate `valueString`
whenever `ce.value` is present, alongside `valueQuantity`. Simplest change, but
`Observation.value[x]` is a choice type — two variants cannot both be set on the
same element, so this is not actually legal FHIR. Noted only to be dismissed.

**2. `valueCodeableConcept` with `text`, for the affected items.** Where the
source text is a coded menu selection rather than free text, serve
`valueCodeableConcept` carrying `coding` (the item's value code, if one exists)
and `text` (the verbatim source string), and put the number in
`Observation.component` or drop it where it is derivative. Semantically the most
correct, most invasive.

**3. `Observation.component` for the source text.** Keep `valueQuantity` as the
primary value and add a component carrying the verbatim `ce.value` — e.g. a
component code of `sourceValue` in a MIMIC-proprietary system with
`valueString`. Least disruptive to existing consumers, fully additive, and it
directly restores what the derived concepts need. **This is the one I would
propose.**

**4. Minimum viable.** If a general fix is out of scope, at least special-case
the items where `(itemid, valuenum)` is provably ambiguous — the output of test
1 above is exactly that list. Narrower, but it fixes `gcs` and whatever else
test 1 turns up.

---

## What we are doing meanwhile

The `gcs` port is not published partially. The missing discriminator changes
`gcs_unable`, `gcs_verbal`, total `gcs`, and six-hour carry-forward semantics,
so the equivalence judge must block the entire concept after the new full-data
comparison confirms the gap. It remains blocked until upstream preserves the
source text. See `mimic-iv/concepts_fhir/TODO_reopen_uuid_inversion.md`.

Worth bundling into the same issue as the separate `TIMESTAMPTZ` DST-gap
finding (`fhir_observation_chartevents.sql:9`), since both are in this file and
both are "the served resource cannot express what the source row said".
