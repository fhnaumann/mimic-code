# FHIR prober mapping: `icustay_times`

**Probe date:** 2026-08-12  
**Authoritative Delta:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (read-only)  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/icustay_times/source-analyst.md`  
**Manifest:** 73,181 rows, keyed by `stay_id`; `subject_id`, `hadm_id`, and
`stay_id` are `INTEGER`, `intime_hr` and `outtime_hr` are `TIMESTAMP`.

## Resource mapping

| MIMIC-IV source | FHIR resource/stream | Selection and role |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter`, ICU identifier stream | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`; 140/140 demo ICU Encounters, one ICU identifier per resource |
| `mimiciv_icu.chartevents` | `Observation`, chartevents stream | `code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` and exact `code = '220045'`; 13,913 target demo Observations |
| MIMIC subject spine | `Patient` | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/patient'`; 100/100 demo Patients |
| MIMIC hospital-admission spine for `hadm_id` | `Encounter`, hospital identifier stream | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'`; 275/275 demo hospital Encounters. ICU `partOf` resolves to this stream 140/140. |

The unfiltered Delta `Encounter` table contains 637 resources: 222 ED, 275
hospital, and 140 ICU. `Encounter.class` is not a discriminator; use the exact
identifier system. The ICU Encounter is the identifier spine for `stay_id`, and
its `partOf` reference is the exact UUID join to the hospital Encounter for
`hadm_id`. Do not use `getResourceKey()` or `getReferenceKey()` as numeric MIMIC
IDs: those are UUID join keys.

## Confirmed code set and coding cardinality

The source literal is exactly `itemid = 220045`. The served Delta carries it as
the string code below:

| source itemid | FHIR `Coding.code` | FHIR `Coding.system` | display | coding rows | distinct resources | ratio |
|---:|---|---|---|---:|---:|---:|
| 220045 | `"220045"` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Heart Rate` | 13,913 | 13,913 | 1.000 |

The authoritative Delta probe found no alternate system for code `220045` and
no dead lifted code. The complete chartevents system had 668,862 coding rows on
668,862 distinct Observation resources (1.000); the target query was 13,913 /
13,913 (1.000). A constrained coding `forEach` is still required so a future
second coding cannot fan out the result.

The discriminator is **`system` plus exact string `code`**, never
`meta.profile`. `d_items.itemid` is a global primary key with one `linksto`
value per item, so the exact code separates this chartevents stream from the
other ICU item streams; profile metadata is not a safe discriminator in merged
warehouse variants. The Delta contains no served `CodeSystem` resource; code
presence was established from the Observation codings and the ETL, not a
terminology lookup.

Canonical coding group:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code='220045')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

Comparing against an unfiltered `code.coding` projection gives the same result
in this warehouse because the measured ratio is 1.000, but retain the
constraint in the ViewDefinition.

## Canonical ViewDefinition projections

These are mapping projections only, not an attempt ViewDefinition. The
`*_key` aliases are UUID/reference strings for joins. The `*_str` aliases are
FHIR `Identifier.value` strings and must remain string-like in the view before
the final SQL casts them to the manifest's integer types.

### Patient

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

### ICU Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "period_start" },
    { "path": "period.end", "name": "period_end" }
  ]
}
```

Filter/use the ICU Encounter view with `stay_id_str IS NOT NULL` (or constrain
the identifier system in the FHIRPath). `parent_encounter_key` joins to the
hospital Encounter's `encounter_key`; the hospital view needs:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
  ]
}
```

### Chart Observation

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" }
  ]
}
```

Add the constrained coding group shown above. The source only needs the
dateTime choice: on the 220045 target, `effective_datetime` was populated
13,913/13,913; `effective_period_start` 0/13,913; `effective_instant`
0/13,913. It is useful to project the unused variants during probing to make
choice behavior explicit, but the implementer can use the confirmed dateTime
variant alone. Pathling materialized the aliases as:

