# FHIR mapping: `kdigo_stages`

## Scope and authority

- Concept: `kdigo_stages` (`organfailure/kdigo_stages.sql`), DAG level 2.
- Source analysis checked: `mimic-iv/concepts_fhir/carryover/kdigo_stages/source-analyst.md`.
- Canonical SQL checked: `mimic-iv/concepts/organfailure/kdigo_stages.sql`.
- Authoritative FHIR warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`.
- Probe engine: embedded Pathling 9.6.0 on Spark 4.0.2. The HTTP Pathling server
  and raw NDJSON were not used.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- Canonical ViewDefinition structure checked:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- No attempt ViewDefinition or `concept.sql` was authored.

This prober maps only the direct non-derived inputs of `kdigo_stages`: the ICU
stay backbone (`icustays`), its subject/admission/stay identifiers, and
`intime`. The raw Observation mappings that created `kdigo_creatinine`,
`kdigo_uo`, and `crrt` belong to those completed dependencies and must not be
inlined or rederived in this consumer.

## Source table to FHIR resource mapping

| MIMIC source table/column | FHIR resource/stream | Role in `kdigo_stages` |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter` selected by ICU identifier system `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Driving relation; supplies ICU resource key, patient reference, parent hospital-admission reference, `stay_id`, and `intime`. |
| `icustays.subject_id` | ICU `Encounter.subject` reference → `Patient` identifier system `http://mimic.mit.edu/fhir/mimic/identifier/patient` | Numeric subject identifier is not on the ICU Encounter directly. Join the opaque patient reference key to `Patient.getResourceKey()`, then read `Patient.identifier.value`. |
| `icustays.hadm_id` | ICU `Encounter.partOf` reference → hospital `Encounter` selected by identifier system `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | Numeric admission identifier is not on the ICU Encounter directly. Join the opaque parent reference key to the hospital Encounter resource key, then read its hospital identifier value. |
| `icustays.stay_id` | ICU `Encounter.identifier` with system `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Direct identifier value; it is a FHIR string and must be cast to the target integer. |
| `icustays.intime` | ICU `Encounter.period.start` | Scalar FHIR `dateTime`, materialized as an offset-bearing string; cast directly to `TIMESTAMP_NTZ` for the UO admission test and smoothing order. |

The Encounter stream is selected by `identifier.system`, never by
`Encounter.class` or `meta.profile`. The unfiltered demo Encounter table has
637 resources; the system counts are hospital 275, ICU 140, and ED 222.

## Canonical ViewDefinition select/column mappings

These are mapping projections, not attempt artifacts. The flat ICU projection
keeps the identifier-system predicate inside the FHIRPath, so it does not
explode the identifier array. The aliases ending in `_str` are FHIR strings,
not finished integer outputs. The aliases ending in `_key` are opaque,
type-prefixed equality keys.

### ICU Encounter (`icustays`)

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "icu_encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
        { "path": "period.start", "name": "intime_datetime" }
      ]
    }
  ]
}
```

The equivalent identifier probe shape, when the system itself is needed as an
output column, is:

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    { "path": "system", "name": "stay_system" },
    { "path": "value", "name": "stay_id_str" }
  ]
}
```

### Patient (`subject_id` resolution)

```json
{
  "resource": "Patient",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "patient_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
      ]
    }
  ]
}
```

### Hospital Encounter (`hadm_id` resolution)

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "encounter_key" },
        { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
      ]
    }
  ]
}
```

The join spine is therefore:

```text
icu_encounter.parent_encounter_key
  = hospital_encounter.encounter_key

icu_encounter.patient_key
  = patient.patient_key
