# FHIR probe and mapping: `coagulation`

**Concept:** `measurement/coagulation`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/coagulation/source-analyst.md`  
**Probed:** 2026-08-10  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with
embedded Pathling 9.6.0 / Spark 4.0.2. No HTTP Pathling server or raw NDJSON
was used.  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB 1.5.5,
read-only.

## Target shape and resource mapping

The source table is `mimiciv_hosp.labevents`. Its FHIR stream is the
labevents-derived `Observation` resource. `Patient`, hospital-stream
`Encounter`, and `Specimen` are supporting resources for identifier joins:

| Source table/role | FHIR resource | Discriminator or join |
|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` plus exact string `code` |
| `labevents.subject_id` | `Patient` | `Observation.subject.getReferenceKey(Patient)` → `Patient.identifier` with the patient system |
| `labevents.hadm_id` | hospital `Encounter` | `Observation.encounter.getReferenceKey(Encounter)` → `Encounter.identifier` with the hospital system; always a `LEFT JOIN` |
| `labevents.specimen_id` | `Specimen` | `Observation.specimen.getReferenceKey(Specimen)` → `Specimen.identifier` with the lab-specimen system |

The full oracle manifest declares ten output columns, `keyed_join` comparison,
natural key `specimen_id`, and 1,543,003 full-data rows. The demo probe found
4,630 coded Observation rows for the six active itemids, 4,577 rows with a
numeric FHIR Quantity, and 1,630 unique specimen groups after the source
equivalent numeric filter. The DuckDB demo oracle also has 4,577 eligible rows
and 1,630 grouped rows. The candidate must preserve this output order and
shape:

```text
subject_id INTEGER
hadm_id INTEGER (nullable)
charttime TIMESTAMP
specimen_id INTEGER
d_dimer DOUBLE
fibrinogen DOUBLE
thrombin DOUBLE
inr DOUBLE
pt DOUBLE
ptt DOUBLE
```

`specimen_id` is the natural key. Do not group by patient/time or by an
Observation resource UUID. The source uses independent `MAX` aggregates, so
the FHIR-side pivot must use independent `MAX` values as well.

## Canonical ViewDefinition projections

The following paths use the canonical `{path, name}` format. Implementations
may use the `_key`/`_str` aliases from the identifier-spine convention to avoid
collisions between UUID join keys and final MIMIC identifiers; those aliases
have the same paths and types shown here.

### Observation

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "resource": "Observation",
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_id"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_id"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id"},
        {"path": "specimen.getReferenceKey(Specimen)", "name": "specimen_id"},
        {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
        {"path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
        {"path": "(effective).ofType(instant)", "name": "effective_instant"}
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')",
      "column": [
        {"path": "code", "name": "code"},
        {"path": "system", "name": "system"},
        {"path": "display", "name": "display"}
      ]
    }
  ]
}
```

FHIR types and observed materialized types for the relevant Observation
columns are:

| Source role | Canonical FHIRPath mapping (`{path, name}`) | FHIR type | Observed Pathling type / use |
|---|---|---|---|
| Observation resource key (support only) | `{ "path": "getResourceKey()", "name": "observation_id" }` | resource key string / UUID-like key | `STRING`; join/support only, not output |
| `subject_id` reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }` | `Reference(Patient)` | `STRING`; join to Patient, never emit as MIMIC `subject_id` |
| `hadm_id` reference | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }` | `Reference(Encounter)` | `STRING`; nullable join to hospital Encounter |
| `specimen_id` reference | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_id" }` | `Reference(Specimen)` | `STRING`; join to Specimen, never emit UUID |
| `itemid` | coding group `{ "path": "code", "name": "code" }` | `code` | `STRING`; filter exact text code |
| code system | coding group `{ "path": "system", "name": "system" }` | `uri` | `STRING`; exact discriminator |
| item label | coding group `{ "path": "display", "name": "display" }` | `string` | `STRING`; informational only |
| `valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal | `STRING` in a materialized ViewDefinition; cast to `DOUBLE` before pivot |
| comparator diagnostic | `{ "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" }` | `Quantity.comparator` code | `STRING`; 0/4,630 targeted rows in demo |
| `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` | `STRING` containing ISO-8601 offset; `CAST(... AS TIMESTAMP_NTZ)` |
| alternate effective | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` dateTime | `STRING`; 0/4,630, not populated for this target |
| alternate effective | `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | `instant` | `TIMESTAMP`; 0/4,630, not populated for this target |

The target observations all use `effective.ofType(dateTime)`. The alternate
projections were probed to check the choice type and are not needed in the
final concept view for this target. Use `TIMESTAMP_NTZ`, not an offset-aware
timestamp conversion: the FHIR offset is not a real instant for de-identified
MIMIC wall-clock times.

### Patient identifier spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "patient_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
  ]
}
```

