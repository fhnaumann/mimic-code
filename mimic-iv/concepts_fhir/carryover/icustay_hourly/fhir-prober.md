# FHIR prober mapping: `icustay_hourly`

**Probe date:** 2026-08-21  
**Attempt:** `0001`  
**Authoritative Delta:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone pinned to UTC  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/icustay_hourly/source-analyst.md`  
**Completed dependency:** `icustay_times`, state `COMPLETED_WITH_DIVERGENCE`, attempt `0003`

This is a mapping artifact only. No target ViewDefinition or `concept.sql` was
authored here. The target must consume `FROM icustay_times`; it must not inline
or rederive `icustay_times` from FHIR resources.

## Source and dependency boundary

The target source SQL reads `icustay_times.stay_id`, `intime_hr`, and
`outtime_hr`, then emits a generated hourly grid. The dependency's completed
attempt has the compared columns plus paired resource keys. The executor's
published-dependency strip removes an identifier when its paired key is
present:

```text
icustay_times (published):
  intime_hr          TIMESTAMP_NTZ
  outtime_hr         TIMESTAMP_NTZ
  patient_key        STRING       -- Patient/<opaque-id>
  encounter_key      STRING       -- hospital Encounter/<opaque-id>
  icu_encounter_key  STRING       -- ICU Encounter/<opaque-id>
```

`subject_id`, `hadm_id`, and `stay_id` are not published dependency columns.
The exact strip is `subject_id`, `hadm_id`, `stay_id`; it leaves the five
columns above. Therefore the target must join the published dependency's
`icu_encounter_key` to an ICU Encounter view to recover `stay_id_str` from the
ICU identifier. It must not join `icustay_times.stay_id`, because that column
does not exist at the dependency boundary.

The target's final required key columns are `icu_encounter_key` and
`patient_key`, emitted verbatim beside the compared output columns. They are
opaque equality keys, not numeric identifiers.

## Resource mapping

| MIMIC source / dependency field | FHIR resource and stream | Canonical mapping `{path, name}` | FHIR/served type | Target/dependency use |
|---|---|---|---|---|
| `icustays.stay_id` | ICU `Encounter`, selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` FHIR `string`, materialized `STRING` | Cast only in final target SQL to manifest `stay_id INTEGER`; this is the replacement for the stripped dependency `stay_id`. |
| ICU Encounter identity | ICU `Encounter` | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque resource key `STRING`, `Encounter/<id>` | Join to the published dependency and emit as required target key. Never parse or regenerate it. |
| `icustays.subject_id` | ICU `Encounter.subject` / `Patient` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` on ICU Encounter; Patient source projection `{ "path": "getResourceKey()", "name": "patient_key" }` plus `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` / resource key `STRING`; identifier value FHIR `string` | The completed dependency already publishes `patient_key`; pass it through. Numeric `subject_id` is not a target output. |
| `icustays.hadm_id` (dependency-only) | ICU Encounter `partOf` → hospital `Encounter` | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` on ICU Encounter; hospital key `{ "path": "getResourceKey()", "name": "encounter_key" }`; hospital identifier `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | reference/resource keys `STRING`; identifier value FHIR `string` | Needed by completed `icustay_times`; its `hadm_id` is stripped from the published dependency. `icustay_hourly` does not read it. |
| `chartevents.itemid = 220045` (dependency-only discriminator) | ICU chartevents `Observation` | coding group `{ "path": "code", "name": "item_code" }`, `{ "path": "system", "name": "item_system" }`, `{ "path": "display", "name": "item_display" }` inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code='220045')"` | `Coding.code/system/display` materialized `STRING` | Completed dependency owns the exact code filter; do not repeat it by rederiving the dependency in this target. |
| `chartevents.charttime` → dependency `intime_hr` / `outtime_hr` | ICU chartevents `Observation` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` lexical string with offset; materialized `STRING` | Completed dependency casts directly to `TIMESTAMP_NTZ` before `MIN`/`MAX`; target receives the published `TIMESTAMP_NTZ` endpoints and passes them through. |
| published `icustay_times.intime_hr` | Completed derived dependency, not a new FHIR resource | no new FHIR path; inherited dependency column `intime_hr` | published Spark `TIMESTAMP_NTZ`, nullable | Use directly as the target's aggregate start input. |
| published `icustay_times.outtime_hr` | Completed derived dependency, not a new FHIR resource | no new FHIR path; inherited dependency column `outtime_hr` | published Spark `TIMESTAMP_NTZ`, nullable | Use directly as the target's aggregate end input. |
| published `icustay_times.icu_encounter_key` | Completed dependency's ICU Encounter key | inherited `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque `STRING` | Join to the target ICU Encounter view and pass through as a required key. |
| published `icustay_times.patient_key` | Completed dependency's Patient reference key | inherited `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque `STRING` | Pass through as a required key. Equality only. |
| published `icustay_times.encounter_key` | Completed dependency's hospital Encounter key | inherited `{ "path": "getResourceKey()", "name": "encounter_key" }` | opaque `STRING` | Not read by `icustay_hourly`; do not emit solely for this target. |