```

Both sides are the byte-identical type-prefixed Pathling key. The final SQL
must cast `subject_id_str`, `hadm_id_str`, and `stay_id_str` to `INTEGER`, while
emitting `patient_key`, `encounter_key`, and `icu_encounter_key` verbatim as
required downstream key columns. In particular, `parent_encounter_key` may be
used as the hospital `encounter_key` equality value, but `hadm_id` itself comes
from the hospital Encounter's identifier value.

## Source column → FHIRPath, FHIR type, and target type

| Source column | Canonical mapping `{path, name}` | FHIR / materialized type | Required target use |
|---|---|---|---|
| `icustays.subject_id` | ICU Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key is opaque `string` / `STRING`; `Identifier.value` is FHIR `string` / `STRING` | Equality-join on `patient_key`; `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`. Emit `patient_key` alongside it. |
| `icustays.hadm_id` | ICU Encounter `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` → hospital Encounter `{ "path": "getResourceKey()", "name": "encounter_key" }` and `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Reference(Encounter)`/resource keys are opaque `string` / `STRING`; `Identifier.value` is FHIR `string` / `STRING` | Equality-join parent key to hospital key; `CAST(hadm_id_str AS INTEGER)` → `hadm_id INTEGER`. Emit `encounter_key` alongside it. |
| `icustays.stay_id` | ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | FHIR `Identifier.value` `string` / `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`. Emit `icu_encounter_key` alongside it. |
| `icustays.intime` | ICU Encounter `{ "path": "period.start", "name": "intime_datetime" }` | FHIR `dateTime`, materialized offset-bearing `string` / `STRING` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)` for all arithmetic and comparisons. The target semantic type is `TIMESTAMP`; preserve the served wall clock and do not offset-convert it. |
| ICU Encounter resource identity | ICU Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque type-prefixed resource key `string` / `STRING` (`Encounter/<id>`) | Required key and equality join only; emit verbatim. |
| ICU Encounter subject reference | ICU Encounter `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque type-prefixed reference key `string` / `STRING` (`Patient/<id>`) | Required key and equality join/grouping only; emit verbatim. |
| ICU parent admission reference | ICU Encounter `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` | opaque type-prefixed reference key `string` / `STRING` (`Encounter/<id>`) | Equality join to hospital `encounter_key`; do not parse it. |

## Probe counts and exact agreement

The following counts are from fresh embedded Pathling/Spark projections over the
authoritative demo Delta. Every mapped field was counted as total rows versus
non-null rows.

| Projection/population | Total | Non-null / result |
|---|---:|---|
| ICU Encounter view, unfiltered | 637 | `icu_encounter_key` 637, `patient_key` 637, `intime_datetime` 637; `parent_encounter_key` 312; `stay_id_str` 140 |
| ICU Encounter view, `stay_id_str IS NOT NULL` | 140 | `icu_encounter_key` 140, `patient_key` 140, `parent_encounter_key` 140, `stay_id_str` 140, `intime_datetime` 140 |
| Hospital Encounter view, `hadm_id_str IS NOT NULL` | 275 | `encounter_key` 275, `hadm_id_str` 275 |
| Patient view | 100 | `patient_key` 100, `subject_id_str` 100 |
| ICU `parent_encounter_key` → hospital `encounter_key` | 140 | 140 equality matches |
| ICU `patient_key` → Patient `patient_key` | 140 | 140 equality matches |

Identifier-system probes over raw Delta `Encounter.identifier` produced:

| System | Identifier rows | Distinct resources | Codings/identifier rows per resource |
|---|---:|---:|---:|
| `.../identifier/encounter-hosp` | 275 | 275 | 1.000 |
| `.../identifier/encounter-icu` | 140 | 140 | 1.000 |

The ICU identifier projection therefore has no identifier fan-out. The
selected ICU rows also had `subject.identifier.value` 0/140 and
`partOf.identifier.value` 0/140 in the raw resource table: the referenced
Patient and hospital Encounter joins are required; there is no usable direct
identifier nested in either reference.

Read-only DuckDB agreement after the two opaque-key joins, sorted by `stay_id`:

```text
subject_id  140/140 exact
hadm_id     140/140 exact
stay_id     140/140 exact
intime wall 140/140 exact
```

All 140 ICU keys and patient/parent reference keys had the expected
type-prefixed shape (`Encounter/...` for ICU and parent keys, `Patient/...` for
patient keys). All 140 `intime_datetime` values were non-null and directly
parseable with the `TIMESTAMP_NTZ` cast.

## Datetime and direct-path limitations

`Encounter.period.start` is a scalar `dateTime` field, not a FHIR choice type.
There are no `effective.ofType(dateTime)`, `effective.ofType(Period)`, or
`effective.ofType(instant)` alternatives for this direct `intime` input, and
there is no need to coalesce datetime variants. Use `period.start` exactly as
shown. The `charttime` fields in this concept come from the already-completed
dependency views and are not direct FHIR inputs to `kdigo_stages`.

The served ICU Encounter period endpoint is an ETL-transformed value. The
upstream ICU Encounter SQL casts source wall times through `TIMESTAMPTZ` before
writing `period.start`; a source `02:xx` in the New York spring-forward gap can
therefore be served as `03:xx`. The original source wall time is not in any
FHIR element. In the authoritative demo, the direct `intime` comparison was
exact for 140/140 ICU stays and the demo had no affected endpoint. Full-data
dependency evidence independently found nine ICU-intime-derived residual
interval effects in `weight_durations`; that is a cross-concept bound, not a
`kdigo_stages` row count. The target-specific full reach must be measured by
the full comparator.

This loss is **not representable** on the rows where the upstream transform
has changed the source wall clock. It is potentially essential rather than a
typed-NULL branch: `intime` controls the UO stage's inclusive six-hour test and
the `DATETIME_DIFF(charttime, intime, SECOND)` order used by the six-hour
smoothed stage window. A changed endpoint can therefore change stage values or
carry-forward values. The affected row condition is identifiable only as an
upstream transformed ICU endpoint, not by a surviving source discriminator; do
not infer the original value from a resource id. The established contract's
known upstream-DST exception sends any resulting divergence to the full
comparator/equivalence judge; this prober does not block the concept or accept
the loss.

If the Patient or hospital parent reference is absent in another warehouse
variant, the corresponding numeric identifier is not recoverable exactly from
the ICU Encounter; retain the ICU row with a typed NULL rather than using a
patient/time heuristic. The authoritative demo bound is 0/140 for each join.

Resource and reference keys are opaque identity. They may be compared for
equality, grouped, and used for provenance, but they must not be parsed,
regenerated, hashed, hardcoded, or used to infer `subject_id`, `hadm_id`,
`stay_id`, `intime`, or any clinical value. `Resource.id` is also not a
substitute: it is the bare UUID, while `getResourceKey()` and
`getReferenceKey()` are the type-prefixed join forms.

## Consumption of completed dependencies

The source SQL names `cr`, `uo`, and `crrt` columns such as `stay_id`, but the
consumer side must use the published dependency shapes. The export step drops
an integer identifier when its paired resource key is also projected. The
published dependency schemas therefore retain the source-derived event values
and opaque keys, but not the redundant `stay_id`/`hadm_id` columns that are
replaced by those keys:

| Dependency table exposed to the consumer | Published columns needed by `kdigo_stages` | Published key columns | Required join to the ICU base |
|---|---|---|---|
| `kdigo_creatinine` | `charttime TIMESTAMP`, `creat_low_past_7day DOUBLE`, `creat_low_past_48hr DOUBLE`, `creat DOUBLE` | `icu_encounter_key`, `patient_key`, `encounter_key` | `cr.icu_encounter_key = e.icu_encounter_key`; align additionally on `cr.charttime`. |
| `kdigo_uo` | `charttime TIMESTAMP`, `weight DECIMAL(38,3)`, `uo_rt_6hr`, `uo_rt_12hr`, `uo_rt_24hr`, `uo_tm_6hr`, `uo_tm_12hr`, `uo_tm_24hr` | `icu_encounter_key`, `patient_key` | `uo.icu_encounter_key = e.icu_encounter_key`; use `e.intime` for the six-hour admission branch. |
| `crrt` | `charttime TIMESTAMP`, `crrt_mode VARCHAR` | `icu_encounter_key`, `patient_key` | `crrt.icu_encounter_key = e.icu_encounter_key`; apply the source `crrt_mode IS NOT NULL` predicate to the published column. |

The completed dependencies are candidate-side tables named exactly
`kdigo_creatinine`, `kdigo_uo`, and `crrt`. Use `FROM` those stems; do not read
raw `Observation`, `labevents`, `outputevents`, or `chartevents`, and do not
recreate the dependency windows or pivots.

The FHIR-safe equivalent of the source's `stay_id` joins is equality on the
opaque `icu_encounter_key`. The base ICU Encounter supplies the output
`stay_id_str`, `subject_id_str`, `hadm_id_str`, and the three required key
columns. Build the event axis as a `UNION DISTINCT` of
`(icu_encounter_key, charttime)` from the three published dependencies, then
left join each component back on that key and timestamp. This preserves the
source `(stay_id, charttime)` alignment without parsing an identifier. Use
`patient_key` for the source's subject-level smoothing partition; equality
grouping by the opaque Patient key is permitted and is not inference from the
key contents. Preserve the source left join from every ICU Encounter,
including the NULL-`charttime` fallback row.

The dependency-owned coded filters remain dependency-owned. In particular,
`kdigo_stages.sql` itself has no itemid, ICD, code-system, or enumerated coded
filter; its only inclusion predicate is the non-coded `crrt_mode IS NOT NULL`
condition on the completed `crrt` table. Do not add a raw FHIR coding
`forEach` to this consumer.

## Code-set confirmation

The direct `kdigo_stages` code set is empty: there are no literal coded filters
and no `code.coding` projection is needed. Consequently, there are no
per-code row counts and no coding-rows-per-resource ratio for this concept;
the applicable ratio is **N/A**, not an unmeasured code filter. The upstream
literal code sets belong to `kdigo_creatinine`, `kdigo_uo`/`urine_output`, and
`crrt`, and must not be duplicated in `kdigo_stages`.

## Notes and provisional fragments read

Established entries in `mimic-iv/concepts_fhir/MIMIC_NOTES.md` that changed
this mapping were:

- Delta tables, not stale NDJSON or the unavailable HTTP server, are the source
  of truth.
- MIMIC identifiers are `identifier.value` strings; numeric outputs require
  explicit casts, and each identifier output is accompanied by its opaque
  resource key.
- Resource/reference keys are type-prefixed opaque equality identities;
  `Resource.id` is not a key and no id side channel is permitted.
- Encounter streams are separated by `identifier.system`; `Encounter.class`
  does not discriminate hospital, ICU, and ED streams.
- FHIR datetimes carry offsets and must be parsed as MIMIC wall-clock values
  with `TIMESTAMP_NTZ`; the upstream DST-gap transformation is irrecoverable.
- The essential-loss policy requires any timing loss affecting a key, branch,
  or window to be reported rather than hidden with a heuristic.

The following provisional fragments were read as leads and checked where
applicable against the authoritative Delta, DuckDB oracle, or completed
attempt evidence:

- `MIMIC_NOTES.d/README.md` — append-only/provisional protocol; verified by
  following it.
- `MIMIC_NOTES.d/crrt.md` — chartevents cardinality, DST, and superseded UUID
  recovery; the key prohibition and timing lead were checked against the
  completed CRRT attempt, while raw CRRT Observation mapping is outside this
  consumer.
- `MIMIC_NOTES.d/kdigo_creatinine.md` — no served CodeSystem and labevents DST
  effects; the CodeSystem absence and dependency attempt evidence were checked,
  but no raw lab mapping was adopted here.
- `MIMIC_NOTES.d/kdigo_uo.md` — outputevents datetime and rolling-window DST
  leads; the dependency's completed published shape and full comparison were
  checked, but no raw output mapping was adopted here.
- `MIMIC_NOTES.d/urine_output.md` and `first_day_urine_output.md` —
  outputevents dateTime-only and DST leads; checked against the completed
  dependency evidence, not used as direct `kdigo_stages` inputs.
- `MIMIC_NOTES.d/weight_durations.md` and `first_day_weight.md` — ICU period
  endpoint/DST lead; checked against the completed `weight_durations`
  comparison and used only to bound the `intime` limitation.
- `MIMIC_NOTES.d/icustay_times.md` — aggregate DST lead; treated as a warning,
  not as a substitute for `Encounter.period.start`.
- `MIMIC_NOTES.d/icustay_detail.md` — ICU period/resource omission lead; the
  direct ICU identifier/reference paths were independently probed here.
- `MIMIC_NOTES.d/rrt.md` — chartevents timing/opaque-id lead; treated as
  unrelated to the direct ICU Encounter mapping.
- `MIMIC_NOTES.d/creatinine_baseline.md` — Encounter/Condition lead; its
  Condition-specific claim was not applicable.

No new dataset-wide quirk beyond the established notes was found. Therefore
no section was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/kdigo_stages.md`.
