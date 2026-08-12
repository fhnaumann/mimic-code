# FHIR prober carryover: `invasive_line`

## Probe provenance

- **Concept/source:** `invasive_line`, from
  `mimic-iv/concepts/treatment/invasive_line.sql`.
- **Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`.
  All FHIR observations below used embedded Pathling 9.6.0 on Spark 4.0.2;
  no HTTP Pathling server and no NDJSON snapshot was used.
- **Read-only oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, queried
  with DuckDB.
- **Canonical structural reference:**
  `/Users/nau025/Documents/master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- The immutable full oracle for this concept has 93,378 rows and output
  columns `(stay_id, line_type, line_site, starttime, endtime)` with types
  `(INTEGER, VARCHAR, VARCHAR, TIMESTAMP, TIMESTAMP)`. It has no natural key;
  the implementer must preserve duplicate tuple multiplicity and use the
  manifest's full-tuple multiset comparison.

## Resource mapping

| MIMIC source | FHIR resource/stream | Role and discriminator |
|---|---|---|
| `mimiciv_icu.procedureevents` | `Procedure`, ICU procedure stream | One Procedure per served `procedureevents` row. Select the source item set using `Procedure.code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items'` plus the exact string code. |
| `mimiciv_icu.d_items` | `Procedure.code.coding.display` | Dimension label only; it is not a separate served resource. The item code itself is `Procedure.code.coding.code`. |
| FHIR `Encounter`, ICU identifier stream | `Encounter` | Support join for `procedureevents.stay_id`; select `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`. |
| FHIR `Patient` | `Patient` | Support only through `Procedure.subject`; the canonical `invasive_line` output does not emit `subject_id`. |

`Observation` is **not** the resource for `procedureevents`. For reference,
the authoritative Delta's only populated Observation identifier systems were
`.../identifier/observation-labevents` (107,727 rows) and
`.../identifier/observation-micro-susc` (1,036 rows); neither is relevant to
this concept. The Procedure stream has no identifier array and must use its
resource key only as an internal row/support key.

The exact Encounter identifier systems in the warehouse are:

| Encounter identifier system | resources/identifier rows |
|---|---:|
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` | 222/222 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | 275/275 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | 140/140 |

The target Procedure references all 216/216 selected ICU Encounters. Do not
use `Encounter.class` to choose the stream; the identifier system is the
discriminator. `Identifier.value` is a FHIR string and must be cast to the
manifest's `INTEGER` only in the final SQL.

## Canonical ViewDefinition projections

These are mapping projections, not an attempt ViewDefinition. The UUID/key
aliases are join/support values and must not be emitted as MIMIC integer IDs.

### Procedure flat columns

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "procedure_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(performed).ofType(dateTime)", "name": "performed_datetime" },
    { "path": "(performed).ofType(Period).start", "name": "performed_period_start" },
    { "path": "(performed).ofType(Period).end", "name": "performed_period_end" },
    { "path": "(performed).ofType(instant)", "name": "performed_instant" },
    { "path": "(performed).ofType(date)", "name": "performed_date" }
  ]
}
```

The authoritative Delta contains 3,450 Procedure resources. Across all
Procedure resources, `performed_datetime` is populated on 1,982/3,450 and
the Period start/end variants on 1,468/3,450 each; `instant` and `date` are
0/3,450. The 24-code invasive-line target is entirely Period-valued:
`performed_period_start` and `performed_period_end` are each 216/216, while
`performed_datetime`, `performed_instant`, and `performed_date` are 0/216.
Project both dateTime and Period variants in a general Procedure view; the
exact item-code filter selects the Period branch for this concept.

### Patient support view

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

`Patient.identifier` uses the exact patient system above. It is a FHIR
`Identifier.value` string; the target Procedure subject reference resolved to
this identifier for 216/216 rows, although `subject_id` is not a final
invasive-line column.

### ICU Encounter support view

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

`stay_id_str` is a FHIR string and must become final `stay_id INTEGER` via
`CAST(stay_id_str AS INTEGER)`. `Procedure.encounter.getReferenceKey(Encounter)`
is the UUID join to `Encounter.getResourceKey()`; it is not the numeric stay
ID.

### Item code projection

Constrain the repeated coding inside the `forEach`:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

