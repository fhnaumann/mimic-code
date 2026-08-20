# FHIR prober mapping: `first_day_height`

**Concept:** `first_day_height`  
**Attempt:** `attempt_0001`  
**Canonical source:** `mimic-iv/concepts/firstday/first_day_height.sql`  
**Dependency:** completed `height`, attempt `0004`,
`mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004`

## Probe basis

- Authoritative warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`,
  queried with embedded Pathling 9.6.0 on Spark 4.0.2.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- Canonical ViewDefinition shape:
  `/Users/nau025/Documents/master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Read first: `AGENTS.md`, curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`,
  `MIMIC_NOTES.d/height.md`, `weight_durations.md`, and `icustay_times.md`.
  The fragments were treated as provisional leads and checked against the
  warehouse; none was used as unverified evidence.
- Source carryover:
  `mimic-iv/concepts_fhir/carryover/first_day_height/source-analyst.md`.
- Completed dependency carryover and artifacts read:
  `mimic-iv/concepts_fhir/carryover/height/fhir-prober.md`,
  `height/source-analyst.md`, `height/carryover.json`, and attempt 0004's
  `ViewDefinition.height_{observation,patient,encounter}.json`, `concept.sql`,
  `comparison.full.json`, and stage evidence.

## Resource mapping

| Source role | MIMIC-on-FHIR resource | Required discriminator / join |
|---|---|---|
| `mimiciv_icu.icustays` stay spine, `stay_id`, `subject_id`, `intime` | ICU `Encounter` | `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; value is `stay_id` as a string; `subject.getReferenceKey(Patient)` is the patient join; `period.start` is the `intime` representation |
| `mimiciv_icu.icustays.subject_id` | `Patient` reached from ICU `Encounter.subject` | `Encounter.subject.getReferenceKey(Patient) = Patient.getResourceKey()`; patient identifier system `http://mimic.mit.edu/fhir/mimic/identifier/patient` carries `subject_id` as a string |
| completed `mimiciv_derived.height` | **Published derived dependency `height`**, not a new source table | Consume `FROM height`; join by `icu_encounter_key`; do not inline/rederive the dependency or join on a stripped `stay_id` |
| dependency's `mimiciv_icu.chartevents` streams | `Observation` | exact `code.coding.system` plus code `226707` or `226730`; system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`; never use `meta.profile` |

The target SQL has no coded filter of its own. The two itemids are required
only because the completed `height` dependency is the upstream specification.
The target joins every ICU stay, including stays with no matching height row,
and must retain those rows with a NULL aggregate.

## Canonical source-column to FHIRPath mapping

Resource/reference keys are opaque strings. They are valid for equality joins,
grouping and provenance only; they must not be parsed, regenerated, hashed,
hardcoded, or used to infer a source identifier or time.

### ICU Encounter

| Source column / use | Canonical `{path, name}` | FHIR type | Served/materialized type; target requirement |
|---|---|---|---|
| ICU Encounter resource identity / dependency join and required output key | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | resource key string | `STRING`/`VARCHAR`, type-prefixed `Encounter/<id>`; retain verbatim |
| `icustays.subject_id` reference spine | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` key | `STRING`/`VARCHAR`, type-prefixed `Patient/<id>`; equality-join to Patient or use directly as the required output key |
| `icustays.stay_id` / target natural key and output | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` string | `STRING`/`VARCHAR`; final SQL must cast to `INTEGER` for manifest `stay_id` |
| `icustays.intime` / window anchor | `{ "path": "period.start", "name": "period_start" }` | `Period.start` `dateTime` | materialized as ISO string with offset; cast directly to `TIMESTAMP_NTZ`, never an offset-aware `TIMESTAMP` conversion |

The ICU stream is selected by the identifier system, not by `Encounter.class`.
The demo has 637 Encounter resources: 275 hosp, 140 ICU and 222 ED. ICU
selection produced 140/140 non-null ICU identifier values, keys, patient
references, and period starts, with 140 distinct ICU Encounter keys.

### Patient

