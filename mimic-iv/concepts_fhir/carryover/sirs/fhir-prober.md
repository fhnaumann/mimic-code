# FHIR probe and mapping: `sirs`, attempt 0001

**Concept:** `sirs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/sirs/source-analyst.md`  
**Canonical SQL:** `mimic-iv/concepts/score/sirs.sql`  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2, session timezone UTC  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB 1.5.5  
**Structural reference:** `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`

This is a mapping artifact only. No ViewDefinition, candidate SQL, resource ID,
or dependency was authored or reconstructed here. The live HTTP Pathling
server and raw NDJSON were not used.

## Scope and target shape

SIRS has no raw Observation source and no coded filter. Its only direct raw
source is `mimiciv_icu.icustays`; its three direct derived inputs are the
completed dependencies `first_day_bg_art`, `first_day_lab`, and
`first_day_vitalsign`. SIRS must consume those dependency views as published,
without inlining or rederiving their producers.

The full oracle manifest declares `key = ["stay_id"]` and the required opaque
key columns `encounter_key`, `icu_encounter_key`, and `patient_key`. The
compared output types are:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
sirs INTEGER, temp_score INTEGER, heart_rate_score INTEGER,
resp_score INTEGER, wbc_score INTEGER
```

The three required resource keys remain uncast Spark `STRING` values with their
type prefixes intact. `identifier.value` aliases are FHIR `string` values and
must be cast to the manifest's `INTEGER` type only in the final SQL.

## Source table/dependency to served interface

| Source relation | Served interface | SIRS use |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by the ICU identifier system | One left-side row per ICU stay; supplies the three MIMIC identifiers and the three required key columns |
| `mimiciv_derived.first_day_bg_art` | Published dependency view `first_day_bg_art` | `pco2_min`, joined by published `icu_encounter_key` |
| `mimiciv_derived.first_day_vitalsign` | Published dependency view `first_day_vitalsign` | `temperature_min`, `temperature_max`, `heart_rate_max`, `resp_rate_max`, joined by published `icu_encounter_key` |
| `mimiciv_derived.first_day_lab` | Published dependency view `first_day_lab` | `wbc_min`, `wbc_max`, `bands_max`, joined by published `icu_encounter_key` |
| ICU `Encounter.subject` target | `Patient` | Resolves `subject_id` and supplies `patient_key` |
| ICU `Encounter.partOf` target | Hospital `Encounter`, selected by the hospital identifier system | Resolves `hadm_id` and supplies `encounter_key` |

The SIRS source joins dependencies on integer `stay_id`, but the preprocessed
published dependency shape has stripped `stay_id` because it is paired with
`icu_encounter_key`. The implementer must therefore join each dependency on
the opaque equality
`icu_encounter.getResourceKey() = dependency.icu_encounter_key`. Do not join
on a dropped dependency `stay_id`, and do not parse or regenerate a key.

The SIRS attempt's dependency plan resolved in dependency-first order as:

```text
bg                    attempt_0007
first_day_bg_art      attempt_0001
blood_differential    attempt_0003
chemistry             attempt_0004
coagulation           attempt_0005
complete_blood_count  attempt_0003
enzyme                attempt_0003
first_day_lab         attempt_0001
vitalsign             attempt_0002
first_day_vitalsign   attempt_0001
```

`EmbeddedExecutor.preprocess_dependencies()` materialized each completed
attempt, applied `strip_mimic_ids()` to the dependency SQL, cached the result,
and registered the result as a Spark temporary view under the unqualified
concept stem. Thus SIRS will see `FROM first_day_bg_art`,
`FROM first_day_lab`, and `FROM first_day_vitalsign`, not the attempt parquet
shape and not a FHIR resource table.

## Canonical FHIRPath projections for the ICU identity spine

These are the only direct FHIR projections needed by SIRS. Identifier values
are strings; the final target SQL casts them to `INTEGER`.

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
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

The ICU stream discriminator is the exact system
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; `Encounter.class`
must not be used.

### Parent hospital Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
  ]
}
```

The ICU `partOf.getReferenceKey(Encounter)` value joins byte-for-byte to the
hospital Encounter `getResourceKey()` value. It is an opaque equality key, not
a value from which `hadm_id` may be inferred.