`Procedure.code.coding.code` is a string containing the source `itemid`
verbatim. `item_display` is a string and is populated for every selected
target row. Filter on exact `item_system + item_code`, not on display or
profile metadata. There are no served `CodeSystem` resources; code presence
was established from the Procedure codings themselves and the ETL.

### Body-site projection

Use `forEachOrNull` when preserving the source row grain, because 76 selected
rows have no body site:

```json
{
  "forEachOrNull": "bodySite.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-bodysite')",
  "column": [
    { "path": "code", "name": "site_code" },
    { "path": "system", "name": "site_system" },
    { "path": "display", "name": "site_display" }
  ]
}
```

The FHIR type of `site_code` is `code`, of `site_system` is `uri`, and of
`site_display` is `string`; all materialize as Spark strings. The source
`procedureevents.location` is carried as `bodySite.coding.code` after the
FHIR ETL's `TRIM(REGEXP_REPLACE(location, '\\s+', ' ', 'g'))`. The body-site
system is the exact proprietary URI above. In the target, 140/216 have one
site coding and 76/216 have none; all 216 have exactly one Procedure resource.
`site_display` is null on 140/140 body-site codings, so use `site_code`, not
display. A plain `forEach` would silently drop the 76 no-site procedures.

## Source-column to FHIRPath mapping

The table reports both the FHIR element type and the materialized/required
target type. A `VARCHAR`/`STRING` materialization is not a finished output:
the implementer must cast it to the manifest type in the outer SQL.

| Source column or output | Canonical FHIR mapping `{path, name}` | FHIR type | Served/materialized type | Final target/use |
|---|---|---|---|---|
| Procedure internal row identity | `{ "path": "getResourceKey()", "name": "procedure_key" }` | `Procedure.id` / resource key | `STRING` UUID-like key (`Procedure/<uuid>`) | Internal only; do not use as `stay_id` or as a natural output key. |
| `procedureevents.stay_id` → `stay_id` | Procedure `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`; ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` then `Identifier.value` string | Both UUID/string | `CAST(stay_id_str AS INTEGER)` → `INTEGER`; exact 216/216 demo join. |
| `procedureevents.itemid` (filter only) | Inside item coding group `{ "path": "code", "name": "item_code" }` | `Coding.code` | `STRING` | Compare exact decimal string in the exact `mimic-d-items` system; do not emit in the five-column source output. |
| `d_items.label` → source `line_type` input | Item coding `{ "path": "display", "name": "item_display" }` | `Coding.display` string | `STRING` | Apply the source SQL's exact CASE to `item_display`; final `line_type` is `VARCHAR`. Display agreed with DuckDB labels 216/216. |
| Item coding discriminator | Item coding `{ "path": "system", "name": "item_system" }` | `Coding.system` URI | `STRING` | Require exact `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`. |
| `procedureevents.location` → source `line_site` input | Body-site group `{ "path": "code", "name": "site_code" }` | `bodySite.coding.code` code | `STRING` | Apply the source SQL's exact eight location CASEs to `site_code`; final `line_site` is `VARCHAR`. FHIR code is ETL-trimmed first; see gap below. |
| Body-site coding system | Body-site group `{ "path": "system", "name": "site_system" }` | `Coding.system` URI | `STRING` | Require exact `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-bodysite`; not a source output. |
| Body-site display | Body-site group `{ "path": "display", "name": "site_display" }` | `Coding.display` string | `STRING`, always null when coding exists | Not usable for `line_site`; use `site_code`. |
| `procedureevents.starttime` → `starttime` | `{ "path": "(performed).ofType(Period).start", "name": "performed_period_start" }` | `Period.start` `dateTime` | Offset-bearing `STRING` | `CAST(performed_period_start AS TIMESTAMP_NTZ)` → `TIMESTAMP`; exact 216/216 in the demo. |
| `procedureevents.endtime` → `endtime` | `{ "path": "(performed).ofType(Period).end", "name": "performed_period_end" }` | `Period.end` `dateTime` | Offset-bearing `STRING` | `CAST(performed_period_end AS TIMESTAMP_NTZ)` → `TIMESTAMP`; exact 216/216 in the demo. |
| Alternate `performed[x]` branch | `{ "path": "(performed).ofType(dateTime)", "name": "performed_datetime" }` | `dateTime` | `STRING` | 0/216 for the filtered target; project it for a general Procedure probe/view. |
| `procedureevents.subject_id` (not source output) | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` plus Patient `subject_id_str` support path above | `Reference(Patient)` then `Identifier.value` string | UUID/string | 216/216 resolved; no final `subject_id` column is required by `invasive_line`. |