The target-side ICU Encounter view should expose at least:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter the materialized ICU view with `stay_id_str IS NOT NULL`, not
`icu_encounter_key IS NOT NULL` and not `Encounter.class`. The unfiltered
Encounter table includes hospital, ICU, and ED streams.

## Target pass-through and generated output mapping

| Target output | Canonical mapping `{path, name}` or dependency source | FHIR/served type | Required final type / rule |
|---|---|---|---|
| `stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` from the ICU Encounter joined by `icustay_times.icu_encounter_key` | FHIR `string`, materialized `STRING` | `CAST(stay_id_str AS INTEGER)`; target manifest `INTEGER`. Do not use `getResourceKey()` as `stay_id`. |
| `hr` | generated from the source literal `GENERATE_ARRAY(-24, upper)` / `UNNEST`; no single FHIRPath | generated integer, Spark `BIGINT` | `BIGINT`; signed offset, inclusive from `-24` through the source upper bound. |
| `endtime` | generated from aligned published `icustay_times.intime_hr` plus `hr` hours; no single FHIRPath | generated wall-clock timestamp, Spark `TIMESTAMP_NTZ` | target manifest `TIMESTAMP`; preserve NTZ wall-clock semantics and do not cast through offset-aware `TIMESTAMP`. |
| `icu_encounter_key` | inherited `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` / published `icustay_times.icu_encounter_key` | opaque `STRING` | Emit verbatim as required key column. |
| `patient_key` | inherited `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` / published `icustay_times.patient_key` | opaque `STRING` | Emit verbatim as required key column. |

The source target grain is one generated row per `(stay_id, hr)` and its
manifest comparison key is `(stay_id, endtime)`. The dependency is one row
per ICU stay. A dependency row with null endpoints must not be replaced by an
Encounter-period heuristic; its generated hourly expansion remains empty under
the source array semantics.

Important temporal detail: BigQuery `DATETIME_DIFF(..., HOUR)` counts HOUR
boundaries after truncating both endpoints, and the source then applies `CEIL`
to that integer. Do not implement this as `ceil((outtime_hr-intime_hr) /
3600)` over fractional elapsed duration. On the demo, fractional-duration
ceiling produced 15,618 rows versus the oracle's 15,615; reproducing the
source boundary-count semantics produced 15,615/15,615 exact rows.

## Confirmed code and cardinality

The target SQL itself has no coded filter. Its required dependency has one
transitive literal, `mimiciv_icu.chartevents.itemid = 220045`, and the FHIR
discriminator is system plus exact code:

