# FHIR prober mapping: `lods`

**Concept:** `score/lods`
**Source analysis:** `mimic-iv/concepts_fhir/carryover/lods/source-analyst.md`
**Canonical source:** `mimic-iv/concepts/score/lods.sql`
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`
**Probe engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone UTC
**Read-only source snapshots:** `/Users/nau025/warehouses/mimic-iv-duckdb-demo/{icu,hosp}`

This is a mapping table, not a ViewDefinition or a terminal equivalence
decision. Resource and reference keys are opaque identity strings. No resource
id was parsed, regenerated, hashed, hardcoded, or used to infer a source value.

## Target contract

The source has one final row per ICU `stay_id` and the manifest declares
73,181 full rows, keyed by `stay_id`:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
lods INTEGER, neurologic INTEGER, cardiovascular INTEGER,
renal INTEGER, pulmonary INTEGER, hematologic INTEGER, hepatic INTEGER
```

The port must also retain the required opaque companion keys
`patient_key`, `encounter_key`, and `icu_encounter_key`. The comparison manifest
does not list these auxiliary key columns, but the export/dependency interface
requires them.

## Source table/stream to FHIR mapping

| MIMIC-IV source/interface | MIMIC-on-FHIR resource/interface | Role |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Final one-row-per-stay spine; supplies ICU identity and period |
| `mimiciv_hosp.admissions` | Parent hospital `Encounter`, filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | Existence gate in `cohort`; no admission attribute is used |
| `mimiciv_hosp.patients` | `Patient`, filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/patient` | Existence gate and `subject_id` value |
| `mimiciv_icu.chartevents` item `226732` | Chartevents `Observation` | Direct CPAP/BiPAP-mask interval input |
| `mimiciv_derived.bg` | Published dependency view `bg` | `charttime`, hospital encounter key, and `pao2fio2ratio` |
| `mimiciv_derived.ventilation` | Published dependency view `ventilation` | `starttime`, `endtime`, and `ventilation_status` |
| `mimiciv_derived.first_day_gcs` | Published dependency view `first_day_gcs` | `gcs_min` |
| `mimiciv_derived.first_day_lab` | Published dependency view `first_day_lab` | BUN, WBC, bilirubin, creatinine, PT, platelets |
| `mimiciv_derived.first_day_urine_output` | Published dependency view `first_day_urine_output` | `urineoutput` |
| `mimiciv_derived.first_day_vitalsign` | Published dependency view `first_day_vitalsign` | Heart-rate and systolic-BP extrema |

The source `cohort` uses inner admission/patient existence joins, but the final
query starts from all ICU stays and left joins `scorecomp`. Preserve that
distinction: missing cohort data must not remove the final ICU-spine row.

## Canonical FHIRPath projections

### Patient

```json
{
  "path": "getResourceKey()",
  "name": "patient_key"
}
```

```json
{
  "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value",
  "name": "subject_id_str"
}
```

`subject_id_str` is FHIR `Identifier.value` (`string`/Pathling `VARCHAR`), and
must be cast to final `INTEGER`. `patient_key` remains an uncast,
type-prefixed opaque string.

### ICU Encounter

```json
{
  "path": "getResourceKey()",
  "name": "icu_encounter_key"
}
```

```json
{
  "path": "subject.getReferenceKey(Patient)",
  "name": "patient_key"
}
```

```json
{
  "path": "partOf.getReferenceKey(Encounter)",
  "name": "encounter_key"
}
```

```json
{
  "path": "period.start",
  "name": "intime_datetime"
}
```

```json
{
  "path": "period.end",
  "name": "outtime_datetime"
}
```

```json
{
  "path": "value",
  "name": "stay_id_str"
}
```

The identifier value is projected inside:

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    {"path": "system", "name": "stay_system"},
    {"path": "value", "name": "stay_id_str"}
  ]
}
```

`intime_datetime` and `outtime_datetime` are FHIR `dateTime` strings with
offsets. Cast directly to `TIMESTAMP_NTZ`; do not offset-convert them.
`stay_id_str` becomes final `stay_id INTEGER`. `encounter_key` is the parent
hospital Encounter key and is the replacement for published `hadm_id` joins.

### Hospital Encounter

```json
{
  "path": "getResourceKey()",
  "name": "encounter_key"
}
```

```json
{
  "path": "value",
  "name": "hadm_id_str"
}
```

