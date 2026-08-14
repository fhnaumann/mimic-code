# FHIR prober mapping — `rhythm`

**Concept:** `measurement/rhythm`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/rhythm/source-analyst.md`  
**Canonical SQL:** `mimic-iv/concepts/measurement/rhythm.sql`  
**Authoritative demo warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB, read-only)  
**Probe engine:** embedded Pathling 9.6.0 / Spark 4.0.2. No live Pathling
server or stale NDJSON was used.

## Resource and stream mapping

The sole source table, `mimiciv_icu.chartevents`, maps to FHIR
`Observation`, specifically the chartevents coding stream. The source
`mimiciv_icu.icustays` table is not read by the canonical SQL; its FHIR
equivalent is needed only as the linked ICU `Encounter` spine for the source
`stay_id IS NOT NULL` inclusion predicate.

Use system plus exact code, never `meta.profile`:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
codes  = "220048", "224650", "224651", "226479", "226480"
```

The code system was observed directly on all 24,832 targeted coding rows.
The Delta warehouse has no served `CodeSystem` resource (`src.read('CodeSystem')`
raises `IllegalArgumentException: No data found for resource type: CodeSystem`),
so the served Observation codings, the source itemids, and the `d_items`
labels are the authority. `d_items.itemid` is a global key with one `linksto`
value per item; the exact itemid therefore separates this chartevents stream
from the other ICU streams. The other ICU systems are not substituted, and
`meta.profile` is not consulted.

The coding expansion must be constrained inside the `forEach`:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

There was exactly one coding per targeted Observation: 24,832 coding rows /
24,832 distinct resources = **1.000**, both overall and for every code. The
whole chartevents-system stream also measured 668,862 coding rows /
668,862 distinct resources = **1.000** in the same demo warehouse. The
constraint remains required because the ratio is a warehouse property, not a
FHIR guarantee.

## Canonical ViewDefinition projections

These are reusable projections, not an attempt ViewDefinition. Resource and
reference keys are opaque strings used only for equality joins, grouping, and
provenance. They must not be parsed, regenerated, guessed, or used to recover
a source timestamp or source value.

### Patient spine

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

### ICU Encounter spine

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter the materialized Encounter view with `stay_id_str IS NOT NULL`. Do not
use `Encounter.class` to select ICU encounters. Join the Observation's
`encounter_key` to this Encounter's `encounter_key`, and cast the resulting
FHIR `Identifier.value` string to `INTEGER` only in final SQL.

