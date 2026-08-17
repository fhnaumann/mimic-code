# FHIR Prober Mapping: `age` (demographics/age)

**Attempt:** `0003` (reopened)
**Probe date:** 2026-08-17
**Natural key:** `hadm_id` (the manifest also requires `patient_key` and `encounter_key`)
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, embedded Pathling 9.6.0 on Spark

## Resource identification and current probe results

The source tables map to two resources:

| Source table | FHIR resource/stream | Delta probe |
|---|---|---|
| `mimiciv_hosp.admissions` | `Encounter`, filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | 637 Encounter resources total; 275 hospital, 140 ICU, 222 ED. The hospital stream is 275/275 against the demo admissions table. |
| `mimiciv_hosp.patients` | `Patient` | 100 Patient resources, 100/100 with the patient identifier and `birthDate`. |

Every Delta `Encounter` has one identifier (637/637), one non-null
`subject.getReferenceKey(Patient)` (637/637), and one non-null `period.start`
(637/637). Every Delta `Patient` has one identifier (100/100), a non-null
`birthDate` (100/100), and one non-null resource key (100/100).

The exact identifier systems and counts are:

| Resource | `identifier.system` | identifier rows | distinct resources |
|---|---|---:|---:|
| `Encounter` | `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` | 222 | 222 |
| `Encounter` | `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | 275 | 275 |
| `Encounter` | `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | 140 | 140 |
| `Patient` | `http://mimic.mit.edu/fhir/mimic/identifier/patient` | 100 | 100 |

`Encounter.class` is not a stream discriminator. The hospital filter must be
the exact identifier system above. There are no coded filters in `age`, so
code-system/code counts and a codings-per-resource ratio are not applicable.

## Required ViewDefinition projections

These are the current canonical column groups. The `_str` names remain FHIR
`string`/Spark `STRING` until the final SQL casts them to the manifest types.
Resource keys are also Spark `STRING`/`VARCHAR`, with the required type prefix;
do not cast, strip, regenerate, or parse them.

### `Encounter` ViewDefinition

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "encounter_key"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str"},
    {"path": "period.start", "name": "period_start"}
  ]
}
```

| Path | Name | FHIR type | Materialized type | Population in current Delta |
|---|---|---|---|---:|
| `getResourceKey()` | `encounter_key` | string resource key | STRING | 637/637; 637 distinct; all `Encounter/<opaque-id>` |
| `subject.getReferenceKey(Patient)` | `patient_key` | Reference key string | STRING | 637/637; all `Patient/<opaque-id>`; joins exactly to Patient resource keys 637/637 |
| `identifier.where(system='.../encounter-hosp').value` | `hadm_id_str` | string | STRING | 275/637; 275 distinct hospital identifiers |
| `period.start` | `period_start` | `dateTime` | STRING | 637/637; ISO-8601 offset-bearing values such as `2180-05-06T22:23:00-04:00` |

The resource's own `getResourceKey()` is mandatory in addition to the
reference key. The final output must carry `e.encounter_key` beside the
integer `hadm_id`; `patient_key` is the join/reference key and is also carried
beside `subject_id` as required by the current manifest.

### `Patient` ViewDefinition

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "patient_key"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"},
    {"path": "birthDate", "name": "birth_date"}
  ]
}
```

| Path | Name | FHIR type | Materialized type | Population in current Delta |
|---|---|---|---|---:|
| `getResourceKey()` | `patient_key` | string resource key | STRING | 100/100; 100 distinct; all `Patient/<opaque-id>` |
| `identifier.where(system='.../identifier/patient').value` | `subject_id_str` | string | STRING | 100/100; exact patient identifier system |
| `birthDate` | `birth_date` | `date` | STRING | 100/100; ISO date values such as `2083-04-10` |

## Source-column mapping