## Source-column to FHIRPath mapping

| Source column / role | Canonical `{path, name}` mapping | FHIR type and materialized type | Required target/use type |
|---|---|---|---|
| `icustays.subject_id` / output `subject_id` | ICU Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` joined to Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `Reference(Patient)` key plus `Identifier.value string`; both aliases `STRING` | `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; emit `patient_key` unchanged |
| `icustays.hadm_id` / output `hadm_id` | ICU Encounter `{path: "partOf.getReferenceKey(Encounter)", name: "encounter_key"}` joined to hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}` and `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | `Reference(Encounter)`/resource key plus `Identifier.value string`; aliases `STRING` | `CAST(hadm_id_str AS INTEGER)` → `hadm_id INTEGER`; emit `encounter_key` unchanged |
| `icustays.stay_id` / natural key `stay_id` | ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | `Identifier.value string`; alias `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; emit `icu_encounter_key` unchanged |
| required patient join/output key | ICU Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` (byte-equal to Patient `{path: "getResourceKey()", name: "patient_key"}`) | opaque type-prefixed key `STRING` | required manifest key; equality/provenance only |
| required hospital Encounter join/output key | ICU Encounter `{path: "partOf.getReferenceKey(Encounter)", name: "encounter_key"}` (byte-equal to hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}`) | opaque type-prefixed key `STRING` | required manifest key; equality/provenance only |
| required ICU Encounter join/output key | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque type-prefixed key `STRING` | required manifest key and dependency join; equality/provenance only |

SIRS does not read ICU `period.start`, `period.end`, `intime`, `outtime`, or
any event timestamp. No datetime ViewDefinition column is needed for this
consumer.

## Published dependency columns consumed by SIRS

The following are dependency-boundary mappings, not new FHIR extractions. The
published columns are already materialized outputs of completed concepts. The
FHIR provenance paths are shown only to identify the upstream type; the SIRS
implementer must not query those paths or repeat the upstream filters,
windows, grouping, or aggregates.

| Published dependency column | Upstream provenance `{path, name}` (do not rederive in SIRS) | Upstream FHIR type | Published Spark type / observed population | SIRS use |
|---|---|---|---|---|
| `first_day_bg_art.pco2_min` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` on the completed blood-gas Observation stream | `Quantity.value decimal`; Pathling aliases are string-like before producer casting | nullable `DOUBLE`, 76/140 non-null | `paco2_min < 32.0` and respiratory NULL branch |
| `first_day_vitalsign.temperature_min` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` on the completed chartevents Observation stream | `Quantity.value decimal` | nullable `DECIMAL(38,2)`, 135/140 non-null | low-temperature branch and temperature NULL branch |
| `first_day_vitalsign.temperature_max` | same completed chartevents provenance `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DECIMAL(38,2)`, 135/140 non-null | high-temperature branch |
| `first_day_vitalsign.heart_rate_max` | completed chartevents Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DOUBLE`, 140/140 non-null | heart-rate high-value branch and NULL branch |
| `first_day_vitalsign.resp_rate_max` | completed chartevents Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DOUBLE`, 140/140 non-null | respiratory high-value branch and NULL branch |
| `first_day_lab.wbc_min` | completed labevents Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DOUBLE`, 139/140 non-null | low-WBC branch and WBC NULL branch |
| `first_day_lab.wbc_max` | completed labevents Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DOUBLE`, 139/140 non-null | high-WBC branch |
| `first_day_lab.bands_max` | completed labevents Observation `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` | nullable `DOUBLE`, 23/140 non-null | high-bands branch and WBC NULL branch |
| each immediate dependency `.icu_encounter_key` | producer ICU/reference spine `{path: "getResourceKey()", name: "icu_encounter_key"}`; upstream Observation references use `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}` | opaque `Encounter` key `STRING` | 140/140 non-null and 140 distinct in each published view | equality join to ICU Encounter; replaces source `stay_id` join |
| each immediate dependency `.patient_key` | producer patient/reference spine `{path: "getResourceKey()", name: "patient_key"}`; upstream references use `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | opaque `Patient` key `STRING` | 140/140 non-null and 100 distinct in each published view | retained required output/provenance key; not a new subject-id join predicate in SIRS |

