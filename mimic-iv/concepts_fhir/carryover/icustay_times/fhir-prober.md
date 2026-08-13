# FHIR prober mapping: `icustay_times`

**Probe date:** 2026-08-13  
**Attempt:** `0002` (re-run after invalidation)  
**Authoritative Delta:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone pinned to UTC  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (read-only)  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/icustay_times/source-analyst.md`  
**Manifest:** 73,181 rows keyed by `stay_id`; `subject_id`, `hadm_id`, and
`stay_id` are `INTEGER`; `intime_hr` and `outtime_hr` are `TIMESTAMP`.

## Reopened-attempt prohibition

The previous carryover used `Observation.id` / `getResourceKey()` UUIDv5
reconstruction to infer pre-normalization `charttime`. That mapping is
invalidated and is not reproduced here. Resource and reference IDs are opaque
identity only: they may be compared for equality to join resources or group
resources, but must never be parsed, regenerated, guessed, hashed, hardcoded,
or used to recover `charttime` or any other source value. The port must use the
served `Observation.effectiveDateTime` and let comparator `key_attribution` and
the equivalence judge handle any proven upstream DST transformation.

The new probe deliberately used no Observation ID value in a mapping, join,
comparison, correction, or aggregation.

## Source table to FHIR resource mapping

| MIMIC-IV source | FHIR resource and stream | Selection / role |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter`, ICU stream | Select `Encounter.identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`. The ICU Encounter identifier carries `stay_id`; its `subject` joins to Patient and its `partOf` joins to the hospital Encounter. The probe found 140 selected ICU resources, one per demo `icustays` row. |
| `mimiciv_icu.chartevents` | `Observation`, chartevents stream | Select `code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` and exact `code = '220045'`. The probe found 13,913 target Observations and one target coding per resource. |
| MIMIC patient spine needed by `icustays.subject_id` | `Patient` | Select `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/patient'`; `identifier.value` carries `subject_id` as a FHIR string. The probe found 100/100 Patient identifiers. |
| MIMIC hospital-admission spine needed by `icustays.hadm_id` | `Encounter`, hospital stream | Select `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'`; `identifier.value` carries `hadm_id` as a FHIR string. The probe found 275/275 hospital Encounters. Join the ICU Encounter `partOf` reference key to this Encounter's resource key. |

The unfiltered Delta `Encounter` resource table has 637 rows: 275 hospital,
140 ICU, and 222 ED. `Encounter.class` is not a stream discriminator. In the
probe, the exact identifier-system selections produced the expected 140 ICU
and 275 hospital rows. Do not use `meta.profile` for Observation stream
selection.

## Confirmed coded filter

The source analyst lifted exactly one code: `mimiciv_icu.chartevents.itemid =
220045`. The authoritative Delta carries the itemid unchanged as a string
FHIR coding:

| Source itemid | `Coding.system` | `Coding.code` | `Coding.display` | coding rows | distinct resources | codings/resource |
|---:|---|---|---|---:|---:|---:|
| 220045 | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220045` | `Heart Rate` | 13,913 | 13,913 | 1.000 |

The exact target code has no alternate system and no dead lifted code. As a
stream-level check, all chartevents-system codings were 668,862 over 668,862
distinct resource IDs (ratio 1.000). A served `CodeSystem` resource is not
available; the system/code/display above were read from the Delta Observation
codings. `d_items.itemid` is a global primary key with one `linksto` value per
item, so system plus exact code separates this chartevents stream from other
ICU item streams. The rule is still system + exact code, never profile.

Use this constrained coding group, not an unconstrained `code.coding` group:

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

For this concept the bare and constrained coding projections have the same
cardinality because the measured ratio is 1.000. Keep the constraint because
the ratio is a warehouse property, not a FHIR guarantee.

## Canonical ViewDefinition projections

These are mapping projections, not an attempt ViewDefinition. Identifier
values remain string-like in the materialized views and are cast only in the
final SQL. Resource/reference keys are opaque strings used only for equality
joins.

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
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter the materialized ICU view with `stay_id_str IS NOT NULL`. The probe
found 140/140 selected rows with non-null `encounter_key`, `patient_key`,
`parent_encounter_key`, and `stay_id_str`; all 140 stay identifiers were
distinct.

### Hospital Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
  ]
}
```

Filter the materialized hospital view with `hadm_id_str IS NOT NULL`. The
probe found 275/275 selected rows with non-null hospital identifiers.