| alias | FHIR type | materialized Spark type | total/non-null |
|---|---|---|---:|
| `observation_key` | resource key | `STRING` | 13,913 / 13,913 |
| `patient_key` | `Reference(Patient)` key | `STRING` | 13,913 / 13,913 |
| `encounter_key` | `Reference(Encounter)` key | `STRING` | 13,913 / 13,913 |
| `effective_datetime` | `dateTime` | `STRING` | 13,913 / 13,913 |
| `effective_period_start` | `Period.start` | `STRING` | 0 / 13,913 |
| `effective_instant` | `instant` | `TIMESTAMP` | 0 / 13,913 |
| `item_code` | `Coding.code` | `STRING` | 13,913 / 13,913 |
| `item_system` | `Coding.system` | `STRING` | 13,913 / 13,913 |
| `item_display` | `Coding.display` | `STRING` | 13,913 / 13,913 |
| `(value).ofType(Quantity).value` | `Quantity.value` | `STRING` alias; raw field `DECIMAL(32,6)` | 13,913 / 13,913 |

`valueQuantity` was populated 13,913/13,913 for the target; the source
`valuenum` and `value` were non-null in all 13,913 demo target rows. The value
is not needed by the source aggregation, but it is an identity witness for
the two DST-normalized rows described below.

## Source-column to FHIRPath mapping