The identifier projection is constrained inside:

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')",
  "column": [
    {"path": "system", "name": "hadm_system"},
    {"path": "value", "name": "hadm_id_str"}
  ]
}
```

`hadm_id_str` is FHIR `string`; cast it to final `hadm_id INTEGER`. Join the
ICU `Encounter.partOf` key to this hospital Encounter key. Do not use
`Encounter.class` to select either stream.

### Direct CPAP Observation

The source itemid is carried verbatim by `Observation.code.coding`:

```json
{
  "path": "getResourceKey()",
  "name": "observation_key"
}
```

```json
{
  "path": "subject.getReferenceKey(Patient)",
  "name": "patient_key"
}
```

```json
{
  "path": "encounter.getReferenceKey(Encounter)",
  "name": "icu_encounter_key"
}
```

```json
{
  "path": "(effective).ofType(dateTime)",
  "name": "effective_datetime"
}
```

```json
{
  "path": "(value).ofType(string)",
  "name": "value_string"
}
```

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code='226732')",
  "column": [
    {"path": "code", "name": "code"},
    {"path": "system", "name": "system"},
    {"path": "display", "name": "display"}
  ]
}
```

FHIR `value.ofType(string)` is the correct path for item `226732`; it is not a
CodeableConcept and has no Quantity value. The source filters its value text
after extraction:

```text
LOWER(value_string) LIKE '%cpap%'
OR LOWER(value_string) LIKE '%bipap mask%'
```

## Published dependency interfaces

Dependencies are consumed in their published resource-key shape, not by
rederiving raw FHIR observations. The runner strips an identifier when the
corresponding resource key is present.

| Dependency | Published fields consumed by `lods` | Published/FHIR type | Join/use |
|---|---|---|---|
| `bg` | `charttime`, `pao2fio2ratio`, `encounter_key`, `patient_key` | `TIMESTAMP_NTZ`, `DOUBLE`, opaque `STRING` keys | Join `bg.encounter_key = ICU.encounter_key` and retain the source time restriction through ICU period |
| `ventilation` | `starttime`, `endtime`, `ventilation_status`, `icu_encounter_key`, `patient_key` | timestamps, `VARCHAR`, opaque `STRING` keys | Join by `icu_encounter_key`; inclusive interval membership; exact status `'InvasiveVent'` |
| `first_day_gcs` | `gcs_min`, `icu_encounter_key`, `patient_key` | `FLOAT`, opaque `STRING` keys | Left join by ICU key |
| `first_day_lab` | `bun_max`, `bun_min`, `wbc_max`, `wbc_min`, `bilirubin_total_max`, `creatinine_max`, `pt_min`, `pt_max`, `platelets_min`, `icu_encounter_key`, `patient_key` | nullable `DOUBLE`, opaque `STRING` keys | Left join by ICU key; aliases `bilirubin_total_max` → `bilirubin_max` and `platelets_min` → `platelet_min` |
| `first_day_urine_output` | `urineoutput`, `icu_encounter_key`, `patient_key` | nullable `DOUBLE`, opaque `STRING` keys | Left join by ICU key |
| `first_day_vitalsign` | `heart_rate_max`, `heart_rate_min`, `sbp_max`, `sbp_min`, `icu_encounter_key`, `patient_key` | nullable `DOUBLE`, opaque `STRING` keys | Left join by ICU key |

`bg.hadm_id` is present in the attempt/oracle shape but is stripped from the
published dependency because `bg.encounter_key` is emitted. The source
`bg.hadm_id = icustays.hadm_id` inner join is therefore represented by the
opaque equality join `bg.encounter_key = ICU Encounter.partOf key`. This is an
equality substitution, not parsing or regeneration of an id.

The dependency FHIR provenance is:

| Dependency field | Upstream FHIRPath | FHIR type |
|---|---|---|
| `bg.charttime` | `(effective).ofType(dateTime)` on lab Observation | `dateTime` string; published `TIMESTAMP_NTZ` |
| `bg.encounter_key` | `encounter.getReferenceKey(Encounter)` on lab Observation | `Reference(Encounter)` key string |
| `bg.pao2fio2ratio` | completed `bg` derivation from Quantity values (primarily codes `50821`, `50816`, and chart `223835`) | derived `DOUBLE`; no single FHIRPath |
| `ventilation.starttime/endtime` | completed dependency derivation from chartevents `(effective).ofType(dateTime)` | derived timestamps |
| `ventilation.ventilation_status` | completed dependency derivation from oxygen-device/mode strings | derived `VARCHAR` |
| all first-day numeric fields | completed dependency aggregations from their own Observation/Specimen mappings | nullable numeric dependency fields; no single direct FHIRPath |

## Source-column to FHIRPath mapping