`subject_id_str` is FHIR `Identifier.value` of type `string` and materializes
as `STRING`/`VARCHAR`. Join `Observation.patient_id` to the Patient resource
key, then cast `subject_id_str` to final `INTEGER`. The resource/reference key
is a UUID-like string and is never the output `subject_id`.

### Hospital Encounter identifier spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "encounter_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str"}
  ]
}
```

`hadm_id_str` is a FHIR `string`/materialized `STRING`. Join the Observation
encounter reference to this view and cast the identifier to nullable final
`INTEGER`. Filter the Encounter identifier system, not `Encounter.class`.
The Observation-to-Encounter join is a `LEFT JOIN`: among 4,577 eligible demo
Observation rows, 3,951 had an encounter reference and 626 did not. The source
also had 3,951 non-null `hadm_id` values. At grouped output level the
null-aware oracle agreement was 1,630/1,630, with 1,418 non-null `hadm_id`
groups.

### Specimen identifier spine

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "specimen_id"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", "name": "specimen_id_str"}
  ]
}
```

`specimen_id_str` is FHIR `Identifier.value` of type `string` and materializes
as `STRING`/`VARCHAR`. Join `Observation.specimen_id` to this Specimen resource
key, cast `specimen_id_str` to final `INTEGER`, and group on it. This is an
exact representation of relational `labevents.specimen_id`, not a heuristic.
All 4,577 eligible demo observations joined to a Specimen identifier and
produced 1,630 distinct identifiers.

## Exact code set and discriminator

The executable source filter contains exactly these six itemids. The
comment-only historical literals (`51149`, `52750`, `52072`, `52073`, `51280`,
`52893`, `51281`, `52161`) are not source filters and feed no output column.

| Source itemid / output | FHIR `code.coding.system` | Exact FHIR `code` | Delta coded rows / Quantity rows | DuckDB source rows / `valuenum IS NOT NULL` |
|---:|---|---:|---:|---:|
| `51196` → `d_dimer` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | `"51196"` | 1 / 1 | 1 / 1 |
| `51214` → `fibrinogen` | same | `"51214"` | 166 / 164 | 166 / 164 |
| `51297` → `thrombin` | same | `"51297"` | 1 / 1 | 1 / 1 |
| `51237` → `inr` | same | `"51237"` | 1,481 / 1,464 | 1,481 / 1,464 |
| `51274` → `pt` | same | `"51274"` | 1,481 / 1,464 | 1,481 / 1,464 |
| `51275` → `ptt` | same | `"51275"` | 1,500 / 1,483 | 1,500 / 1,483 |
| **total** | one system | — | **4,630 / 4,577** | **4,630 / 4,577** |

The Delta probe projected `code.coding` and found only the lab system for the
target set: 4,630 coding rows over 4,630 distinct Observation resource keys,
**1.000 coding per resource**. Per-code displays were `D-Dimer`, `Fibrinogen,
Functional`, `Thrombin`, `INR(PT)`, `PT`, and `PTT`, respectively. The exact
system plus exact string code is the subtype and item discriminator. Do not
cast an unfiltered Observation code to integer because other Observation
streams can carry LOINC strings. Do not use `meta.profile`: it is warehouse
variant-dependent. The lab system/code is sufficient because these are the
verbatim labevents itemids; no LOINC translation is available or required.