| source literal | observed system | code | display | coding rows | distinct resources | codings/resource |
|---:|---|---:|---|---:|---:|---:|
| `220045` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220045` | `Heart Rate` | 13,913 | 13,913 | **1.000** |

The all-chartevents-system probe was 668,862 coding rows over 668,862
resources, also **1.000**. The exact system plus code is the discriminator;
`meta.profile` is prohibited. The system is the chartevents system, not the
generic ICU `mimic-d-items` system. `d_items.itemid` is a global primary key
with one `linksto`, so exact code 220045 separates this stream; the completed
dependency owns that selection.

## Probe counts and oracle checks

All counts below came from embedded Pathling/Spark over the authoritative Delta
unless explicitly marked DuckDB:

- Published completed dependency `icustay_times`: **140 rows**; `intime_hr`
  140/140 non-null, `outtime_hr` 140/140, `patient_key` 140/140,
  `encounter_key` 140/140, `icu_encounter_key` 140/140; 140 distinct ICU keys.
- Dependency source-side FHIR spines: 637 unfiltered Encounter rows, 140 ICU
  identifier-selected rows, 275 hospital identifier-selected rows, and 100
  Patient rows. Selected ICU `stay_id_str`, ICU key, Patient reference key,
  and `partOf` are populated 140/140. ICU `period.start` and `period.end` are
  populated 140/140 on the selected ICU stream (637/637 across unfiltered
  Encounters).
- Heart-rate target Observation: **13,913 rows**; resource key, Patient
  reference, ICU Encounter reference, `effective_datetime`, code, system, and
  display are each **13,913/13,913** non-null. `effective_period_start`,
  `effective_period_end`, and `effective_instant` are each **0/13,913**.
  The target spans 140 ICU stays and 100 patients; all 13,913 Encounter
  references resolve to the selected ICU Encounter view.
- Read-only DuckDB source checks: 140 `icustays`; 13,913 HR chartevents over
  140 stays; HR `value`, `valuenum`, and `charttime` are each non-null
  13,913/13,913; source `icustay_times` is 140 rows with all five source
  columns non-null.
- Direct FHIR-to-oracle aggregate check, using only `stay_id` equality and
  effective wall time (no resource IDs): HR row count, `intime_hr`, and
  `outtime_hr` agreed **140/140**. ICU Encounter period start/end agreed with
  DuckDB `icustays.intime/outtime` **140/140** in the demo; these periods are
  not target inputs and must not replace HR Observation endpoints.
- Replayed target grid check against DuckDB demo oracle: **15,615/15,615**
  `(stay_id, hr, endtime)` tuples exact, with zero candidate-only or
  oracle-only rows, after applying the source HOUR-boundary `DATETIME_DIFF`
  semantics. The demo target has 15,615 rows; the full manifest has 7,799,814.

## DST and representability

The chartevents ETL casts source `charttime` through `TIMESTAMPTZ` before
writing `Observation.effectiveDateTime`
(`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`). The FHIR value is
therefore the normalized wall clock and is not an exact recovery of a source
spring-forward-gap time. In the current HR probe, source and FHIR time groups
had 13,913 source groups versus 13,911 FHIR groups; 13,909 groups had equal
multiplicity, with two source-only `02:00` groups and two FHIR `03:00` groups
carrying multiplicity two:

```text
stay 30932571: source 2116-03-08 02:00 -> FHIR 2116-03-08 03:00
stay 32128372: source 2137-03-10 02:00 -> FHIR 2137-03-10 03:00
```

The two source wall times are **not representable** by any allowed FHIR
mapping. `effectiveDateTime` contains only the normalized value; `issued` is
storetime, not charttime. A heuristic that subtracts an hour from every
03:00 value would also alter genuine 03:00 observations and is not an exact
mapping. Resource/reference IDs are opaque and must not be parsed, regenerated,
hashed, hardcoded, or used to recover the discarded time.

For this demo, the two transformations did not change the per-stay HR MIN/MAX:
the aggregate and generated grid were exact. The completed full dependency
comparison nevertheless found 8/73,181 `icustay_times` endpoint rows differing
(7 `intime_hr`, 1 `outtime_hr`) from the upstream transform/aggregate behavior.
For `icustay_hourly`, an affected endpoint can change `endtime`, row inclusion,
and the `(stay_id,endtime)` natural key, so the loss is potentially essential
on those affected stays. A generic essential-loss policy would recommend
whole-concept blocking; this is the documented upstream DST transformation
case, so the prober makes no terminal decision and the comparator/equivalence
judge must assess the full result. Do not hide it with an ID inversion or an
Encounter-period substitute.

The numeric identifiers are absent from resource keys but **absent and
derivable** from the exact `Identifier.value` paths and key equality joins:
`stay_id` from the ICU Encounter identifier, and the dependency's opaque keys
for joins. This is not a representation gap. No other source column affects
the target output; `subject_id` and `hadm_id` are dependency-only and are not
read by `icustay_hourly`.

## Notes and fragments consulted

Established `MIMIC_NOTES.md` entries that changed this mapping:

- Delta tables are authoritative over stale NDJSON: all counts came from
  embedded Delta, not the live server or raw NDJSON.
- MIMIC identifiers are `identifier.value` strings and must be emitted beside
  their paired opaque resource keys; this required `stay_id_str` plus
  `icu_encounter_key`, rather than using `getResourceKey()` as `stay_id`.
- `getResourceKey()` / `getReferenceKey()` are type-prefixed opaque identity;
  this forbade resource-ID recovery of DST charttimes.
- Encounter stream selection is by exact `identifier.system`; `Encounter.class`
  does not discriminate ICU/hospital/ED, so the target ICU view uses the
  `encounter-icu` system and `stay_id_str IS NOT NULL`.
- Itemid-derived Observation codes are verbatim and must use exact system plus
  code; this established the 220045 filter and its coding ratio.
- Observation profiles are warehouse-version dependent; `meta.profile` was
  not used.
- FHIR datetimes carry offsets and must be parsed directly to `TIMESTAMP_NTZ`
  before aggregation; a late plain `TIMESTAMP` cast or offset-aware conversion
  would corrupt wall-clock values.
- Essential source loss and opaque-ID policy require the DST behavior to reach
  the comparator/judge rather than being silently approximated.

Relevant provisional fragments read:

- `MIMIC_NOTES.d/README.md`: protocol only; verified.
- `MIMIC_NOTES.d/icustay_times.md`: the aggregate-DST lead was independently
  checked here for HR code counts, effective variants, and the 140/140 demo
  aggregate; its full-data 8-row claim was treated as provisional context and
  cross-checked against the completed dependency comparison artifact.
- `MIMIC_NOTES.d/icustay_detail.md`: ICU period/LOS lead; current probing
  verified only selected period population and demo 140/140 period equality,
  not the fragment's full-data LOS claim; period is not used by this target.
- `MIMIC_NOTES.d/first_day_vitalsign.md`: dateTime-only and global chartevents
  omission leads; dateTime-only behavior was independently confirmed for the
  13,913 HR rows and the HR source had no null values or target hard-coded
  tuple. The global claim was not adopted from the fragment.
- `MIMIC_NOTES.d/vitalsign.md`, `gcs.md`, `crrt.md`, `rrt.md`, `height.md`,
  `code_status.md`, `weight_durations.md`, and `rhythm.md`: read as
  chartevents/DST/opaque-ID leads. Their historical ID-reconstruction advice
  was not verified or used; the shared opaque-ID rule supersedes it.
- `MIMIC_NOTES.d/coagulation.md`, `chemistry.md`, `oxygen_delivery.md`, and
  `invasive_line.md`: read for datetime-choice and ICU-stream behavior; their
  non-HR findings were not transferred to this mapping.

## New provisional fragment finding

The current loop appended one dataset/ETL-level lead to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_hourly.md`: chartevents
effective-time normalization can collapse source wall-time groups before a
per-stay MIN/MAX. It is explicitly provisional and should be independently
rechecked before promotion to `MIMIC_NOTES.md`.