| Source column / role | Canonical `{path, name}` mapping | FHIR type | Final/use type |
|---|---|---|---|
| `icustays.subject_id` | `{"path":"subject.getReferenceKey(Patient)","name":"patient_key"}` → Patient `{"path":"identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value","name":"subject_id_str"}` | Reference key + Identifier `string` | `CAST(subject_id_str AS INTEGER)` → `subject_id`; emit `patient_key` |
| `icustays.hadm_id` | ICU `{"path":"partOf.getReferenceKey(Encounter)","name":"encounter_key"}` → hospital `{"path":"value","name":"hadm_id_str"}` under the hospital identifier system | Reference key + Identifier `string` | `CAST(hadm_id_str AS INTEGER)` → `hadm_id`; emit `encounter_key` |
| `icustays.stay_id` | ICU `{"path":"value","name":"stay_id_str"}` inside the ICU identifier group | Identifier `string` | `CAST(stay_id_str AS INTEGER)` → `stay_id`; emit `icu_encounter_key` |
| `icustays.intime` | `{"path":"period.start","name":"intime_datetime"}` | `dateTime` string | `TIMESTAMP_NTZ`; CPAP first-day anchor and blood-gas lower bound |
| `icustays.outtime` | `{"path":"period.end","name":"outtime_datetime"}` | `dateTime` string | `TIMESTAMP_NTZ`; exclusive blood-gas upper bound |
| `chartevents.itemid` | `{ "path": "code", "name": "code" }` under constrained `code.coding` | `Coding.code` string | Exact code filter `226732`; never display/profile |
| `chartevents.value` | `{ "path": "(value).ofType(string)", "name": "value_string" }` | `string` | `LOWER` text filters for CPAP/BiPAP mask |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` string | `TIMESTAMP_NTZ`; CPAP interval envelope |
| `chartevents.stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` → ICU identifier | Encounter reference key + Identifier `string` | Equality join; final `stay_id` from ICU Encounter |
| `bg.hadm_id` | Published replacement `bg.encounter_key`; upstream `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | Encounter reference key string | Equality join to ICU `partOf`; do not join on a stripped integer |
| `bg.charttime` | Upstream `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime`; published `TIMESTAMP_NTZ` | Blood-gas inclusion and CPAP/vent interval membership |
| `bg.pao2fio2ratio` | Completed `bg` dependency output | derived numeric | `MIN` after invasive-vent/CPAP filtering |
| `ventilation.starttime` | Completed dependency output from effective dateTime | derived timestamp | Inclusive lower interval bound |
| `ventilation.endtime` | Completed dependency output from effective dateTime | derived timestamp | Inclusive upper interval bound |
| `ventilation.ventilation_status` | Completed dependency status string | derived `VARCHAR` | Exact predicate `'InvasiveVent'`; this is not a `code.coding` filter |
| `first_day_gcs.gcs_min` | Completed dependency output | nullable `FLOAT` | Neurologic CASE input |
| `first_day_vitalsign.heart_rate_max/min` | Completed dependency output | nullable `DOUBLE` | Cardiovascular CASE input |
| `first_day_vitalsign.sbp_max/min` | Completed dependency output | nullable `DOUBLE` | Cardiovascular CASE input |
| `first_day_urine_output.urineoutput` | Completed dependency output | nullable `DOUBLE` | Renal CASE input |
| `first_day_lab.bun_max/min` | Completed dependency output | nullable `DOUBLE` | Renal/hematologic CASE inputs |
| `first_day_lab.wbc_max/min` | Completed dependency output | nullable `DOUBLE` | Hematologic CASE inputs |
| `first_day_lab.bilirubin_total_max` | Completed dependency output, aliased `bilirubin_max` | nullable `DOUBLE` | Hepatic CASE input |
| `first_day_lab.creatinine_max` | Completed dependency output | nullable `DOUBLE` | Renal CASE input |
| `first_day_lab.pt_min/max` | Completed dependency output | nullable `DOUBLE` | Hepatic CASE inputs |
| `first_day_lab.platelets_min` | Completed dependency output, aliased `platelet_min` | nullable `DOUBLE` | Hematologic CASE input |

## Derived output mapping

These outputs have no single FHIR element. They must be computed exactly from
the mapped dependency columns using the ordered `CASE` expressions in
`lods.sql`.

| Output | Inputs | Type |
|---|---|---|
| `neurologic` | `gcs_min` | nullable `INTEGER` |
| `cardiovascular` | heart-rate and systolic-BP extrema | nullable `INTEGER` |
| `renal` | `bun_max`, `urineoutput`, `creatinine_max` | nullable `INTEGER` |
| `pulmonary` | `pao2fio2_vent_min`; NULL maps to 0 | nullable `INTEGER` |
| `hematologic` | WBC extrema and `platelet_min` | nullable `INTEGER` |
| `hepatic` | PT extrema and `bilirubin_max` | nullable `INTEGER` |
| `lods` | `COALESCE` each of the six component scores to zero, then sum | `INTEGER` |

