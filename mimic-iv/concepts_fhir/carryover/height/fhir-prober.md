# FHIR prober mapping: `height` (reopened, fresh probe)

**Concept:** `height`
**Canonical source:** `mimic-iv/concepts/measurement/height.sql`
**Source analysis:** `mimic-iv/concepts_fhir/carryover/height/source-analyst.md`
**Current immutable attempt:** `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0003`
**Probe date:** 2026-08-13
**Reopened instruction:** obeyed. The previous FHIR-prober carryover was
invalidated because it used `Observation.id`/UUID-v5 inversion as semantic
charttime recovery. This mapping does not parse, regenerate, brute-force,
hardcode, or otherwise use a resource/reference id to infer a source value.

## Authoritative data and structural references

- Served data: `/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with
  embedded Pathling 9.6.0 over Spark 4.0.2 via `EmbeddedExecutor`.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- Canonical ViewDefinition shape:
  `/Users/nau025/Documents/master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Curated dataset/IG rules: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- Source output shape from the analyst and full manifest: `(subject_id
  INTEGER, stay_id INTEGER, charttime TIMESTAMP, height DECIMAL(38,2))`,
  33,474 full rows, empirical comparison key `stay_id`.

The source table is read twice: both CTEs use
`mimiciv_icu.chartevents`. The source full outer join is on
`subject_id + charttime`, not `stay_id`; centimetres (`226730`) have
`COALESCE` precedence over inches (`226707`). Preserve those semantics.

## Resource mapping

| Source table/role | MIMIC-on-FHIR resource | FHIR stream/discriminator |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` | `code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` plus exact `code` `226707` or `226730`; do not use `meta.profile` |
| `chartevents.subject_id` spine | `Patient` | `Observation.subject` joins to `Patient.getResourceKey()`; emit the numeric MIMIC id from the patient identifier system |
| `chartevents.stay_id` spine | `Encounter` | `Observation.encounter` joins to the ICU `Encounter.getResourceKey()`; select the ICU stream using the `encounter-icu` identifier system and emit its identifier value |

`Observation.getResourceKey()` is an opaque resource identity column only. It
may be retained as `observation_id` for identity/provenance, but is not a
charttime, value, source-id, or de-identification side channel. No mapping in
this file uses it to recover `charttime`.

## Canonical ViewDefinition projections

These are mapping projections, not an implementation. Keep UUID/reference
aliases separate from numeric identifier aliases. Coded filtering belongs
inside the coding `forEach`.

### Observation (`height_observation`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_id" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(Quantity).system", "name": "quantity_system" },
    { "path": "(value).ofType(Quantity).code", "name": "quantity_code" }
  ]
}
```

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

The fresh choice probe also projected `(effective).ofType(instant)` as
`effective_instant` and `(effective).ofType(Period).start/end` as
`effective_period_start`/`effective_period_end`. For both target codes those
variants were 0/71, so the implementer should use the served
`effective.ofType(dateTime)` directly rather than coalescing an unused variant.
If it projects the variants for shape diagnostics, it must not coalesce a
native timestamp with the dateTime string before casting.

### Patient (`height_patient`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

### ICU Encounter (`height_encounter`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter this Encounter view/use to the exact ICU identifier system (equivalently
`stay_id_str IS NOT NULL`). `Encounter.class` is not a stream discriminator.

## Source-column to FHIRPath mapping and types