The published immediate dependency views each had 140 rows in the demo. Their
materialized schemas after identifier stripping were checked as follows:

```text
first_day_bg_art:
  pco2_min DOUBLE, patient_key STRING, icu_encounter_key STRING
  (the view also contains the other completed bg extrema; no stay_id/subject_id)

first_day_vitalsign:
  temperature_min/temperature_max DECIMAL(38,2),
  heart_rate_max/resp_rate_max DOUBLE,
  patient_key STRING, icu_encounter_key STRING
  (the view also contains the other completed vital aggregates; no stay_id/subject_id)

first_day_lab:
  wbc_min/wbc_max/bands_max DOUBLE,
  patient_key STRING, icu_encounter_key STRING
  (the view also contains the other completed lab aggregates; no stay_id/subject_id)
```

All three views had `icu_encounter_key` 140/140 non-null and 140 distinct;
`patient_key` was 140/140 non-null and 100 distinct. These are published
dependency fields, not FHIR resource columns and not integer identifiers.

## Oracle and served-data checks

The embedded preprocessing probe resolved the completed attempt plan above and
registered the three immediate dependency views under their unqualified stems.
The ICU/Patient/hospital projections returned 140 ICU Encounters, 275
hospital Encounters, and 100 Patients. Counts for the identity spine were:

```text
ICU resource key                 140/140 non-null, 140 distinct
ICU subject reference key        140/140 non-null
ICU partOf hospital reference    140/140 non-null
ICU stay identifier              140/140 non-null, 140 distinct
hospital admission identifier    275/275 non-null, 275 distinct
Patient identifier               100/100 non-null
ICU -> hospital hadm resolution  140/140
ICU -> Patient subject resolution 140/140
```

The identifier systems were exactly:

```text
ICU:  http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu   140/140
Hosp: http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp 275/275
Patient: http://mimic.mit.edu/fhir/mimic/identifier/patient     100/100
```

The read-only DuckDB comparison joined the FHIR-derived spine to
`mimiciv_icu.icustays` on `stay_id`: 140/140 rows joined; `subject_id`,
`hadm_id`, and `stay_id` were each 140/140 exact, and all three were exact on
140/140 rows. No resource key was parsed, regenerated, or used to infer a
clinical value.

The requested completed dependency values were compared after mapping each
published `icu_encounter_key` back to the probed ICU Encounter by opaque
equality and then joining the resulting stay identifier to DuckDB:

```text
first_day_bg_art.pco2_min:
  140/140 keyed rows, oracle non-null 76, candidate non-null 76, exact 140/140

first_day_vitalsign.temperature_min:
  oracle/candidate non-null 135/140, exact 140/140
first_day_vitalsign.temperature_max:
  oracle/candidate non-null 135/140, exact 140/140
first_day_vitalsign.heart_rate_max:
  oracle/candidate non-null 140/140, exact 140/140
first_day_vitalsign.resp_rate_max:
  oracle/candidate non-null 140/140, exact 140/140

first_day_lab.wbc_min:
  oracle/candidate non-null 139/140, exact 140/140
first_day_lab.wbc_max:
  oracle/candidate non-null 139/140, exact 140/140
first_day_lab.bands_max:
  oracle/candidate non-null 23/140, exact 140/140
```

These NULLs are populated aggregate NULLs on individual stays, not absent
FHIR schema fields. The source SIRS `CASE` expressions and final NULL-to-zero
sum must preserve their existing semantics.

## Codes and cardinality

The SIRS SQL names no `itemid`, ICD code, LOINC code, coding URI, or other
coded literal. Its literal code set is therefore **empty**. There is no
SIRS-side `forEach: "code.coding"`, so a SIRS coding-system probe and
codings-per-resource ratio are **not applicable** (`N/A`, not zero). Itemid
filters used by the completed upstream dependencies remain inside those
dependencies and were not reintroduced here.

## Gaps and dataset/ETL quirks