For source equivalence, filter the Quantity projection to the source numeric
branch. On the authoritative demo, `quantity_value IS NOT NULL` returned
exactly the 4,577 source rows and `quantity_comparator` was null for all of
them. The 53 remaining coded rows are source text/error rows and must not be
used as numeric values. The labevents ETL can synthesize a Quantity from
comparator text when source `valuenum` is null; therefore a full-data
implementation should also retain the `quantity_comparator` diagnostic and
exclude comparator-bearing synthesized values rather than using
`value.ofType(string)` as a numeric fallback. For this target's demo data the
equivalent condition is `quantity_value IS NOT NULL AND
quantity_comparator IS NULL`; there were no comparator-bearing rows to exclude
in the demo.

## Source item to FHIR numeric mapping

Each active itemid uses the same Quantity path and is pivoted into its named
output column:

| Source column/filter | Canonical FHIR mapping (`{path, name}`) | FHIR type / materialized type | Final target use |
|---|---|---|---|
| `itemid = 51196` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | cast/filter as text; `MAX` Quantity value → `d_dimer DOUBLE` |
| `itemid = 51214` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | `MAX` Quantity value → `fibrinogen DOUBLE` |
| `itemid = 51297` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | `MAX` Quantity value → `thrombin DOUBLE` |
| `itemid = 51237` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | `MAX` Quantity value → `inr DOUBLE` |
| `itemid = 51274` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | `MAX` Quantity value → `pt DOUBLE` |
| `itemid = 51275` | coding `{ "path": "code", "name": "code" }` under the lab-system `forEach` | `code` / `STRING` | `MAX` Quantity value → `ptt DOUBLE` |
| all six numeric values | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR decimal; materialized `STRING` | `CAST(quantity_value AS DOUBLE)` before conditional `MAX` |

The source `valuenum IS NOT NULL` predicate is not equivalent to merely
having an Observation or a `valueString`. Do not fall back to the 53 text rows.
No unit conversion, rounding, plausibility bound, or positivity filter is in
the source SQL.

## Aggregation, pivot, and candidate NULLs

After the exact lab-system/code filter and numeric-value filter, join the four
views by UUID/reference keys, keeping the Encounter join left-sided. Cast the
identifier strings and Quantity value only after extraction. Group by the
integer Specimen identifier and reproduce the source's independent aggregates:

```text
MAX(subject_id_str::INTEGER)                         -> subject_id
MAX(hadm_id_str::INTEGER)                            -> hadm_id
MAX(CAST(effective_datetime AS TIMESTAMP_NTZ))       -> charttime
MAX(CASE code='51196' THEN quantity_value END)       -> d_dimer
MAX(CASE code='51214' THEN quantity_value END)       -> fibrinogen
MAX(CASE code='51297' THEN quantity_value END)       -> thrombin
MAX(CASE code='51237' THEN quantity_value END)       -> inr
MAX(CASE code='51274' THEN quantity_value END)       -> pt
MAX(CASE code='51275' THEN quantity_value END)       -> ptt
```

The demo FHIR pivot had 1,630 rows. Its non-null counts were:

| Output column | Non-null / total | Candidate NULLs |
|---|---:|---:|
| `subject_id` | 1,630 / 1,630 | 0 |
| `hadm_id` | 1,418 / 1,630 | 212 |
| `charttime` | 1,630 / 1,630 | 0 |
| `specimen_id` | 1,630 / 1,630 | 0 |
| `d_dimer` | 1 / 1,630 | 1,629 |
| `fibrinogen` | 164 / 1,630 | 1,466 |
| `thrombin` | 1 / 1,630 | 1,629 |
| `inr` | 1,464 / 1,630 | 166 |
| `pt` | 1,464 / 1,630 | 166 |
| `ptt` | 1,483 / 1,630 | 147 |

The six nullable numeric outputs are required columns, not optional columns:
the SQL must preserve typed `DOUBLE` NULLs where a specimen has no numeric
Observation for that itemid. The 18 specimens present only among all coded
rows but absent after `valuenum IS NOT NULL` are correctly excluded, not
emitted as all-null candidate rows.

## Oracle checks

The following checks were run with a pandas comparison after projecting the
FHIR pivot and the DuckDB source query on `specimen_id`:

