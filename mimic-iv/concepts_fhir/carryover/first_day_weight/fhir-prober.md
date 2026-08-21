# FHIR prober mapping — `first_day_weight` (attempt 0001)

## Probe scope and authoritative sources

- Canonical target SQL: `mimic-iv/concepts/firstday/first_day_weight.sql`.
- Reusable source analysis: `mimic-iv/concepts_fhir/carryover/first_day_weight/source-analyst.md`.
- Completed dependency: `weight_durations`, current completed attempt 0003.  The
  dependency is consumed at its published boundary; it must not be rederived or
  joined by parsing a resource id.
- Authoritative FHIR data: `/Users/nau025/warehouses/mimic-iv-demo/delta`,
  queried with embedded Pathling 9.6.0 on Spark 4.0.2.  No HTTP Pathling server
  was used.
- Read-only relational oracle: `/Users/nau025/warehouses/mimic4-demo.db`
  (DuckDB 1.5.5).
- Canonical ViewDefinition structural reference:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- ETL checked: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:8-9,20-23,34-38,58-80`
  and `/Users/nau025/Documents/mimic-fhir/sql/fhir_encounter_icu.sql:30-32,44-46,77-100`.
- This is a mapping artifact only.  No candidate ViewDefinition or candidate
  SQL was authored here.

## Source table → FHIR resource mapping

| MIMIC-IV source relation | FHIR resource/stream | Mapping role |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter`, ICU stream selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | ICU stay identity, patient reference, and `intime`/`outtime` period endpoints. |
| `mimiciv_icu.chartevents` | `Observation`, ICU chartevents stream selected by the exact coding system and codes `226512`/`224639` | Weight item discriminator, Quantity value/unit, effective chart time, patient reference, and ICU Encounter reference. |
| `mimiciv_hosp.patients` (through served `Patient`) | `Patient` | `subject_id` is carried by the Patient identifier; the Patient resource key is the opaque equality join from ICU Encounter/Observation references. |
| `mimiciv_derived.weight_durations` | completed derived dependency `weight_durations` | Published dependency boundary supplies `starttime`, `weight_type`, and `weight`; it is not another FHIR resource to remap in this consumer. |

Encounter stream selection is by the ICU identifier system, not `Encounter.class`.
The demo has 275 hospital, 140 ICU, and 222 ED Encounter identifier rows; class
does not safely separate them.

## Canonical FHIR projections

These are mapping projections, not attempt artifacts.

### ICU Encounter (`icustays`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "period.start", "name": "intime_datetime" },
    { "path": "period.end", "name": "outtime_datetime" }
  ]
}
```

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    { "path": "system", "name": "stay_system" },
    { "path": "value", "name": "stay_id_str" }
  ]
}
```

`getResourceKey()` is the type-prefixed opaque Encounter identity and
`subject.getReferenceKey(Patient)` is the opaque Patient reference key.  The
relational `stay_id` is only `identifier.value`, not either resource key.
`period.start` is the source `intime` representation used by the dependency
lineage and `period.end` is the corresponding `outtime` representation.

### Patient (`subject_id`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" }
  ]
}
```

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient')",
  "column": [
    { "path": "system", "name": "subject_system" },
    { "path": "value", "name": "subject_id_str" }
  ]
}
```

The final `subject_id` is `CAST(subject_id_str AS INTEGER)`.  The demo join of
ICU Encounter → Patient matched all 140/140 ICU stays and the identifier value
matched the DuckDB `icustays.subject_id` on 140/140 rows.