### Rhythm Observation

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(string)", "name": "value_string" },
    { "path": "issued", "name": "issued" }
  ]
}
```

Append the constrained coding group shown above. The `Period.start` and
`instant` columns are probe-only checks for this stream; the ETL writes
`effectiveDateTime`, not an effective Period or instant.

## Source-column to FHIRPath mapping

| Source column / role | Canonical mapping | FHIR type; observed/materialized type | Required use |
|---|---|---|---|
| `chartevents.subject_id` → `subject_id` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` joined to Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key is opaque `string` / `VARCHAR`; `Identifier.value` is FHIR `string` / `VARCHAR` | Equality-join `patient_key`; final `CAST(subject_id_str AS INTEGER)`. The reference key is never the numeric output. 24,832/24,832 Observation references and Patient identifier values resolved in the probe. |
| `chartevents.charttime` → `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`; Pathling materializes an offset-bearing ISO value as `VARCHAR` | `CAST(effective_datetime AS TIMESTAMP_NTZ)` for the source wall-clock timestamp. Do not use an offset-aware `TIMESTAMP` cast or `to_timestamp`; do not coalesce the unused `instant` alias. |
| `chartevents.stay_id` → inclusion only | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` joined to ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key is opaque `string` / `VARCHAR`; ICU `Identifier.value` is FHIR `string` / `VARCHAR` | Preserve the source `stay_id IS NOT NULL` inclusion by requiring a resolved ICU identifier. Do not group by or output `stay_id`; the canonical SQL groups only by `(subject_id, charttime)`. All 24,832 target references resolved to an ICU stay identifier in the demo. |
| `chartevents.itemid` → code discriminator | In constrained coding group `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code` `string` / `VARCHAR` | Filter exact string codes after requiring the chartevents system; do not filter on display or profile. The five codes are carried verbatim. |
| coding system | In constrained coding group `{ "path": "system", "name": "item_system" }` | FHIR `Coding.system` `uri` / `VARCHAR` | Require `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`. |
| `d_items.label` (not a source SQL input) | In constrained coding group `{ "path": "display", "name": "item_display" }` | FHIR `Coding.display` `string` / `VARCHAR` | Informational only. It matched each source item label in the demo; never use it as the discriminator. |
| `chartevents.value` → all five outputs | `{ "path": "(value).ofType(string)", "name": "value_string" }` | FHIR `Observation.valueString` `string` / `VARCHAR` | The five target streams are categorical: source `valuenum` was NULL for 24,832/24,832 selected rows, and FHIR `valueString` was populated for 24,832/24,832. Preserve raw text, including trailing spaces. |
| `chartevents.storetime` | `{ "path": "issued", "name": "issued" }` (probe-only; not referenced by canonical SQL) | FHIR `instant`; Pathling materializes it as native Spark `timestamp` | `rhythm` has no store-time ordering or output. The target probe found `issued` populated on 24,832/24,832 rows; do not substitute it for `charttime`. |
| resource identity (support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | opaque FHIR resource key `string` / `VARCHAR` | Equality/provenance only. Never use it to recover a pre-normalized `charttime`, `value`, or source identifier. |

The primary key and output name conventions above are intentionally different:
`observation_key`, `patient_key`, and `encounter_key` are UUID-like join
columns; `subject_id_str` and `stay_id_str` are digit strings from FHIR
identifiers and must be cast to the manifest's `INTEGER` type in final SQL.

## Confirmed code set and field counts

The source SQL names exactly these five itemids. No code is dead in the demo,
and no terminology translation or expansion is involved.

| Source itemid / exact FHIR code | Coding.system | display | Source rows / `value` non-NULL | FHIR coding rows / distinct resources | valueString non-NULL |
|---:|---|---|---:|---:|---:|
| `220048` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Heart Rhythm` | 12,460 / 12,460 | 12,460 / 12,460 | 12,460 |
| `224650` | same | `Ectopy Type 1` | 11,044 / 11,044 | 11,044 / 11,044 | 11,044 |
| `224651` | same | `Ectopy Frequency 1` | 1,247 / 1,247 | 1,247 / 1,247 | 1,247 |
| `226479` | same | `Ectopy Type 2` | 43 / 43 | 43 / 43 | 43 |
| `226480` | same | `Ectopy Frequency 2` | 38 / 38 | 38 / 38 | 38 |
| **Total** | one system | — | **24,832 / 24,832** | **24,832 / 24,832** | **24,832** |

The coding-per-resource ratio is therefore **1.000 overall and per code**.
The source `d_items` labels and FHIR `Coding.display` agreed for all five
codes. The served coding system, not the table name or IG advertisement, is
the system used by the mapping.

The value streams are string-only in the demo:

| Code | Distinct raw text values | Minimum/maximum text length | Source/FHIR value-frequency distribution |
|---:|---:|---:|---|
| 220048 | 16 | 7 / 35 | Exact frequency distribution, including trailing spaces, on all 12,460 rows |
| 224650 | 8 | 4 / 15 | Exact on all 11,044 rows |
| 224651 | 5 | 4 / 10 | Exact on all 1,247 rows |
| 226479 | 5 | 4 / 15 | Exact on all 43 rows |
| 226480 | 3 | 4 / 10 | Exact on all 38 rows |

The oracle comparison of `(subject_id, stay_id, itemid, value)` had exact
agreement **24,832/24,832**, ignoring effective-time transformation. In
particular, 2,411 `220048` source values have trailing spaces and those spaces
were retained by `valueString`; do not `TRIM` before replaying the source
`STRING_AGG`/`MAX` expressions.

## NULL omission, references, effective choices, and timestamps

The source target had no NULL `value`, `stay_id`, `subject_id`, `itemid`,
`charttime`, or `storetime` rows in the demo:

```text
target source rows                       24,832
source value IS NULL                          0
source valuenum IS NOT NULL                   0
source valueuom IS NOT NULL                   0
source stay_id IS NULL                        0
source charttime IS NULL                      0
source storetime IS NULL                      0
FHIR patient reference NULL                   0
FHIR ICU encounter reference NULL             0
FHIR effective.dateTime NULL                  0
FHIR effective Period.start non-NULL          0
FHIR effective instant non-NULL               0
FHIR valueString NULL                         0
FHIR issued NULL                              0
```