| Source column/output | Canonical `{path, name}` mapping | FHIR type | Served/materialized type and implementer target |
|---|---|---|---|
| `chartevents.subject_id` → `subject_id` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }`; Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` then `string` | UUID/reference and identifier aliases are string/VARCHAR. Cast `subject_id_str` to final `INTEGER`. |
| `chartevents.stay_id` → `stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }`; ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` then `string` | UUID/reference and identifier aliases are string/VARCHAR. Cast `stay_id_str` to final `INTEGER`; this is the full-manifest natural key. |
| `chartevents.itemid` | Coding forEach `{ "path": "code", "name": "item_code" }` with `{ "path": "system", "name": "item_system" }` | `Coding.code` (`code`) and `Coding.system` (`uri`) | Both are string/VARCHAR. Filter exact system first and exact string code second; never cast an unscoped code column because other Observation streams may carry nonnumeric LOINC codes. |
| `chartevents.charttime` → `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` | Pathling materializes this alias as string with an ISO offset. Cast the served value directly to `TIMESTAMP_NTZ`; do not parse as an instant and do not use `Observation.id` to alter it. Final target is `TIMESTAMP`. |
| `chartevents.valuenum` → numeric input | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` (`decimal`) | Raw `Observation.valueQuantity.value` is `decimal(32,6)`, but the materialized ViewDefinition alias is string/VARCHAR. Cast it to a numeric type before arithmetic. |
| `chartevents.valueuom` (not a source SQL output) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }`; optionally `{ "path": "(value).ofType(Quantity).code", "name": "quantity_code" }` | `Quantity.unit` (`string`), `Quantity.code` (`code`) | String/VARCHAR; served values are `Inch` for `226707` and `cm` for `226730`. This supports verification but is not a final height column. |
| `height` derived output | No single stored FHIR path; derive from `quantity_value` and `item_code` | derived `decimal` | `226707`: `ROUND(quantity * 2.54, 2)`; `226730`: `ROUND(quantity, 2)`. Final cast must be `DECIMAL(38,2)`, then retain strict `120 < height < 230`. |

The source's internal `height_orig`, `value`, `valueuom`, and `itemid` are not
final output columns. `hadm_id` is not used by this concept and has no required
mapping.

## Confirmed coding system and exact code set

The fresh embedded probe projected all `code.coding` entries first to establish
the system from served data, then applied the exact source literals. The target
system was the same for both codes:

`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`

| Source predicate | Served exact code | Served system | Served display | DuckDB source total | Source `valuenum` non-null | FHIR coding rows | Distinct FHIR resources | Codings/resource |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `itemid = 226707` | `"226707"` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Height` | 71 | 71 | 71 | 71 | 1.000 |
| `itemid = 226730` | `"226730"` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Height (cm)` | 71 | 71 | 71 | 71 | 1.000 |

For the combined filtered target, the coding ratio was **142 coding rows / 142
distinct Observation resources = 1.000**. The source also had `value` non-null
on 71/71 rows for each code; the source filter itself is on `valuenum IS NOT
NULL`. No target code was dead, and no alternate system was observed for either
lifted code. The exact `system + code` pair is the discriminator. The two codes
are distinct global `d_items.itemid` values in the chartevents system, so code
alone is sufficient after system filtering; `meta.profile` is deliberately not
used.

## Fresh population and join checks

All counts below came from the fresh embedded Pathling/Spark materializations
over the authoritative demo Delta unless marked DuckDB.

| Code | Total | `observation_id` | `encounter_id` | `patient_id` | `effective_datetime` | `effective_instant` | `effective_period_start` | `effective_period_end` | `quantity_value` | unit | quantity system | quantity code | item code/system/display |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `226707` | 71 | 71 | 71 | 71 | 71 | 0 | 0 | 0 | 71 | 71 | 71 | 71 | 71/71/71 |
| `226730` | 71 | 71 | 71 | 71 | 71 | 71 | 71 | 0 | 71 | 71 | 71 | 71 | 71/71/71 |

The authoritative raw schema has `effectiveDateTime` as a
string, `effectiveInstant` as a native timestamp, `effectivePeriod.start/end`
as strings, and Quantity value as `decimal(32,6)`.

Supporting spine counts:

- `Patient`: 100 total, 100 resource keys, 100 patient identifier values.
- `Encounter`: 637 total, 637 resource keys, 140 ICU identifier values (the
  other Encounter streams must not be used for this ICU concept).
- Target Observation joins: 142/142 subject identifiers and 142/142 ICU stay
  identifiers resolved; Observation patient reference equalled the ICU
  Encounter's Patient reference on 142/142.
- Target joined rows: 60 distinct subjects and 71 distinct ICU stays.
- Target joined fields had zero nulls for item code, identifiers, served
  effective dateTime, numeric Quantity value, unit, Quantity system/code, item
  system, and display.

## Oracle agreement and direct effective-time rule

Read-only DuckDB checks and the fresh served-data pandas comparison found:

- Source totals after `valuenum IS NOT NULL`: 71/71 per code; no duplicate
  `(itemid, subject_id, charttime)` groups (71 groups for 71 rows per code).
- Source/FHIR alignment on `(item_code, subject_id, stay_id, charttime)` after
  `CAST(effective_datetime AS TIMESTAMP_NTZ)`: **142/142**.
- Source `valuenum` versus numeric Quantity value: **142/142** agreement at the
  observed numeric precision.
- After the source conversion, centimetre precedence, full outer join on
  `subject_id + charttime`, and strict bounds: **69/69 exact full tuples**, with
  zero source-only or FHIR-only rows in the demo.
- The fresh demo direct cast produced no DST residual: all 142 effective wall
  times matched the DuckDB source at zero-second delta.

The cast must be direct `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` (or the
equivalent direct `CAST` when malformed values are not expected). Do not use an
offset-aware `to_timestamp`/`TIMESTAMP` conversion: it converts the de-identified
wall-clock value through the session timezone. Do not use `substr` if fractional
seconds/date-only shapes must remain supported.

## DST-gap residual for the comparator/judge

The prior full-data result in
`mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/comparison.full.json`
is the relevant full-data characterization: 33,474 candidate and oracle rows,
33,470 identical, and **4 `differing_conflict` rows on `charttime` only**. In
all four, subject, stay, and height agreed; the served effective value was
exactly one hour later than the source wall time (source 02:xx versus served
03:xx). There were no only-oracle rows, only-candidate rows, or row-count
difference. The samples are the four source/FHIR pairs recorded in that
comparison artifact.

The upstream ETL explanation is the `TIMESTAMPTZ` conversion at
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`: a nonexistent
America/New_York spring-forward 02:xx wall time is serialized as 03:xx. The
original source wall time is not representable from served FHIR
`effectiveDateTime` for those rows. The resource id is opaque and must not be
used to recover it. Carry this as the expected small datetime conflict for the
full comparator/judge; the prober neither accepts nor blocks the result.