### Observation (`chartevents`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" },
    { "path": "(value).ofType(string)", "name": "string_value" }
  ]
}
```

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='226512' or code='224639'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

The Observation reference keys join to the ICU Encounter resource key by exact
equality.  They are not `stay_id` or `subject_id`, and no resource id may be
parsed, regenerated, or used as a source-value side channel.

## Confirmed coding discriminator

The source/dependency code set is exactly the two source literals:

| source `chartevents.itemid` | FHIR `code.coding.system` | FHIR `code` | FHIR display | source rows | FHIR coding rows | FHIR resources | codings/resource |
|---:|---|---:|---|---:|---:|---:|---:|
| `226512` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `226512` | `Admission Weight (Kg)` | 129 | 129 | 129 | 1.000 |
| `224639` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `224639` | `Daily Weight` | 441 | 441 | 441 | 1.000 |
| **total** | | | | **570** | **570** | **570** | **1.000** |

The whole served chartevents system was 668,862 coding rows over 668,862
distinct Observation resources, also ratio 1.000.  The exact filter is
`system + code`, never `meta.profile`; the merged warehouse profile is not a
stable stream discriminator.  `d_items.itemid` is a global primary key and the
DuckDB dimension reports `linksto='chartevents'` for both codes, so these exact
codes identify this stream.

`226512` is exactly the `admit` branch and `224639` is exactly the `daily`
branch.  `weight_type` is therefore absent as a standalone FHIR element but is
derivable from the surviving code; it must not be inferred from display text.

## Confirmed populated choices, types, and transforms

The authoritative raw Delta schema reports `Observation.valueQuantity.value`
as `decimal(32,6)`, `Observation.effectiveDateTime` and
`Observation.effectivePeriod.start/end` as strings, `Observation.effectiveInstant`
as a native Spark timestamp, and `Patient.identifier.value` as string.  The
ViewDefinition aliases have these observed types:

| FHIR element / alias | FHIR type | materialized probe type | target use |
|---|---|---|---|
| `Observation.getResourceKey()` / `observation_key` | resource key string | `STRING` | identity only; not needed in the aggregate output |
| `Observation.subject.getReferenceKey(Patient)` / `patient_key` | `Reference(Patient)` key | `STRING` | opaque equality join and required additive output key |
| `Observation.encounter.getReferenceKey(Encounter)` / `encounter_key` | `Reference(Encounter)` key | `STRING` | opaque equality join to ICU Encounter |
| `Observation.effective.ofType(dateTime)` / `effective_datetime` | `dateTime` | offset-bearing `STRING` | selected target variant; cast directly to `TIMESTAMP_NTZ` before arithmetic |
| `Observation.effective.ofType(Period).start/end` / `effective_period_start/end` | `Period.start/end` | `STRING` | 0/570 target rows; project as typed-null variants, do not omit polymorphic choices in a reusable view |
| `Observation.effective.ofType(instant)` / `effective_instant` | `instant` | native Spark `TIMESTAMP` | 0/570 target rows; do not coalesce this native type with string variants before casting |
| `Observation.value.ofType(Quantity).value` / `quantity_value` | decimal | ViewDefinition alias `STRING`; raw Delta `decimal(32,6)` | cast numeric before dependency rounding; source/FHIR values agreed within 1e-6 on 570/570 |
| `Observation.value.ofType(Quantity).unit` / `quantity_unit` | string | `STRING` | `kg` on 570/570 and exact source unit match |
| `Observation.value.ofType(Quantity).comparator` / `quantity_comparator` | code | `STRING` | 0/570; no comparator branch for these numeric chartevents |
| `Observation.value.ofType(string)` / `string_value` | string | `STRING` | 0/570; numeric rows are Quantity, not valueString |
| coding `{path: "code", name: "item_code"}` | `Coding.code` | `STRING` | exact code discriminator |
| coding `{path: "system", name: "item_system"}` | `Coding.system` URI | `STRING` | exact system discriminator |
| coding `{path: "display", name: "item_display"}` | string | `STRING` | descriptive only; do not filter on it |
| ICU `Encounter.getResourceKey()` / `icu_encounter_key` | resource key string | `STRING` | opaque identity and required additive output key |
| ICU `Encounter.subject.getReferenceKey(Patient)` / `patient_key` | `Reference(Patient)` key | `STRING` | opaque equality join to Patient and required additive output key |
| ICU `Encounter.identifier...value` / `stay_id_str` | identifier string | `STRING` | final `CAST(... AS INTEGER)` gives `stay_id` |
| ICU `Encounter.period.start` / `intime_datetime` | `dateTime` | offset-bearing `STRING` | cast directly to `TIMESTAMP_NTZ` before the +1 day gate or two-hour lineage arithmetic |
| ICU `Encounter.period.end` / `outtime_datetime` | `dateTime` | offset-bearing `STRING` | used upstream by the completed dependency's terminal interval fallback; not read by the target consumer itself |
| Patient `getResourceKey()` / `patient_key` | resource key string | `STRING` | opaque equality join |
| Patient `identifier...value` / `subject_id_str` | identifier string | `STRING` | final `CAST(... AS INTEGER)` gives `subject_id` |

Do not use `CAST(... AS TIMESTAMP)` or offset-aware parsing for these de-identified
wall-clock datetimes.  The established warehouse rule is
`CAST(string_alias AS TIMESTAMP_NTZ)`, and each string choice must be cast before
any `COALESCE` with another choice.

## Completed `weight_durations` dependency boundary

The current completed attempt 0003 candidate has source-attempt columns
`stay_id`, `starttime`, `endtime`, `weight`, `weight_type`,
`icu_encounter_key`, and `patient_key`.  The runner applies the published-shape
identifier strip before registering a dependency.  Because `stay_id` is paired
with `icu_encounter_key`, the published `FROM weight_durations` boundary is:

| published dependency column | type | use in `first_day_weight` |
|---|---|---|
| `starttime` | `TIMESTAMP` | inclusive target predicate `ce.starttime <= intime + 1 day` |
| `endtime` | `TIMESTAMP` | available but not read by the target |
| `weight` | `DECIMAL(38,3)` | inputs to all four aggregates |
| `weight_type` | `VARCHAR` | exact conditional branch `weight_type = 'admit'` |
| `icu_encounter_key` | opaque `STRING` | join to the ICU Encounter key; use this, not an identifier join |
| `patient_key` | opaque `STRING` | required dependency identity key; preserve equality/provenance |

`stay_id` is **not** available in the published dependency view after the
strip.  The consumer must obtain `stay_id` from the ICU Encounter identifier,
obtain `subject_id` from the Patient identifier, and join the dependency on
`ce.icu_encounter_key = e.icu_encounter_key`.  This is an opaque equality join,
not reconstruction or parsing of an id.  The dependency's own canonical
mapping matched 570/570 selected source/FHIR weight events and replayed its
derived interval multiset 578/578 on demo data; DuckDB reports 578 dependency
rows, 137 distinct stays, 129 `admit` rows, and 449 `daily` rows in the demo.

## Source column → FHIRPath mapping and final target types

| source column / derived field | canonical mapping `{path, name}` | FHIR/materialized type | final `first_day_weight` type / note |
|---|---|---|---|
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` on ICU Encounter | FHIR `string`, `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; group key |
| `icustays.subject_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` on Patient, joined from `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | FHIR `string`, `STRING` | `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; group key |
| ICU Encounter resource identity | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque type-prefixed `STRING` | required additive `icu_encounter_key`; emit verbatim |
| Patient resource identity | `{ "path": "getResourceKey()", "name": "patient_key" }` | opaque type-prefixed `STRING` | required additive `patient_key`; emit verbatim |
| `chartevents.stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` → `stay_id_str` identifier | opaque reference/resource `STRING` then identifier `STRING` | equality join only; final integer comes from Encounter identifier |
| `chartevents.itemid` | coding `{ "path": "code", "name": "item_code" }` inside the constrained coding group | `Coding.code` string, `STRING` | `226512 → 'admit'`; `224639 → 'daily'` |
| code system | coding `{ "path": "system", "name": "item_system" }` | URI string, `STRING` | constrain to exact chartevents system before code cast |
| code display | coding `{ "path": "display", "name": "item_display" }` | string, `STRING` | informational only |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` string | dependency lineage `charttime`; cast to `TIMESTAMP_NTZ` |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | `dateTime` string | target one-day upper bound; cast to `TIMESTAMP_NTZ` |
| `chartevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | FHIR decimal; alias `STRING`, raw decimal(32,6) | dependency rounds to `DECIMAL(38,3)` `weight` |
| `chartevents.valueuom` | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | FHIR string, `STRING` | `kg`; ancillary to this target |
| dependency `weight_durations.starttime` | no new FHIR path at consumer boundary | `TIMESTAMP` | target join predicate; already derived/published by completed dependency |
| dependency `weight_durations.weight_type` | no new FHIR path at consumer boundary; upstream code-derived | `VARCHAR` | exact `'admit'` CASE branch; not a coded FHIR field |
| dependency `weight_durations.weight` | no new FHIR path at consumer boundary; upstream Quantity-derived | `DECIMAL(38,3)` | aggregate input |
| `weight_admit` | aggregate over dependency `weight` where `weight_type='admit'` | SQL aggregate | `DOUBLE`, nullable |
| `weight` | aggregate `AVG(ce.weight)` | SQL aggregate | `DOUBLE`, nullable |
| `weight_min` | aggregate `MIN(ce.weight)` | SQL aggregate | `DECIMAL(38,3)`, nullable |
| `weight_max` | aggregate `MAX(ce.weight)` | SQL aggregate | `DECIMAL(38,3)`, nullable |

The final output manifest requires `subject_id INTEGER`, `stay_id INTEGER`,
`weight_admit DOUBLE`, `weight DOUBLE`, `weight_min DECIMAL(38,3)`, and
`weight_max DECIMAL(38,3)`, plus the required additive opaque keys
`icu_encounter_key` and `patient_key`.

## Coverage, omissions, and representability

### Confirmed target coverage

- The target FHIR projection had 570/570 rows: 129 code `226512` and 441
  code `224639`.
- `observation_key`, `patient_key`, `encounter_key`, dateTime effective time,
  Quantity value, and unit were populated 570/570.  Period start/end,
  instant, Quantity comparator, and string value were 0/570 by design of this
  numeric target.
- Opaque Observation-reference → ICU-Encounter and Observation → Patient joins
  matched 570/570.  There were 137 distinct stays, not 570 unique stays.
- The source filter over the demo oracle had 570 rows, with `value` NULL 0/570,
  `valuenum` NULL 0/570, and the positive `<1500` dependency range 570/570.
  The global hard-coded ETL tuple `(34934165, 2151-10-03 05:14:00)` had zero
  source rows.  Thus the global chartevents omission predicates caused no loss
  for these demo itemids.
- A DuckDB/FHIR equality join on `(stay_id, itemid, charttime)` matched
  570/570 rows; Quantity values agreed within `1e-6` on 570/570 and units were
  exact on 570/570.
- ICU Encounter → Patient mapping had 140/140 stay-id joins, 140/140 subject
  identifier matches, and direct `period.start`/`period.end` agreement with
  DuckDB `intime`/`outtime` on 140/140 each.  The demo source had seven
  `intime` values and three `outtime` values in hour 02, but none was a
  New-York spring-forward gap; this explains why demo direct agreement does
  not disprove the full-data DST lead.

### Gaps and transforms

1. **`weight_type` is absent but derivable, not a representation gap.**  The
   exact surviving system+code discriminator identifies `admit` versus `daily`.

2. **Dependency `starttime`/`endtime` are absent as single FHIR interval fields
   but derivable/published.**  The completed `weight_durations` dependency
   provides the columns at its registered boundary.  It preserves `UNION ALL`
   multiplicity and the target only consumes `starttime`, `weight_type`, and
   `weight`; `endtime` is not used by `first_day_weight`.

3. **Chartevents pre-ETL wall `charttime` is not representable on a
   spring-forward-gap row.**  The ETL casts through `TIMESTAMPTZ` at
   `fhir_observation_chartevents.sql:9,67` before writing
   `Observation.effectiveDateTime`.  The original 02:xx wall time is not in a
   FHIR element.  It is essential to the upstream dependency's row ordering,
   `LEAD`, and interval construction, but this target consumes the already
   completed dependency rather than rederiving it.  Demo exposure was 0/570
   gap rows; the completed `weight_durations` full comparison reports eight
   chartevents/`LEAD` residual effects.  Do not recover it from an opaque
   Observation id.

4. **Pre-ETL ICU `intime`/`outtime` wall values are not representable on
   spring-forward-gap rows.**  The ICU ETL casts endpoints through
   `TIMESTAMPTZ` at `fhir_encounter_icu.sql:31-32,97-100` and writes only the
   transformed values to `Encounter.period`.  Demo exposure was 0/140 gap
   `intime` rows and direct endpoint agreement was 140/140.  The completed
   `weight_durations` full diagnosis independently reports nine selected
   ICU-intime-derived residual `starttime` effects among 272,445 dependency
   rows: subtracting two hours can move the final value out of the visible
   02:xx→03:xx pattern.  In `first_day_weight`, `intime` also controls the
   inclusive `starttime <= intime + 1 day` inclusion gate, so an affected row
   can propagate to the four aggregates.  This is the established upstream
   New-York DST transformation exception; no whole-concept block or id-based
   recovery is justified by this probe, and the full comparator/judge must
   assess any affected rows.  The original wall time remains unrecoverable by
   allowed FHIR queries.

5. **Global chartevents omissions are not representable on an omitted row.**
   `value IS NOT NULL` and the hard-coded tuple exclusion happen before the
   Observation exists.  For this target they reached 0/570 rows in the demo,
   and the completed dependency's full result diverged only in the documented
   DST effects, not an omission.  If a future full target row were omitted,
   it could affect source ranking/interval inclusion and must be reported as a
   row-level coverage loss rather than replaced with a fabricated value.

## Notes and provisional fragments read

Curated `MIMIC_NOTES.md` decisions used here were: Delta rather than stale
NDJSON is authoritative; identifiers come from `identifier.value` strings;
resource/reference keys are type-prefixed opaque equality keys; Encounter
streams use identifier systems rather than class; itemids are verbatim and
filtered by system plus exact code rather than profile; choice fields need one
alias per variant; Quantity aliases materialize as strings; FHIR datetimes must
be cast to `TIMESTAMP_NTZ`; and upstream chartevents/Encounter datetime casts
can irreversibly normalize DST-gap wall times.

I read every current `MIMIC_NOTES.d` fragment: `README.md`, `weight_durations.md`,
`dobutamine.md`, `crrt.md`, `charlson.md`, `oxygen_delivery.md`, `icp.md`,
`complete_blood_count.md`, `coagulation.md`, `norepinephrine.md`,
`neuroblock.md`, `gcs.md`, `height.md`, `vitalsign.md`, `icustay_times.md`,
`phenylephrine.md`, `first_day_bg.md`, `milrinone.md`, `epinephrine.md`,
`icustay_detail.md`, `rhythm.md`, `invasive_line.md`, `arb.md`, `rrt.md`,
`ventilator_setting.md`, `first_day_urine_output.md`, `cardiac_marker.md`,
`kdigo_creatinine.md`, `vasopressin.md`, `creatinine_baseline.md`,
`blood_differential.md`, `dopamine.md`, `code_status.md`, `chemistry.md`, and
`urine_output.md`.  The relevant chartevents/ICU Encounter leads from
`weight_durations.md` were checked against the fresh demo Delta probe, ETL
SQL, and the completed dependency's full comparison artifacts.  The unrelated
medication, laboratory, outputevents, and other resource-specific claims were
read but not substituted into this mapping.

The owned fragment
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_weight.md` records the two
dataset-wide ETL findings confirmed during this probe.  `MIMIC_NOTES.md` was
not edited.