The global chartevents ETL has a `value IS NOT NULL` predicate and a
hard-coded duplicate exclusion. The selected demo target exercised neither:
the source NULL count was 0/24,832 and the hard-coded tuple
`(stay_id=34934165, charttime='2151-10-03 05:14:00')` had 0 target rows. The
full port must not invent a FHIR row for an omitted source row.

The source `charttime` values are de-identified wall-clock timestamps. The
served `effectiveDateTime` is an offset-bearing string, but the offset is not
a real clinical instant for this data. Direct `CAST(effective_datetime AS
TIMESTAMP_NTZ)` preserves the served wall clock independently of the Spark
session timezone. An offset-aware cast would shift values, and ordinary
`TIMESTAMP` handling can reintroduce timezone conversion.

`Observation.issued` is not the source temporal key. It is populated as a FHIR
instant from the ETL's `storetime` branch, while `rhythm` never reads
`storetime`, orders by it, or outputs it.

## Repeated rows and grouping implications

The FHIR ETL preserves repeated source observations until the resource-level
global omission predicates are applied; a ViewDefinition must not deduplicate
by patient/time/item before replaying the source aggregates. Demo counts were:

| Stream | Source rows | Source `(subject_id, charttime)` groups | repeated source groups / max rows | FHIR rows | FHIR groups after effective-time serialization | repeated FHIR groups / max rows |
|---|---:|---:|---:|---:|---:|---:|
| 220048 | 12,460 | 12,407 | 53 / 2 | 12,460 | 12,405 | 55 / 2 |
| 224650 | 11,044 | 11,044 | 0 / 1 | 11,044 | 11,042 | 2 / 2 |
| 224651 | 1,247 | 1,247 | 0 / 1 | 1,247 | 1,247 | 0 / 1 |
| 226479 | 43 | 43 | 0 / 1 | 43 | 43 | 0 / 1 |
| 226480 | 38 | 38 | 0 / 1 | 38 | 38 | 0 / 1 |

Across all five codes, the source had 12,439 patient/time groups, 11,046
multi-row groups, and maximum group size 6. The FHIR side had 12,437 groups,
11,044 multi-row groups, and maximum group size 6. No demo patient/time group
contained more than one distinct ICU stay, but that does not authorize adding
`stay_id` to the canonical grouping key.

The implementer must preserve the source grain `(subject_id, charttime)`:

```text
GROUP BY subject_id, CAST(effective_datetime AS TIMESTAMP_NTZ)
```

Do not group by `encounter_key`, `stay_id`, `item_code`, or Observation id.
Keep all item rows until the pivot. `heart_rhythm` is the distinct raw
`valueString` set for code 220048, sorted lexically and joined with `'; '`;
each ectopy field is the lexical `MAX` of its raw `valueString` rows. FHIR
resource row identity is not part of the source semantics.

## Oracle replay and timestamp findings

On the demo, a pandas replay of the source SQL over the FHIR projections
produced:

```text
source selected rows                         24,832
FHIR selected resources                     24,832
source output groups                         12,439
FHIR output groups                           12,437
matched output keys                          12,437
matched-key aggregate tuples                 12,437 / 12,437 exact
source-only output keys                              2
candidate-only output keys                           0
```

The two source-only output keys are the New York DST-gap rows:

```text
subject_id  stay_id   source charttime       served effectiveDateTime
10003400    32128372  2137-03-10 02:00       2137-03-10 03:00
10035631    30932571  2116-03-08 02:00       2116-03-08 03:00
```

Each key has both code 220048 and code 224650, so this is 4/24,832 selected
resource rows and 2/12,439 source output groups. The effective-time tuple
comparison had 24,828/24,832 exact rows and four source-only/four shifted
FHIR-side rows. The text-only comparison was 24,832/24,832 exact. In this
demo the shifted rows did not change any aggregate value on the 12,437 keys
that remained on both sides, but the normalized time can collide with a real
03:xx group and is not safe to invert.

No Observation id or resource key was read as a source-value channel in this
comparison. In particular, UUID reconstruction, candidate enumeration, and
hardcoded-id lookup are forbidden and are not part of this mapping.