* FHIR eligible Observation rows: 4,577; source numeric rows: 4,577.
* FHIR grouped rows: 1,630; source grouped rows: 1,630.
* Key merge: 1,630/1,630 `both`, 0 `left_only`, 0 `right_only`.
* `subject_id`: 1,630/1,630 exact, including the independent MAX semantics.
* `hadm_id`: 1,630/1,630 exact, including NULLs.
* `d_dimer`, `fibrinogen`, `thrombin`, `inr`, `pt`, `ptt`: 1,630/1,630
  exact for every output column, including NULLs.
* `charttime`: 1,629/1,630 exact. The only difference was specimen
  `68982928`: oracle `2116-03-08 02:52:00`, served FHIR effective time
  `2116-03-08 03:52:00`. This is the established DST-gap rewrite in the ETL;
  `TIMESTAMP_NTZ` preserves the served wall-clock value but cannot recover the
  original 02:52.

## Gaps and representability

* **Representable and exact:** subject identifier, specimen identifier, all
  six numeric values, and the specimen grouping key. The demo checks above are
  exact.
* **Hospital admission identifier:** the path is present when the Observation
  has an Encounter reference. If that reference is absent, no FHIR element
  carries the relational `hadm_id`; patient-plus-time matching is an
  approximation and is not an exact inversion. For this target's demo, the
  left join was exact at 1,630/1,630 grouped rows, and all 626 eligible
  observations without an Encounter reference corresponded to source-null
  admission values. Do not replace the left join with an inner join or invent a
  heuristic admission ID.
* **Effective datetime:** present on all target observations, but not exactly
  representable for the DST-gap row above. This is a **not representable**
  transformation loss, not an absent field and not recoverable by another
  FHIRPath. The measured demo agreement is 1,629/1,630 grouped rows.
* **Source text/error rows:** 53 coded Observations have no Quantity and carry
  text instead. They are excluded because the source explicitly requires
  `valuenum IS NOT NULL`; text is not an approximation of the numeric source
  column.
* Source columns not selected by `coagulation.sql` (`value`, `valueuom`,
  `comments`, `storetime`, reference ranges, flags, `labevent_id`) need no
  output mapping. `labevent_id` is not the concept key; `specimen_id` is.

## Notes and fragments consulted

Curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md` entries that changed this
mapping were:

* Delta tables are authoritative over stale NDJSON;
* MIMIC itemids are verbatim Observation coding codes, with the
  `mimic-d-labitems` system and no LOINC translation;
* `d_labitems` has no LOINC field in MIMIC-IV 2.2;
* subtype `meta.profile` is not a safe discriminator, so system plus exact code
  is required;
* resource/reference keys are UUID-like strings while MIMIC identifiers live
  in string-valued `identifier.value` and must be cast to final integers;
* Quantity ViewDefinition value aliases materialize as strings and require a
  numeric cast;
* lab Observation specimens preserve `specimen_id` through the lab Specimen
  identifier;
* lab Encounter references are incomplete, requiring a left join and allowing
  a typed nullable `hadm_id`;
* FHIR date-times require `TIMESTAMP_NTZ`, and the DST-gap rewrite is
  intrinsically unrecoverable; and
* lab `valueString` may be a source text/comments fallback and must not be
  treated as `valuenum`.

I read `MIMIC_NOTES.d/README.md`, `MIMIC_NOTES.d/blood_differential.md`, and
`MIMIC_NOTES.d/cardiac_marker.md`. The blood-differential comparator warning
was independently checked against the labevents ETL SQL and this target's
Delta/oracle counts; the demo had no comparator-bearing target rows, so that
specific provisional full-data example was not reproduced. The cardiac-marker
system-before-cast warning was confirmed by using the constrained lab-system
`forEach` and exact string codes. No other fragments existed at probe time.

I appended the following dataset-wide lead to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/coagulation.md`: labevents comparator
text can synthesize `Observation.valueQuantity` values even when relational
`valuenum` is NULL, so a numeric source port must retain the Quantity comparator
diagnostic and not admit comparator-bearing synthesized values. It is verified
against `mimic-fhir/sql/fhir_observation_labevents.sql:27-47,123-136` and the
coagulation Delta probe (4,630 coded rows, 4,577 Quantity rows with zero
comparators, and 53 `valueString` rows versus 4,577 source `valuenum`
non-null rows); it remains a provisional fragment entry until human merge.