| Source column / use | Canonical `{path, name}` | FHIR type | Served/materialized type; target requirement |
|---|---|---|---|
| Patient resource identity / required output key | `{ "path": "getResourceKey()", "name": "patient_key" }` | resource key string | `STRING`/`VARCHAR`, type-prefixed `Patient/<id>`; retain verbatim |
| `icustays.subject_id` / target output and grouping value | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Identifier.value` string | `STRING`/`VARCHAR`; final SQL must cast to `INTEGER` for manifest `subject_id` |

The ICU Encounter `patient_key` joined to the Patient `patient_key` for 140/140
ICU Encounters. The height Observation subject and ICU Encounter patient
reference also agreed for 142/142 targeted Observations.

### Height dependency Observation inputs

These are the paths needed to reproduce the already-completed `height`
dependency if it is being probed or its mapping is audited. The implementer of
`first_day_height` must not rederive these rows; it consumes the completed
dependency boundary described below.

| Source column / use | Canonical `{path, name}` | FHIR type | Served/materialized type; target requirement |
|---|---|---|---|
| Observation identity (optional audit column) | `{ "path": "getResourceKey()", "name": "observation_key" }` | resource key string | `STRING`/`VARCHAR`; opaque only |
| `chartevents.stay_id` reference | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | `Reference(Encounter)` key | `STRING`/`VARCHAR`; equality-join to ICU `Encounter.getResourceKey()` |
| `chartevents.subject_id` reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` key | `STRING`/`VARCHAR`; equality-join to Patient / ICU Encounter patient key |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `effectiveDateTime` `dateTime` | materialized `STRING`/`VARCHAR` with an offset; cast directly to `TIMESTAMP_NTZ` |
| Optional choice diagnostic | `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | `instant` | materialized native `TIMESTAMP`; zero populated target rows, so do not coalesce it into the dateTime string |
| Optional choice diagnostic | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` `dateTime` | materialized `STRING`/`VARCHAR`; zero populated target rows |
| Optional choice diagnostic | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | `Period.end` `dateTime` | materialized `STRING`/`VARCHAR`; zero populated target rows |
| `chartevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal | ViewDefinition alias materializes as `STRING`/`VARCHAR`; cast to numeric before arithmetic. Raw `Observation.valueQuantity.value` is `DecimalType(32,6)` |
| `chartevents.valueuom` audit / unit check | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` string | `STRING`/`VARCHAR`; observed `Inch` for 226707 and `cm` for 226730 |
| Quantity UCUM/system audit | `{ "path": "(value).ofType(Quantity).system", "name": "quantity_system" }` | `uri` | `STRING`/`VARCHAR` |
| Quantity code audit | `{ "path": "(value).ofType(Quantity).code", "name": "quantity_code" }` | `code` | `STRING`/`VARCHAR` |
| `chartevents.itemid` | coding `forEach` `{ "path": "code", "name": "item_code" }` | `Coding.code` | `STRING`/`VARCHAR`; exact values are `'226707'` and `'226730'` |
| coding discriminator | coding `forEach` `{ "path": "system", "name": "item_system" }` | `Coding.system` URI | `STRING`/`VARCHAR`; constrain to the exact chartevents system inside `forEach` |
| dimension label (audit only) | coding `forEach` `{ "path": "display", "name": "item_display" }` | `Coding.display` string | `STRING`/`VARCHAR`; observed `Height` / `Height (cm)` |

The authorable coding group is:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='226707' or code='226730'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

The exact code-system and cardinality probe found:

| Source literal | Served system | code/display | FHIR coding rows | distinct resources | codings/resource |
|---|---|---:|---:|---:|---:|
| `itemid = 226707` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `226707` / `Height` | 71 | 71 | 1.000 |
| `itemid = 226730` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `226730` / `Height (cm)` | 71 | 71 | 1.000 |
| combined target | same | exact codes | 142 | 142 | **1.000** |

The DuckDB source had 71 non-NULL `valuenum` rows per code. No lifted code was
dead and no alternate system was observed. The discriminator is `system +
exact code`; code alone is safe only after the system restriction. Do not use
`meta.profile`.

## Completed dependency boundary

The completed height attempt 0004 emits compared columns plus the required
resource keys. The dependency preprocessing/export boundary applies
`strip_mimic_ids` and dropped the paired `subject_id` and `stay_id` columns
because `patient_key` and `icu_encounter_key` are present. A read-only embedded
execution of the completed dependency's SQL reproduced this published shape:

```text
height: charttime TIMESTAMP_NTZ,
        height DECIMAL(38,2),
        patient_key STRING,
        icu_encounter_key STRING
```

The demo published dependency had 69 rows, with 69/69 non-null values for all
four fields. It had **no published `subject_id` or `stay_id`**. Therefore the
`first_day_height` consumer must:

1. use `FROM height` and retain the completed dependency's centimetre values;
2. join `height.icu_encounter_key = icu_encounter.icu_encounter_key`;
3. use `height.charttime` for the inclusive window;
4. obtain final `stay_id` from the ICU Encounter identifier and final
   `subject_id` from the Patient identifier, casting both strings to `INTEGER`;
5. emit `patient_key` and `icu_encounter_key` alongside those manifest-facing
   identifiers.