For datetimes, cast the FHIR string directly to `TIMESTAMP_NTZ`. Do not use
an offset-aware `TIMESTAMP` conversion: the offset is not an instant to be
converted for this de-identified wall-clock data.

## Confirmed code set, systems, labels, and cardinality

The source SQL names exactly these 24 itemids. Counts below are source
DuckDB rows and served Delta Procedure rows/resources for the exact
`mimic-d-items` system and code. A zero is an observed dead filter, not an
omitted code.

| itemid/code | d_items label | source rows | FHIR rows | coding/resources |
|---:|---|---:|---:|---:|
| 227719 | AVA | 1 | 1 | 1/1 |
| 225752 | Arterial Line | 82 | 82 | 82/82 |
| 224269 | CCO PAC | 4 | 4 | 4/4 |
| 224267 | Cordis/Introducer | 10 | 10 | 10/10 |
| 224270 | Dialysis Catheter | 8 | 8 | 8/8 |
| 224272 | IABP line | 1 | 1 | 1/1 |
| 226124 | ICP Catheter | 1 | 1 | 1/1 |
| 228169 | Impella Line | 0 | 0 | 0/0 |
| 225202 | Indwelling Port (PortaCath) | 3 | 3 | 3/3 |
| 228286 | Intraosseous Device | 2 | 2 | 2/2 |
| 225204 | Midline | 4 | 4 | 4/4 |
| 224263 | Multi Lumen | 45 | 45 | 45/45 |
| 224560 | PA Catheter | 8 | 8 | 8/8 |
| 224264 | PICC Line | 38 | 38 | 38/38 |
| 225203 | Pheresis Catheter | 1 | 1 | 1/1 |
| 224273 | Presep Catheter | 0 | 0 | 0/0 |
| 225789 | Sheath (Venous) | 3 | 3 | 3/3 |
| 225761 | Sheath Insertion | 0 | 0 | 0/0 |
| 228201 | Tandem Heart Inflow Line | 0 | 0 | 0/0 |
| 228202 | Tandem Heart Outflow Line | 0 | 0 | 0/0 |
| 224268 | Trauma line | 5 | 5 | 5/5 |
| 225199 | Triple Introducer | 0 | 0 | 0/0 |
| 225315 | Tunneled (Hickman) Line | 0 | 0 | 0/0 |
| 225205 | RIC | 0 | 0 | 0/0 |

The source and FHIR target each have 216 selected rows/resources and 93
distinct ICU stays. The exact item code plus system is the discriminator.
The complete Procedure code projection has 3,450 codings over 3,450 distinct
Procedure resources (ratio **1.0**). Its other systems are
`mimic-procedure-icd10` (321), `mimic-procedure-icd9` (401), and
`http://snomed.info/sct` (1,260), so system filtering is required; the
selected item codes were observed only under `mimic-d-items`.

The target item coding has one coding per resource: 216/216. There is no
Procedure identifier: `identifier` is populated on 0/3,450 Procedure
resources. The upstream ICU ETL derives the opaque Procedure UUID from
`stay_id-orderid-itemid`, but serializes neither `orderid` nor an identifier;
do not claim that `orderid` is recoverable as an output column.

## Labels, sites, duplicates, and oracle checks

- `Procedure.code.coding.display` agreed with the DuckDB `d_items.label` for
  every selected code row: **216/216**. The display strings are not the final
  `line_type` because the source CASE merges selected labels (for example,
  `Arterial Line` → `Arterial`, `PICC Line` → `PICC`, and `CCO PAC` →
  `Continuous Cardiac Output PA`). Reproduce the source CASE exactly and use
  the unmodified display for the `ELSE` branch.
- Target `bodySite.coding` was present exactly once on 140/216 resources and
  absent on 76/216. `site_display` was null on **140/140** present codings.
  Source `location` was non-null on 140/216 rows and null on 76/216. The
  FHIR ETL's trimmed location value matched the non-null source location
  multiset exactly: **140/140**.