Do not coalesce the component output columns themselves. The total and the
component nullness have different source semantics.

## Coded filters and served-data confirmation

The only direct coded filter in `lods.sql` is item `226732`. The served system
was established from `Observation.code.coding`, not from the table name or
profile:

```text
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
```

| Exact code | Source raw rows | FHIR coding rows | Distinct Observation resources | Codings/resource | FHIR value path |
|---:|---:|---:|---:|---:|---|
| `226732` | 3,145 | 3,145 | 3,145 | 1.000 | `(value).ofType(string)` |

The fresh UTC Delta probe counted, over all 3,145 item-226732 resources:

```text
observation_key       3145/3145
patient_key           3145/3145
icu encounter key     3145/3145
effective dateTime    3145/3145
effective Period      0/3145
effective instant     0/3145
valueString           3145/3145
Quantity value        0/3145
component text        0/3145
code/system/display   3145/3145 each
```

The raw source count was `itemid=226732: 3,145`, with `value IS NULL: 0`.
The source text filter selected 4 rows containing `cpap` and 28 rows
containing `bipap mask`; the served value distribution contained exactly 4
`CPAP mask` and 28 `Bipap mask` values. Existing oxygen-delivery replay also
matched all 3,145 source/FHIR tuples and all 3,014 `(subject_id, charttime)`
groups exactly. The repeated rows must not be deduplicated before applying the
source interval logic.

`'InvasiveVent'` is not a FHIR coding literal. It is a string value in the
completed `ventilation.ventilation_status` dependency, so no separate
`code.coding` count is applicable. The latest ventilation full comparison was
exact: 111,172 candidate/oracle rows, keyed by `(stay_id, starttime)`.

The `system + exact code` rule is valid here. The chartevents URI is distinct
from the shared `mimic-d-items` URI used by outputevents/datetimeevents; in any
shared-system stream, `d_items.itemid` is a global primary key with one
`linksto` value, so exact code remains the discriminator. Never use
`meta.profile`.

## Dependency evidence and freshness

Latest located full comparisons:

| Dependency attempt | Result |
|---|---|
| `bg` attempt_0008 | exact, 511,637/511,637 |
| `first_day_lab` attempt_0003 | exact, 73,181/73,181 |
| `first_day_urine_output` attempt_0002 | exact, 73,181/73,181 |
| `ventilation` attempt_0001 | exact, 111,172/111,172 |
| `first_day_vitalsign` attempt_0001 | 183 value conflicts across 73,181 rows; consume the published dependency and let its own verdict govern |
| `first_day_gcs` attempt_0002 | stale pre-`e7c326b` result with 72,651 NULL-shaped differences; it must be re-run after the completed `gcs` attempt_0008 component-text repair |

The current Delta probe independently confirmed the repaired GCS component
branch: the three-code projection had 9,791/9,791 component texts, with item
`223900` containing 1,348 `No Response-ETT` and 78 `No Response` values. This
supersedes the old `first_day_gcs` carryover's pre-rebuild label-loss claim;
the LODS implementer must consume the refreshed `first_day_gcs` dependency,
not attempt_0002's stale ambiguity propagation.

## Oracle and identity checks

- ICU Encounter probe: 140/140 ICU resources had `icu_encounter_key`,
  `patient_key`, parent hospital key, `period.start`, `period.end`, and ICU
  identifier value.
- Patient probe: 100/100 resources had `patient_key` and the patient identifier.
- ICU-to-hospital `partOf` join: 140/140 ICU stays joined to a hospital
  Encounter; `stay_id` and `hadm_id` agreed with the raw `icustays` snapshot
  140/140.
- The prior dependency source/FHIR spine checks matched ICU identifiers and
  `intime` 140/140. Current UTC rebuilding means the historical DST-gap shift
  must not be reproduced; use `TIMESTAMP_NTZ` to preserve served wall-clock
  values.
- CPAP source/FHIR tuple agreement was 3,145/3,145 in the oxygen-delivery
  replay; the filtered CPAP/BiPAP text counts were 4/28.

## Gaps and representability

1. **No target-essential CPAP value gap in the rebuilt demo.** Item 226732's
   source text is present at `value.ofType(string)` for all 3,145 rows, and
   the source filter can identify the 32 selected rows exactly. A future
   source NULL cannot satisfy either `LIKE` branch, so the global FHIR
   `value IS NOT NULL` omission cannot change this direct filter's inclusion.