Joining the published dependency on `stay_id` is invalid because that column is
not served at the dependency boundary. Rebuilding height from Observations is
also invalid: the completed dependency owns the source full outer merge on
`subject_id + charttime`, centimetre precedence, unit conversion, rounding and
strict `(120,230)` bounds. The dependency's resolved demo output agreed with
`mimiciv_derived.height` on 69/69 charttimes and 69/69 heights.

## Manifest outputs and natural grain

The full manifest requires:

- `subject_id INTEGER` — Patient identifier value, cast from `subject_id_str`;
- `stay_id INTEGER` — ICU Encounter identifier value, cast from `stay_id_str`;
- `height DECIMAL(38,2)` — `ROUND(AVG(height), 2)` over all dependency rows in
  the inclusive `[period.start - 6 hours, period.start + 1 day]` window;
- required key metadata columns `patient_key` and `icu_encounter_key`, emitted
  verbatim as resource/reference keys.

The manifest natural key is `stay_id`; the relational source grain is one row
per ICU stay. The left join is essential: a stay with no height measurement is
retained with a NULL aggregate. The demo FHIR reproduction produced 140 rows,
matching the 140-row DuckDB `first_day_height` oracle; all 140 keyed heights
matched exactly, including 74 NULL heights on both sides.

## Datetime, window, and representability findings

- `period.start` is the served representation of `icustays.intime`, but it is
  not a byte-for-byte raw source field in every full-data row. The curated
  Encounter/DST notes and `weight_durations.md` document upstream
  `TIMESTAMPTZ` normalization of ICU spring-forward-gap times. Direct
  `CAST(period_start AS TIMESTAMP_NTZ)` preserves the served wall clock and is
  the only safe cast; an offset-aware conversion changes all rows by the local
  timezone.
- In the authoritative demo, ICU `period.start` matched DuckDB `intime` on
  **140/140** rows. There were no source height rows exactly at either inclusive
  boundary. The source and FHIR-projected window joins each selected 66
  dependency rows, with **66/66 exact `(stay_id, charttime, height)` tuples**.
- The completed `height` full comparison found 2/33,474 dependency charttime
  conflicts, both the already-curated one-hour spring-forward transformation;
  the height value, row inclusion and natural grain remained equal. The
  `weight_durations` lead found 9 ICU admission-time DST shifts in its full
  selected population. These are upstream coverage/transformation effects, not
  reasons to parse resource IDs.

The discarded raw wall time is **not representable** on the affected DST-gap
rows: FHIR retains only the normalized `period.start` or `effectiveDateTime`,
and a genuine 03:xx value cannot be distinguished from a shifted 02:xx value
using a FHIR element. The loss is potentially essential here because the raw
`intime` and `charttime` values control membership in the 30-hour inclusive
window and therefore the per-stay average and NULL/non-NULL output. The demo
bound is 0 period-start discrepancies, 0 boundary rows, and 66/66 exact window
tuples; the first-day full-data boundary effect must be measured by the full
comparison. If a full run shows that an unidentifiable shift changes window
membership or the aggregate, the whole concept should be referred to the
equivalence judge for the essential-loss/blocking assessment. No terminal
decision is made by this prober.

Numeric identifiers are absent from FHIR's key/reference values but are exactly
derivable from the two identifier systems above. They are essential natural
key/grouping values, but this is not a gap after the identifier mappings and
casts are used. Resource IDs remain opaque and are not a permitted recovery
route for either identifiers or datetimes.

## Curated notes and fragment status

Curated entries that changed this mapping decision were:

- identifier spine: identifiers are strings, must be cast, and must be emitted
  with `patient_key` / `icu_encounter_key`;
- type-prefixed opaque resource/reference keys: equality joins only;
- ICU Encounter stream selection by `identifier.system`, not `class`;
- direct `TIMESTAMP_NTZ` datetime handling and intrinsic DST normalization;
- mixed choice and Quantity alias rules: project the relevant choice variants,
  cast dateTime strings and Quantity value strings before arithmetic;
- exact itemid coding-system rule and the prohibition on `meta.profile`.

The provisional leads `height.md`, `weight_durations.md`, and
`icustay_times.md` were all read. `height.md`'s effective-choice lead was
verified: both target codes use dateTime 71/71, while instant and Period
variants were 0/71 per code. Its historical UUID-v5 recovery suggestions were
rejected under the curated opaque-id rule. `weight_durations.md`'s ICU
period-start DST warning was consistent with the curated datetime notes; the
demo period probe was 140/140 exact. `icustay_times.md` concerns MIN/MAX
non-commutation and does not directly apply to this AVG, though its
transformed-time warning reinforces the window probe.

No dataset-wide quirk absent from curated `MIMIC_NOTES.md` was discovered, so
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_height.md` was not appended.
The findings above are concept-specific and belong in this carryover.

No ViewDefinition, candidate SQL, or attempt artifact was authored.