This loss is potentially essential to the source derivation because
`charttime` is the source full-outer-join key between the cm and inch streams;
a shifted time can theoretically change stream matching, centimetre
precedence, grouping, or row inclusion. In the observed full height result it
changed only the four reported output timestamps, not row inclusion or height.
The judge should assess the whole-concept consequence rather than treating a
typed NULL or an id-based correction as an exact fix. No terminal
representability decision is made here.

## Gaps and representability

| Information | Classification | Evidence and consequence |
|---|---|---|
| Numeric `subject_id` | Absent but derivable exactly | `Patient.identifier` with the patient system supplied 100/100 values; target joins resolved 142/142. It is also used in the source join and is therefore essential, but the exact identifier spine recovers it. |
| Numeric `stay_id` | Absent but derivable exactly | ICU `Encounter.identifier` with the ICU system supplied 140 values and resolved all 142/142 target references. It is the manifest key and is essential; cast the string identifier to `INTEGER`. |
| Normalized `height` | Absent as one stored field but derivable exactly | Quantity value plus exact code/unit reproduced the source conversion, rounding, precedence, bounds, and 69/69 demo output. |
| Original source `charttime` in DST spring-forward gaps | Not representable for the affected rows | FHIR carries only the already-normalized `effectiveDateTime`; direct NTZ casting preserves 03:xx, not the discarded 02:xx. Resource/reference IDs are forbidden side channels, so no id inversion or candidate hashing is permitted. This can be essential because the source uses charttime as a stream join key; the full height evidence currently shows only 4 timestamp conflicts and no row/group divergence. |
| Source `height_orig`, `value`, `valueuom`, and `itemid` as final columns | Not a gap in the requested output | They are internal/source discriminator inputs and are not emitted by the canonical SQL. `itemid` and Quantity/unit remain available for deriving the requested height. |

## Notes and fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping decision:

- The identifier-spine entry requires `identifier.value`, not resource/reference
  keys, for `subject_id`/`stay_id`, and requires final integer casts.
- The opaque-id rule explicitly forbids parsing, regenerating, hashing, or
  hardcoded lookup of resource ids; this supersedes the previous carryover's
  UUID-based charttime proposal.
- The code-system entry requires exact `system + code`, records the chartevents
  system, and forbids `meta.profile` discrimination.
- The Quantity alias entry requires numeric casting of the materialized
  `Quantity.value` string.
- The datetime entry requires direct `TIMESTAMP_NTZ` wall-clock casting and
  documents the irrecoverable DST-gap normalization.
- The Encounter entry requires ICU identifier-system selection rather than
  `Encounter.class`.

I read **all** current fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`:
`README.md`, `arb.md`, `blood_differential.md`, `cardiac_marker.md`,
`chemistry.md`, `code_status.md`, `coagulation.md`,
`complete_blood_count.md`, `crrt.md`, `dobutamine.md`, `dopamine.md`,
`epinephrine.md`, `gcs.md`, `height.md`, `icp.md`, `icustay_detail.md`,
`invasive_line.md`, and `kdigo_creatinine.md`. Sibling fragments were treated
as provisional leads, not evidence; unrelated claims were not adopted without
verification. The relevant `height.md` effective-choice lead was verified by
the fresh probe. Its historical UUID-recovery entries were explicitly rejected
and not used.

No new dataset-wide quirk was found that is absent from curated
`MIMIC_NOTES.md`: the fresh probe reverified the already-curated code-system,
opaque-id, Quantity-alias, identifier-spine, and direct-NTZ/effective-choice
rules. Therefore no new section is appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/height.md` in this reopened run. The
existing height fragment remains append-only historical/provisional provenance;
this file is the replacement carryover mapping.

No ViewDefinition, concept SQL, attempt artifact, or git commit was authored or
modified.