| Source column / output | Canonical mapping `{path, name}` | FHIR type / served type | Required final output and use |
|---|---|---|---|
| `icustays.subject_id` → `subject_id` | ICU `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key `STRING`; `Identifier.value` `string` / `STRING` | join on UUID key, then `CAST(subject_id_str AS INTEGER)` → manifest `subject_id INTEGER` |
| `icustays.hadm_id` → `hadm_id` | ICU `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }`; hospital `{ "path": "getResourceKey()", "name": "encounter_key" }` plus `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | Reference/resource keys `STRING`; identifier `string` / `STRING` | exact ICU `partOf` join, then `CAST(hadm_id_str AS INTEGER)` → `hadm_id INTEGER` |
| `icustays.stay_id` → `stay_id` | ICU `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` `string` / `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`, natural key |
| `chartevents.charttime` → `intime_hr`, `outtime_hr` input | Observation `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`, offset-bearing `string`; materialized `STRING` | `CAST(effective_datetime AS TIMESTAMP_NTZ)` gives the served wall clock; aggregate `MIN`/`MAX` by `stay_id`. Do not offset-convert. |
| `chartevents.itemid` | constrained coding `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code` `code`, materialized `STRING` | filter exact string `item_code = '220045'` inside the chartevents system; cast only after system/code filtering if needed |
| coded system | constrained coding `{ "path": "system", "name": "item_system" }` | FHIR `Coding.system` `uri`, materialized `STRING` | exact discriminator `item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` |
| dimension label (not source output) | constrained coding `{ "path": "display", "name": "item_display" }` | FHIR `Coding.display` `string`, materialized `STRING` | `Heart Rate` on 13,913/13,913; no filtering or output use |
| resource identity (support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | `Observation` resource key `STRING` | not a source output or natural key; retain for conditional UUID/charttime recovery only |
| `chartevents.value` / `valuenum` (not source output) | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR `Quantity.value` decimal; ViewDefinition alias `STRING`; raw Delta decimal `DECIMAL(32,6)` | preserve the uncast alias string if recreating the ETL UUID witness; no value arithmetic is needed for `MIN`/`MAX` |

The final SQL must cast all three identifier values to `INTEGER`. It must also
cast the datetime alias directly to `TIMESTAMP_NTZ`; `CAST(... AS TIMESTAMP)`
session timezone and can produce different values on the laptop and HPC. There
is no need to cast `quantity_value` for this concept's MIN/MAX aggregation.

## Cardinality and null probes

Authoritative Delta results:

| Check | Result |
|---|---:|
| ICU Encounter resources | 140 |
| ICU identifier rows / distinct ICU resources | 140 / 140 |
| ICU `stay_id_str`, Patient key, `parent_encounter_key`, period start/end | 140 / 140 each |
| Hospital Encounter resources after exact stream selection | 275 |
| Hospital identifier rows / distinct hospital resources | 275 / 275 |
| Patient resources / patient identifiers | 100 / 100 |
| target Observation rows/resources | 13,913 / 13,913 |
| target Observation subject references | 13,913 / 13,913 |
| target Observation ICU Encounter references | 13,913 / 13,913 |
| target effective dateTime | 13,913 / 13,913 |
| target `Period.start` / `instant` variants | 0 / 0 |
| target Quantity value | 13,913 / 13,913 |
| target code/system/display | 13,913 / 13,913 each |

The source DuckDB demo checks found 140 `icustays`, 13,913
`chartevents.itemid=220045` rows, 140 distinct heart-rate `stay_id` values,
and 140 stays after the left join. All 140 stays have a heart-rate row and
therefore non-null `MIN` and `MAX` in the demo; there are no target source NULL
`value` rows or NULL `valuenum` rows. The target has no duplicate
`(stay_id, charttime)` heart-rate rows (13,913 rows and 13,913 groups).

The global chartevents ETL predicates still matter on full data: it excludes
source rows with `value IS NULL` and one hard-coded duplicate tuple
`(stay_id=34934165, charttime='2151-10-03 05:14:00')` before Observation
creation. The exact demo query found 0 rows for that tuple and 0/13,913 target
heart-rate NULL values, so neither omission affected this demo. A source stay
with no served heart-rate Observation is an intrinsic coverage gap; preserve
the left-join output row with typed NULL `intime_hr`/`outtime_hr`, not an inner
join that drops the ICU stay.

## UUID/charttime recovery and DST normalization

The served `Observation.effectiveDateTime` is normally the source charttime
rendered with an offset. The upstream ETL first computes the Observation UUID
from the pre-normalization PostgreSQL text and only then casts charttime through
`TIMESTAMPTZ`:

```text
uuid = uuid_generate_v5(
  ns_observation_chartevents,
  ce.stay_id || '-' || ce.charttime || '-' || ce.itemid || '-' || ce.value
)
effectiveDateTime = CAST(ce.charttime AS TIMESTAMPTZ)
```

Relevant files/lines: `/Users/nau025/Documents/mimic-fhir/sql/`
`fhir_observation_chartevents.sql:8-10,20-23,60-67` and
`fhir_etl/uuid_namespace.sql:7-32`. The namespace chain is:

```text
uuid_ns_oid() = 6ba7b812-9dad-11d1-80b4-00c04fd430c8
MIMIC-IV      = 24ba6d92-ae8e-56f9-8898-873d8cba02da
ObservationChartevents = 36e18860-b4aa-5577-bc80-a5b07922cd3d
```

For this concept, direct `TIMESTAMP_NTZ` parsing of the served effective time
matched the demo source charttime for 13,911/13,913 target Observations. Two
served effective times were 03:00 while their exact UUID matched source 02:00
rows, so they are conditional DST-gap recoveries:

| stay_id | source charttime | served effectiveDateTime | value |
|---:|---|---|---:|
| 30,932,571 | 2116-03-08 02:00 | 2116-03-08T03:00:00-04:00 | 109 |
| 32,128,372 | 2137-03-10 02:00 | 2137-03-10T03:00:00-04:00 | 100 |

The demo source had exactly two March 02:xx target rows, no duplicate
`(stay_id, charttime)` target groups, and all 13,913 served resource IDs were
accounted for by either the direct effective wall-time UUID or the one-hour
earlier UUID. The recovery is therefore:

1. Preserve `observation_key` and extract the UUID after `Observation/`.
2. Parse `effective_datetime` with `CAST(... AS TIMESTAMP_NTZ)`.
3. Recreate the ETL UUID using the ICU `stay_id_str`, exact `item_code`, and
   **uncast** `quantity_value` string at the served wall time.
4. Use that wall time if the UUID matches.
5. Otherwise test exactly one hour earlier; use it only if that UUID matches.
6. Never blanket-shift 03:xx rows. A genuine 03:xx row matches the direct
   candidate. Do not use Spark `DATE_FORMAT` for the UUID name after subtracting
   an hour; it can re-normalize an NTZ value in a session-zone DST gap. Preserve
   the wall-clock string with an NTZ-safe string cast.

For `intime_hr`/`outtime_hr`, recover the pre-normalization charttime before
grouping if exact oracle equality is required. If an Observation has neither
UUID candidate match, there is no warrant to invent a correction; retain the
served wall clock and document the residual.

## Oracle agreement and gaps

A pandas comparison was run after materializing ICU Encounter, hospital
Encounter, Patient, and constrained chart Observation views and joining on the
UUID spine. The demo candidate had 140 rows and the DuckDB oracle had 140 rows:

```text
subject_id + hadm_id + stay_id exact: 140/140
intime_hr exact:                       140/140
outtime_hr exact:                      140/140
candidate nulls:                       0 in every output column
oracle nulls:                          0 in every output column
```

The exact candidate used `CAST(identifier_value AS INTEGER)` for IDs,
`CAST(effective_datetime AS TIMESTAMP_NTZ)` for the initial charttime, and the
source `MIN`/`MAX` aggregation by the ICU stay. The UUID check then identified
the two demo DST-gap rows above; after conditional correction, all 140 stay
tuples and both aggregate endpoints remain exact. The source chartevents target
had 13,913 rows and the FHIR target had 13,913 rows/resources, with a 1.000
coding-per-resource ratio.

Gaps:

1. **Numeric IDs:** absent from Observation/Encounter references as numeric
   values, but exactly derivable through the Patient and ICU Encounter
   identifier spine. This is not a representability loss; cast the FHIR strings.
2. **Heart-rate charttime:** served `effectiveDateTime` is normally the value,
   but two demo rows required the ETL UUID witness because DST-gap normalization
   changed 02:00 to 03:00. It is absent from the effective element alone but
   exactly recoverable for this ETL when the UUID candidate matches. Without a
   match it is not safely derivable.
3. **Potential omitted chartevents rows:** the upstream ETL's NULL-value and
   hard-coded duplicate predicates can make source rows absent rather than
   NULL-valued FHIR rows. This is not representable from a missing resource.
   It was not exercised by the demo target (0 affected rows). The source's
   left join still requires typed NULL endpoints for any stay lacking a target
   Observation.
4. **`hadm_id` from ICU `partOf`:** exactly derivable in the authoritative demo
   (140/140 parents). If a future warehouse has an ICU Encounter without
   `partOf`, no exact admission identifier is available from this source's FHIR
   stream; do not substitute an ambiguous patient/time heuristic.

## Notes and fragments consulted

Established `MIMIC_NOTES.md` entries that changed this mapping decision:

- **Raw NDJSON is stale; Delta is authoritative:** all system/code/cardinality
  claims above used embedded Pathling over Delta. The local snapshots were only
  sanity-checked; `MimicEncounterICU.ndjson.gz` had 140 resources and
  `MimicObservationChartevents.ndjson.gz` had 13,913 target codings, but neither
  was treated as the source of truth.
- **MIMIC IDs live in `identifier.value` strings:** required the Patient and
  Encounter identifier spine, UUID-only joins, and final integer casts.
- **Encounter identifier systems/class:** required the exact ICU/hospital
  identifier filters and `partOf` join; `class` was not used.
- **Observation itemid codes are verbatim and use the chartevents system:**
  required exact system + code filtering, no terminology resolution, and the
  `forEach` code/system/display projection.
- **Observation subtype profiles are unstable:** prohibited `meta.profile` as
  the discriminator.
- **FHIR datetimes carry offsets; use `TIMESTAMP_NTZ`:** required wall-clock
  parsing and led to the conditional UUID recovery for DST-gap rows.

All existing sibling fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` were
read as provisional leads: `README.md`, `arb.md`, `blood_differential.md`,
`cardiac_marker.md`, `chemistry.md`, `code_status.md`,
`complete_blood_count.md`, `coagulation.md`, `crrt.md`, `dobutamine.md`,
`dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`, `icp.md`, and
`icustay_detail.md`. The applicable sibling leads on ICU identifier spine,
chartevents ETL omissions, effective datetime choices, and UUID/charttime DST
recovery were independently checked against this concept's target. Sibling
concept-specific counts were not adopted as evidence. The `icustay_detail.md`
ICU period transformation lead was read but is not a mapping decision here;
this source uses chart Observation effective time, not ICU period endpoints.

No new dataset-wide quirk was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_times.md`: the owned fragment did
not exist before this probe, and the confirmed findings are already covered by
the curated identifier, coding, datetime, and chartevents UUID/ETL notes. The
two-row DST count is concept-specific evidence and belongs here, not in a
shared note.

No ViewDefinition, concept SQL, or attempt artifact was authored. This file is
the reusable FHIR-prober carryover.