2. **No current datetime gap observed in the UTC-built warehouse.** The
   source wall-clock times used by the relevant completed dependency replays
   agreed in the demo. The original source wall time would be
   non-representable if an upstream non-UTC/DST normalization were present;
   resource IDs remain forbidden as a recovery channel. Measure any full-run
   divergence rather than applying a manual hour correction.

3. **Admission/patient existence is essential if a reference is absent.** The
   source `cohort` inner joins admissions and patients, so a missing
   `Encounter.partOf` or Patient reference can change whether a scorecomp row
   exists. In the current demo, parent admission, ICU identifier, patient
   reference, and period fields were all present for 140/140 ICU stays. No
   current demo loss was measured; this is a coverage check for the full run,
   not a prober-side block.

4. **Dependency freshness is not a FHIR representability gap.** The old
   `first_day_gcs` attempt is semantically stale because its dependency was
   ported before the upstream component repair. Do not declare LODS
   unrepresentable from that artifact. The dependency must be refreshed before
   interpreting a LODS comparison.

5. `pao2fio2_vent_min` is absent when no qualifying invasive-vent/CPAP ratio
   exists, but this is represented by the dependency's nullable field and the
   source pulmonary CASE intentionally maps it to score zero. It is not a
   missing FHIR element for this consumer.

## Notes consulted

Established `MIMIC_NOTES.md` entries that changed this mapping were:

- Delta tables are authoritative; stale NDJSON and the unauthorized HTTP
  server are not probe sources.
- MIMIC identifiers live in `identifier.value` as strings; resource/reference
  keys are separate opaque equality keys and required companion outputs.
- ICU/hospital/ED Encounter streams are separated by identifier system, not
  `Encounter.class`; ICU `partOf` links to the hospital Encounter.
- Observation item codes are verbatim and must be discriminated by exact
  `system + code`, never `meta.profile`.
- Chartevents categorical values use `value.ofType(string)`, while the rebuilt
  ETL preserves meaningful numeric-row text in `component.valueString`.
- FHIR datetime aliases must be parsed as `TIMESTAMP_NTZ`; the current
  warehouse is rebuilt under UTC, so the historical DST workaround is not to
  be reproduced.
- Dependency views are consumed in published key-shaped form, and opaque IDs
  cannot recover discarded source values.

Provisional fragments read as leads and checked where relevant were:
`MIMIC_NOTES.d/README.md`, `gcs.md`, `first_day_gcs.md`, `oxygen_delivery.md`,
`ventilation.md`, `ventilator_setting.md`, `first_day_vitalsign.md`, `bg.md`,
`first_day_urine_output.md`, `first_day_lab.md` (missing), and the relevant
`first_day_lab`/dependency carryover files. The old GCS label-loss claims in
`gcs.md` and `first_day_gcs/fhir-prober.md` were not adopted; the rebuilt
component path was independently probed. No other concept fragment was used
as established evidence.

## Evidence block

`lods` maps ICU `icustays` to ICU `Encounter`, admissions to parent hospital
`Encounter`, and patients to `Patient`; direct CPAP input is chartevents
`Observation` item `226732`; all six other inputs are the published dependency
views `bg`, `ventilation`, `first_day_gcs`, `first_day_lab`,
`first_day_urine_output`, and `first_day_vitalsign`. The source mappings are:
`subject_id` → Patient identifier value, `hadm_id` → ICU `partOf` hospital
Encounter identifier value, `stay_id` → ICU Encounter identifier value,
`intime/outtime` → Encounter period start/end, item/value/charttime →
Observation code/valueString/effective dateTime, `bg.hadm_id` → published
`bg.encounter_key`, and all aggregate inputs → their named published
dependency fields. Computed LODS and six component scores have no single FHIR
path and retain the source CASE/null semantics.

The confirmed direct code is system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus code
`226732`: 3,145 source rows, 3,145 FHIR coding rows, 3,145 distinct resources,
ratio 1.000; 4 CPAP and 28 BiPAP-mask rows matched the text predicates.
ICU-to-hospital identity agreed 140/140. The current rebuilt Delta also
confirmed GCS component text 9,791/9,791, including 1,348 ETT and 78 ordinary
No Response labels. The only outstanding implementation dependency is the
stale pre-rebuild `first_day_gcs` attempt; refresh it before judging LODS.

This carryover was written to:
`mimic-iv/concepts_fhir/carryover/lods/fhir-prober.md`.