### Heart-rate Observation

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }
  ]
}
```

Append the constrained coding group above. The source charttime mapping is
the `dateTime` choice only. On the 13,913 target Observations:

| View alias | FHIR type | Materialized Spark type | rows / non-null |
|---|---|---|---:|
| `observation_key` | opaque `Observation` resource key | `STRING` | 13,913 / 13,913 |
| `patient_key` | `Reference(Patient)` key | `STRING` | 13,913 / 13,913 |
| `encounter_key` | `Reference(Encounter)` key | `STRING` | 13,913 / 13,913 |
| `effective_datetime` | `dateTime` | `STRING` | 13,913 / 13,913 |
| `effective_period_start` (probe-only) | `Period.start` | `STRING` | 13,913 / 0 |
| `effective_instant` (probe-only) | `instant` | `TIMESTAMP` | 13,913 / 0 |
| `quantity_value` (probe-only) | `Quantity.value` decimal | ViewDefinition alias `STRING` | 13,913 / 13,913 |

The `Period`, `instant`, and Quantity aliases above are probe evidence only;
the source SQL does not need them. In particular, do not coalesce the unused
native `instant` alias with the string `dateTime` alias: that can cause Spark
to parse the offset as an instant before the wall-clock cast.

## Source-column to FHIRPath mapping and target types

| Source column / output | Canonical mapping `{path, name}` | FHIR type and served type | Final SQL requirement |
|---|---|---|---|
| `icustays.subject_id` → `subject_id` | ICU Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key is opaque `STRING`; `Identifier.value` is FHIR `string`, materialized `STRING` | Join `patient_key`; `CAST(subject_id_str AS INTEGER)` for manifest `subject_id INTEGER`. Never use `getReferenceKey(Patient)` as the numeric output. |
| `icustays.hadm_id` → `hadm_id` | ICU Encounter `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }`; hospital Encounter `{ "path": "getResourceKey()", "name": "encounter_key" }` and `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | Reference/resource keys are opaque `STRING`; `Identifier.value` is FHIR `string`, materialized `STRING` | Equality join parent key to hospital resource key; `CAST(hadm_id_str AS INTEGER)` for manifest `hadm_id INTEGER`. |
| `icustays.stay_id` → `stay_id` | ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | FHIR `Identifier.value` `string`, materialized `STRING` | `CAST(stay_id_str AS INTEGER)` for manifest `stay_id INTEGER`; natural key. |
| `chartevents.itemid` | constrained coding `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code`, materialized `STRING` | Filter `item_system` plus exact string `item_code = '220045'`; cast only after filtering if needed. |
| Coding system | constrained coding `{ "path": "system", "name": "item_system" }` | FHIR `uri`, materialized `STRING` | Require the exact chartevents system URI shown above. |
| Item label | constrained coding `{ "path": "display", "name": "item_display" }` | FHIR `string`, materialized `STRING` | `Heart Rate` on 13,913/13,913; informational only, not a discriminator. |
| `chartevents.charttime` → `intime_hr` / `outtime_hr` input | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` with an offset-bearing lexical string; materialized `STRING` | `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` directly, then `MIN`/`MAX` by `stay_id_str`. Final output must be the manifest timestamp type while retaining NTZ wall-clock semantics; do not use plain `TIMESTAMP` or offset-aware `to_timestamp`. |
| Observation reference to ICU stay | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | FHIR `Reference(Encounter)` key, opaque `STRING` | Equality join to ICU `encounter_key`; never parse the reference key. |
| Observation patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | FHIR `Reference(Patient)` key, opaque `STRING` | Equality join/provenance only; numeric `subject_id` comes from Patient `identifier.value`. |
| Resource identity support | `{ "path": "getResourceKey()", "name": "observation_key" }` for Observation; `{ "path": "getResourceKey()", "name": "encounter_key" }` for Encounter; `{ "path": "getResourceKey()", "name": "patient_key" }` for Patient | Opaque resource key, materialized `STRING` | Join/group identity only. Do not use an ID or UUID to infer, correct, or compare a source timestamp or any source value. |

## NULL preservation and SQL shape

The source creates one row for every `icustays` row and uses a `LEFT JOIN` to
the heart-rate aggregate. The FHIR implementation must preserve that shape:

```sql
WITH heart_rate_times AS (
    SELECT
        i.stay_id_str,
        MIN(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS intime_hr,
        MAX(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS outtime_hr
    FROM icustay_times_observation o
    JOIN icustay_times_icu_encounter i
      ON o.encounter_key = i.encounter_key
    WHERE i.stay_id_str IS NOT NULL
      AND o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
      AND o.item_code = '220045'
    GROUP BY i.stay_id_str
)
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(h.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(i.stay_id_str AS INTEGER) AS stay_id,
    hr.intime_hr,
    hr.outtime_hr
FROM icustay_times_icu_encounter i
LEFT JOIN icustay_times_hospital_encounter h
  ON i.parent_encounter_key = h.encounter_key
LEFT JOIN icustay_times_patient p
  ON i.patient_key = p.patient_key
LEFT JOIN heart_rate_times hr
  ON i.stay_id_str = hr.stay_id_str
WHERE i.stay_id_str IS NOT NULL;
```

The ICU-stay backbone is the left side. A stay with no served target
Observation must remain a row with typed NULL `intime_hr` and `outtime_hr`;
an inner join to the aggregate would change an absent timestamp into a
missing row. The hospital and Patient joins are also left joins so an absent
FHIR parent/reference cannot silently drop an ICU stay. Do not replace a
missing `hadm_id` with a patient/time heuristic.

## Offset-bearing FHIR datetime handling

The authoritative target has strings such as
`2110-04-11T15:54:00-04:00`. `CAST(... AS TIMESTAMP_NTZ)` preserves the served
wall-clock `2110-04-11 15:54:00` regardless of the session timezone. The probe
confirmed all 13,913 target strings were non-null and parseable by this direct
cast. Do not use `to_timestamp` with an offset format, because it converts to
the session-zone instant; do not use a plain `TIMESTAMP` cast after NTZ
parsing, because it reintroduces timezone conversion. Cast before `MIN`/`MAX`
and before any `COALESCE`; no choice variant needs coalescing for item 220045.

The served FHIR effective time is not guaranteed to preserve every original
MIMIC wall clock. A direct source/FHIR row check using only `stay_id`, wall
time, and Quantity value matched 13,911/13,913 target rows. Two source rows
were served one hour later by the upstream New York DST-gap normalization:

| stay_id | source charttime | served `effectiveDateTime` wall clock | value |
|---:|---|---|---:|
| 30,932,571 | 2116-03-08 02:00 | 2116-03-08 03:00 | 109 |
| 32,128,372 | 2137-03-10 02:00 | 2137-03-10 03:00 | 100 |

These two row-level losses were identified without reading or manipulating
Observation IDs. They did not change the demo `MIN`/`MAX` endpoint for any
stay: the direct, no-ID aggregate matched the DuckDB oracle for all five
output columns on 140/140 demo stays. On full data, any residual from this
upstream transformation must remain visible to the comparator/judge; it is
not a reason to reconstruct an ID.

## Probe counts and oracle checks

Authoritative embedded Pathling/Spark counts:

- selected ICU Encounter rows/resources: 140/140; `stay_id_str`, Patient key,
  and ICU parent key all 140/140 non-null and distinct where expected;
- selected hospital Encounter rows/resources: 275/275, with `hadm_id_str`
  275/275 non-null;
- Patient rows/resources: 100/100, with `subject_id_str` 100/100 non-null;
- target Observation rows/resources: 13,913/13,913;
- target Observation patient references and Encounter references: 13,913/13,913;
- target dateTime: 13,913/13,913; Period.start and instant variants: 0/13,913;
- target Quantity value: 13,913/13,913; target code/system/display:
  13,913/13,913 each;
- ICU `partOf` to hospital Encounter: 140/140 in the selected ICU stream;
- target Observation Encounter references resolving to selected ICU Encounters:
  13,913/13,913, covering all 140 ICU stays.

Read-only DuckDB checks:

- `mimiciv_icu.icustays`: 140 rows;
- `itemid = 220045`: 13,913 rows across 140 stays;
- target `value IS NULL`: 0/13,913; target `valuenum IS NULL`: 0/13,913;
- target `charttime IS NULL`: 0/13,913;
- target `(stay_id, charttime)` groups: 13,913 rows and 13,913 groups;
- the global ETL duplicate tuple `(34934165, 2151-10-03 05:14:00)` was absent
  (0 rows) in this demo target;
- direct FHIR aggregate versus source oracle: `subject_id` 140/140 exact,
  `hadm_id` 140/140, `stay_id` 140/140, `intime_hr` 140/140, and `outtime_hr`
  140/140; both sides had zero NULLs in the demo.

The source ETL also globally excludes chartevents rows with NULL `value` and
one hard-coded duplicate tuple. The target-specific demo checks above found
neither condition exercised. A full-data source row absent from FHIR cannot
be recovered from a missing resource; preserve the ICU backbone and typed
NULL aggregate endpoints rather than dropping the stay.

## Gaps and essentiality

1. **Numeric identifier values:** FHIR references/resource keys do not carry
   numeric MIMIC IDs as keys, but `subject_id`, `hadm_id`, and `stay_id` are
   exactly derivable from the three `Identifier.value` paths and the ICU
   `partOf` equality join. This is absent-but-derivable, not a gap. The
   materialized aliases are `STRING`; final SQL casts are required for the
   manifest `INTEGER` columns.
2. **Original charttime at DST-gap rows:** the served effective element
   carries the transformed wall clock. The two demo source rows above are
   absent-but-not-recoverable from allowed FHIR semantics; their original
   `02:00` is not in another mapped element. UUID inversion is a forbidden
   side channel and is not an approximation. For this concept's demo
   `MIN`/`MAX`, the loss is ancillary because the endpoints remain exact. On
   full data, if a transformed measurement changes which row supplies a
   per-stay minimum or maximum, it can change a clinically meaningful output
   and therefore becomes essential to that row's endpoint; the comparator and
   judge must assess it. Do not block or accept it at the prober stage.
3. **Rows omitted by the chartevents ETL:** a source row excluded before
   Observation creation is not representable as a FHIR value. For this
   source query the omitted row can alter a per-stay MIN/MAX if it is the only
   or an endpoint heart-rate row, so the missing information is potentially
   essential. The demo showed no such omission; whole-concept treatment is a
   later judge decision, not a prober decision.
4. **Missing ICU parent or Patient reference:** no exact numeric `hadm_id` or
   `subject_id` can be obtained if the corresponding resource/reference is
   absent. Patient/time reconstruction would be a heuristic and can be
   ambiguous; do not manufacture a value. Keep the ICU row with a typed NULL.
   In the authoritative demo, both spines resolved exactly for all 140 stays.

## Notes and fragments consulted

The following established `MIMIC_NOTES.md` entries changed this mapping:

- **Raw NDJSON is stale; Delta is authoritative:** all resource, coding, and
  population claims above came from embedded Pathling over the Delta, not raw
  NDJSON or the unavailable live server.
- **MIMIC IDs live in `identifier.value` as strings:** required the separate
  opaque UUID join keys, string identifier aliases, and final integer casts.
- **Encounter has three identifier systems and class discriminates none:**
  required exact ICU/hospital identifier-system selection and prohibited class
  filtering; ICU `partOf` supplies the hospital Encounter equality join.
- **Observation itemid codes are verbatim:** required exact string code
  `220045`, the observed chartevents system, and no terminology translation.
- **Observation subtype profiles are warehouse-version dependent:** prohibited
  `meta.profile` as the stream discriminator.
- **FHIR datetimes carry offsets; use `TIMESTAMP_NTZ`:** required direct
  wall-clock parsing, casting before aggregation, and no plain `TIMESTAMP`.
- **Resource IDs are opaque identity and essential-loss policy:** prohibited
  the invalidated UUID/charttime inversion and requires any essential loss to
  proceed to the comparator/judge rather than be hidden by a heuristic.

All existing fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` were read as
provisional leads: `README.md`, `arb.md`, `blood_differential.md`,
`cardiac_marker.md`, `chemistry.md`, `code_status.md`,
`complete_blood_count.md`, `coagulation.md`, `crrt.md`, `dobutamine.md`,
`dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`, `icp.md`,
`invasive_line.md`, `kdigo_creatinine.md`, and `icustay_detail.md`. The
relevant ICU identifier, chartevents omission, datetime-choice, and superseded
UUID/id leads were independently checked against this target. The
`icustay_detail.md` ICU period/LOS finding was not substituted for heart-rate
Observation effective time. The superseded UUID/id warnings in `icp.md`,
`gcs.md`, `height.md`, `crrt.md`, and `code_status.md` were treated as
prohibitions, not mappings.

No `MIMIC_NOTES.d/icustay_times.md` fragment existed before this re-probe. No
new dataset-wide quirk was found that is not already covered by
`MIMIC_NOTES.md` or the provisional leads, so no own fragment entry was
appended. The two DST rows and all other target-specific counts remain in this
concept carryover rather than being promoted as dataset-wide facts.

This reusable mapping was written for the invalidated-stage retry. It authors
no ViewDefinition or concept SQL and uses no Observation/resource UUID as a
source-value channel.