* **Hospital admission identifier is absent on the ICU Encounter's own
  identifier list but exactly derivable.** `partOf.getReferenceKey(Encounter)`
  joins to the hospital Encounter resource key, whose exact
  `encounter-hosp` identifier yields `hadm_id`. The demo bound is 140/140,
  with 140/140 exact oracle values. This uses only reference equality and
  identifier projection; it does not parse an ID. If a future served dataset
  omits a parent reference, the loss would be limited to `hadm_id` on those
  identifiable rows. SIRS uses `stay_id`, not `hadm_id`, for natural identity
  or dependency inclusion, so this is not an essential SIRS-score input in the
  checked warehouse.
* **Published dependency identifiers are stripped.** The attempt SQLs contain
  integer `subject_id`/`stay_id`, but preprocessing exposes the paired opaque
  `patient_key`/`icu_encounter_key` instead. This is the established export
  shape, not a missing FHIR field. Equality joins on `icu_encounter_key` are
  exact and preserve the SIRS stay association.
* **Known upstream chartevents DST normalization reaches one consumed
  dependency.** `first_day_vitalsign` attempt 0001 was accepted with its known
  upstream divergence: 72,998/73,181 rows identical and 183 conflicting rows;
  the full comparison listed 8 `heart_rate_max` conflicts and 11
  `resp_rate_max` conflicts, while `temperature_min` and `temperature_max`
  had no conflicts. The cause is the established
  `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` TIMESTAMPTZ
  normalization, with ICU-anchor effects from
  `mimic-fhir/sql/fhir_encounter_icu.sql:31,98`. The original wall time is not
  in FHIR and resource IDs are opaque. On those bounded dependency rows, a
  threshold crossing could propagate into `heart_rate_score`, `resp_score`,
  and `sirs`; SIRS has no timestamp from which to repair it. This is inherited
  upstream transformation behavior, not a new SIRS mapping or terminal
  decision.
* **No requested-value gap was measured for the other dependencies.** The
  current `first_day_bg_art` and `first_day_lab` full comparison artifacts are
  exact, and the requested demo fields were independently 140/140 exact. No
  typed NULL or ID side channel is appropriate for any requested field.

No new dataset-wide quirk was established, so
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sirs.md` was not created or modified.

## Notes and provisional fragments consulted

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

* the identifier spine: numeric MIMIC IDs come from `identifier.value` strings,
  while paired type-prefixed resource/reference keys are required output and
  join columns;
* resource/reference keys are opaque and may only be compared for equality;
* ICU/hospital/ED Encounter streams are separated by identifier system rather
  than `Encounter.class`, and ICU `partOf` is the hospital-admission link;
* the established datetime/DST ETL transformation is not recoverable from
  FHIR or an ID side channel; and
* Delta tables are authoritative over stale NDJSON and the HTTP server.

Provisional fragments read as leads were:

* `MIMIC_NOTES.d/README.md` — read and followed;
* `first_day_bg.md` — read; the labevents DST lead was not independently
  re-probed at raw Observation level in this SIRS run, while the completed
  `pco2_min` output was checked 140/140 against DuckDB;
* `first_day_vitalsign.md` — read; the completed dependency schema and values
  were checked, while its raw choice/exclusion claims were not re-probed as a
  new SIRS resource mapping;
* `complete_blood_count.md` and `blood_differential.md` — read; their raw
  comparator-text leads were not relevant to the already-produced SIRS fields,
  and the completed `first_day_lab` requested outputs were checked exactly;
* `chemistry.md` and `coagulation.md` — read as first-day-lab dependency leads;
  no chemistry/coagulation field is consumed by SIRS and no new claim was
  adopted; and
* `vitalsign.md` — read; its `issued` lead is irrelevant because SIRS consumes
  only completed aggregates, not `storetime`/`issued`.

There is no `MIMIC_NOTES.d/first_day_lab.md` or `MIMIC_NOTES.d/enzyme.md` in the
workspace. The dependency artifacts directly inspected included the
`first_day_bg_art`, `first_day_lab`, and `first_day_vitalsign` attempt-0001
ViewDefinitions, candidate SQL, full comparison artifacts, and FHIR-prober
evidence, plus the `vitalsign` attempt-0002 comparison/judge artifacts and the
completed dependency states. No fragment was appended by this probe.

## Carryover status

This reusable mapping is written at:

`mimic-iv/concepts_fhir/carryover/sirs/fhir-prober.md`

It must be recorded with:

```text
uv run mimic_utils carryover-record sirs --stage fhir-prober
```