| Source column/expression | Source table | Resource/path | Canonical `{path, name}` | FHIR/materialized type | Required final type/handling |
|---|---|---|---|---|---|
| `subject_id` | `admissions` | Encounter subject reference, joined to Patient | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | reference key string / STRING | Equality join only; emit `patient_key` unchanged and obtain the integer from Patient's identifier. |
| `subject_id` | `patients` | Patient identifier | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | string / STRING | `CAST(subject_id_str AS INTEGER)` → `subject_id`; demo identifier agreement 100/100. |
| `hadm_id` | `admissions` | Hospital Encounter identifier | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | string / STRING | Filter the Encounter stream by this system; `CAST(hadm_id_str AS INTEGER)` → `hadm_id`; demo agreement 275/275. |
| `admittime` | `admissions` | Hospital Encounter period | `{path: "period.start", name: "period_start"}` | `dateTime` / STRING | `TRY_CAST(period_start AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` `admittime`; demo wall-time agreement 275/275. |
| `anchor_age` | `patients` | No exact FHIR element | no FHIR path; emit `CAST(NULL AS SMALLINT)` as `anchor_age` | absent/not representable | `Patient.birthDate` does not carry the individual anchor age. Never estimate it or infer it from an opaque id. |
| `anchor_year` | `patients` | No exact FHIR element | no FHIR path; emit `CAST(NULL AS SMALLINT)` as `anchor_year` | absent/not representable | `min(year(Encounter.period.start))` is only an approximation and must not replace the source output. |
| `age` (computed) | derived | Encounter period + Patient birth date | no single FHIR path; `YEAR(CAST(period_start AS TIMESTAMP_NTZ)) - YEAR(CAST(birth_date AS DATE))` → `age` | BIGINT result | Best available FHIR derivation; demo exact 275/275, but full data has known intrinsic conflicts described below. |

The final SQL must emit `subject_id`, `hadm_id`, `admittime`, `anchor_age`,
`anchor_year`, `age`, `patient_key`, and `encounter_key`. The two integer
identifier columns are not resource keys: `identifier.value` is a string and
must be cast. The two key columns are uncast `Type/id` strings.

## Oracle and identity checks

The read-only demo DuckDB oracle contains 275 admissions and 100 patients;
source types are `INTEGER`, `INTEGER`, `TIMESTAMP`, `SMALLINT`, and `SMALLINT`
for `subject_id`, `hadm_id`, `admittime`, `anchor_age`, and `anchor_year`.
Checks against the materialized Delta views and that oracle were:

- hospital `hadm_id` identifier: **275/275 exact**;
- Patient `subject_id` identifier join: **100/100 exact**;
- Encounter subject reference key → Patient resource key: **637/637 exact** overall and **275/275** in the hospital stream;
- hospital `period.start` wall-clock prefix versus source `admittime`: **275/275 exact** on demo;
- demo `birthDate.year == anchor_year - anchor_age`: **100/100**, explicitly a demo-only result;
- `YEAR(period.start) - YEAR(birthDate)` versus canonical anchor-pair age: **275/275 exact** on demo.

The resource-key checks only compare keys for equality to join resources. They
do not parse or invert UUIDs and do not compare a guessed source value to an
id.

## Full-data representability and gaps

`Patient.birthDate` is not the source anchor pair. The upstream ETL writes it
from `MIN(transfers.intime) - anchor_age`, not from
`anchor_year - anchor_age`. Thus the pair `(anchor_age, anchor_year)` is
collapsed and neither individual source value is exactly recoverable from
FHIR. `anchor_year` can be approximated by the minimum year of the served
Encounter period starts, but it is not an identity; `anchor_age` is likewise
not recoverable as an exact source column. The proper output for both source
columns is a typed NULL, not a near-miss estimate.

This loss reaches the explicit `anchor_age` and `anchor_year` values on every
age row for which the oracle has those values (the full age oracle has
431,231 rows), but it does not change hospital-row inclusion or the natural
key `hadm_id`. The best representable age derivation is therefore still
`year(Encounter.period.start) - year(Patient.birthDate)`. The established
full-data check found 460/431,231 age rows differing from the canonical
anchor-pair age because of the upstream birthDate synthesis. This is a
bounded value conflict caused by the served transform; it is not recoverable
by a query and must not be repaired with resource-id inversion. It is evidence
for the eventual judge, not a prober-stage terminal decision.

`Encounter.period.start` itself is present, but the upstream ETL's
`TIMESTAMPTZ` cast irreversibly normalizes spring-forward-gap wall times; the
established full age run found 44/431,231 admission-time conflicts (+1 hour).
Use `TIMESTAMP_NTZ` to preserve the served wall value and do not attempt to
reverse the shift from an id. This timing transform does not remove the
Encounter or change the hospital discriminator.

No new dataset/IG-wide quirk was found in this re-probe: the relevant facts
are already in curated `MIMIC_NOTES.md` (identifier spine and opaque,
type-prefixed resource keys; hospital identifier-system discrimination;
offset-bearing datetimes; `Patient.birthDate` synthesis and anchor-pair
loss). No `MIMIC_NOTES.d/age.md` fragment was present, so none was appended.