## Gaps and essentiality

### `subject_id` and `stay_id`: absent on Observation, but exactly derivable

The numeric identifiers are not in the Observation reference key. They are
exactly derivable through equality joins to Patient/ICU Encounter resource
keys, then from their `Identifier.value` strings. This is absent-but-derivable,
not a representation gap, provided the linked resources and identifier systems
are present. The demo resolved both spines for all 24,832 target rows. If a
future warehouse lacks a reference or identifier, do not use patient/time
heuristics; retain a typed NULL or the row shape required by the later
implementation/judge.

### Original `charttime` at DST-gap rows: absent and not representable

The served `effectiveDateTime` carries the transformed wall clock. On the
measured demo population the loss reached 4/24,832 selected rows and 2/12,439
source groups. The pre-normalization `02:00` values are not present in another
FHIR element. Resource identity is opaque and cannot be parsed or regenerated
to recover them. A one-hour heuristic is also forbidden and would incorrectly
shift genuine 03:xx observations.

This loss is potentially essential: `charttime` is the natural key and output,
controls grouping, and determines which values feed `STRING_AGG` and `MAX`.
A collision can alter row inclusion and clinically meaningful aggregate
values. The measured demo aggregate values were unchanged on shared keys, but
that does not establish full-data exactness. The comparator and equivalence
judge must assess the full result; if the full loss changes grouping/output,
recommend whole-concept blocking rather than hiding it with an id side
channel.

### Source NULL-valued rows: absent and potentially essential, not exercised

The canonical SQL retains selected rows even when `chartevents.value` is NULL,
whereas the FHIR ETL omits them before Observation creation. The demo loss is
bounded at 0/24,832 target rows. If full data contains a selected NULL row,
the missing Observation can remove an otherwise existing `(subject_id,
charttime)` group or alter whether an aggregate is NULL. This is potentially
essential to row inclusion/grouping, but must be measured on full data. Do not
emit a fabricated NULL-valued resource.

The ETL's hard-coded duplicate predicate was also unexercised for the target
demo population (0 rows). Its effect, if a full target row matches, is the
same kind of absent-row gap and must be evaluated by the comparator/judge.

### Unused `storetime`: not a gap for `rhythm`

The source SQL does not select or use `storetime`, so the FHIR `issued`
element is ancillary. No ranking, temporal carry-forward, row inclusion, or
output derives from it. It must not replace `effectiveDateTime`.

## Notes and fragments consulted

Established `MIMIC_NOTES.md` entries that changed this mapping decision:

- **Delta tables are authoritative; raw NDJSON and the live server are not:**
  all resource counts and paths came from embedded Pathling over Delta.
- **MIMIC identifiers live in `Identifier.value` as strings and resource/reference
  ids are opaque:** required separate Patient/Encounter equality keys and final
  integer casts; prohibited id parsing or timestamp/value recovery.
- **Observation itemid codes are verbatim and filters use system plus exact
  code:** required the chartevents system and the five string itemids, without
  terminology translation.
- **Observation subtype profiles are warehouse-version dependent:** prohibited
  `meta.profile` as the stream discriminator.
- **Categorical chartevents values are `valueString`:** selected the string
  choice and retained raw text rather than a CodeableConcept or Quantity.
- **FHIR datetimes carry offsets and must be cast to `TIMESTAMP_NTZ`:** required
  wall-clock parsing and identified the measured DST-gap loss.
- **Encounter class does not identify ICU versus hospital/ED streams:**
  required the ICU identifier system for the stay inclusion/reference.
- **Essential source loss and opaque identity policy:** requires the DST and
  possible NULL-row losses to remain visible to the comparator/judge.

Relevant provisional fragments read as leads, then checked against this target:
`MIMIC_NOTES.d/README.md`, `crrt.md`, `oxygen_delivery.md`,
`icustay_times.md`, `gcs.md`, `icp.md`, `code_status.md`, `height.md`, and
`icustay_detail.md`. The repeated-row, `issued`, NULL-omission, DST, and
superseded UUID-recovery claims were independently checked where relevant;
the medication/lab and ICU-period claims were not substituted for this
Observation mapping. No provisional fragment was treated as established
without the rhythm probe.

No ViewDefinition, derived `concept.sql`, or attempt implementation artifact
was authored.