- All 216 selected Procedure resources have one target item coding and one
  target resource row: **216 rows / 216 distinct resource keys**, maximum one
  target coding row per resource. Do not use `DISTINCT` or group by stay/time;
  the source query has no deduplication and the full manifest is unkeyed.
  The 216-row demo happens to have 216 distinct final five-column tuples, but
  that does not justify adding a key or deduplicating the full result.
- All selected Procedure subject and encounter references were populated:
  `patient_key` 216/216 and `encounter_key` 216/216. The ICU Encounter join
  supplied `stay_id_str` 216/216 and the Patient support join supplied
  `subject_id_str` 216/216.
- Both performed Period endpoints were populated 216/216. Direct
  `TIMESTAMP_NTZ` casts of start and end agreed with the DuckDB source values
  **216/216** for each endpoint. The combined basic multiset
  `(itemid, subject_id, stay_id, starttime, endtime)` was exact: **216/216**,
  with zero source-only or FHIR-only rows.
- Comparing the final source five-column tuple to the FHIR-representable
  tuple gives **212/216 exact**. Four rows differ only because the FHIR ETL
  trims a trailing space from source `location='Right Antecube '` while the
  source SQL's CASE does not match that whitespace-bearing literal and leaves
  it unchanged. The affected source stays are 35,044,342; 35,889,503;
  35,479,615; and 30,057,454. This is an intrinsic FHIR representation
  transformation, not a code, join, time, or row-cardinality error.

## Gaps and representability

| Source value/field | Classification | Finding and consequence |
|---|---|---|
| `procedureevents.stay_id` | Absent but derivable | Procedure has only a UUID Encounter reference; the ICU Encounter identifier value recovers the numeric stay ID exactly for 216/216 demo rows. |
| `procedureevents.itemid` as a final output | Present as a filter/support code, not source output | `Procedure.code.coding.code` is the exact itemid string and can be filtered/cast, but the canonical SQL intentionally drops itemid/line_number. Do not add an output column. |
| `d_items.label` / `line_type` | Absent as normalized field but derivable | `Coding.display` carries the exact d_items label 216/216; the source CASE reproduces `line_type` exactly. |
| `procedureevents.location` / `line_site` | Partly transformed; four exact source values not recoverable | FHIR bodySite code carries the ETL-trimmed location. The four selected `Right Antecube ` rows lose their trailing space; no FHIR element preserves the original whitespace. The best faithful port uses the FHIR code and documents the 4-row intrinsic conflict rather than manufacturing the space. |
| Null `procedureevents.location` | Absent but derivable as null | No `bodySite` coding is emitted; `forEachOrNull` preserves the Procedure row and gives a null site. Exact target count is 76/216. |
| `procedureevents.orderid` / raw row identity | Not representable as a source output | It contributes to the opaque Procedure UUID in the upstream ETL, but no Procedure identifier or orderid element is serialized. The canonical source output does not request it; preserve resource rows without inventing a key. |
| Source rows with no served Procedure | Not representable if ETL omitted | No omission was observed for the 216 selected demo rows (source and FHIR both 216). A missing FHIR resource cannot be reconstructed by a ViewDefinition; retain the source code specification and report any full-data coverage gap. |

## Notes and fragments used

Curated `MIMIC_NOTES.md` decisions that changed this mapping were:

- Delta tables, not stale NDJSON or the HTTP server, are authoritative;
- MIMIC numeric IDs are string `identifier.value` values, while resource and
  reference keys are UUIDs;
- Encounter streams are selected by exact identifier system and not by
  `Encounter.class`;
- item-derived coded values are verbatim and must be filtered by exact system
  plus exact source code, with no terminology translation;
- polymorphic fields require separate `.ofType()` projections; and
- offset-bearing FHIR datetimes must be cast to `TIMESTAMP_NTZ`, not converted
  as instants.

Relevant provisional fragments read were `MIMIC_NOTES.d/README.md`,
`crrt.md`, `icp.md`, `gcs.md`, `code_status.md`, and `icustay_detail.md`.
The chartevents omission/DST leads in `crrt.md`, `icp.md`, `gcs.md`, and
`code_status.md` were not adopted as Procedure facts; the ICU identifier
system lead in `icustay_detail.md` was independently verified against the
current Encounter Delta counts. No earlier Procedure-specific fragment
existed to verify.

No ViewDefinition, attempt SQL, or attempt artifact was authored. This file
is the reusable FHIR-prober carryover.
