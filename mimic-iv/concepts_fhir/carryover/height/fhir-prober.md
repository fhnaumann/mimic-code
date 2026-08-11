# Corrected FHIR prober mapping: `height`

## Scope and authoritative sources

- **Concept:** `height`.
- **Source analysis:** `mimic-iv/concepts_fhir/carryover/height/source-analyst.md`.
- **Canonical source table:** `mimiciv_icu.chartevents`, read twice by
  `mimic-iv/concepts/measurement/height.sql`.
- **FHIR resource:** `Observation`, specifically the
  `mimic-observation-chartevents` stream. `Patient` and ICU `Encounter` are
  supporting identifier-spine resources used to recover the source numeric
  identifiers.
- **Authoritative probe warehouse:**
  `/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded
  Pathling 9.6.0 / Spark 4.0.2.
- **Read-only demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`.
- **Source output shape:**
  `(subject_id INTEGER, stay_id INTEGER, charttime TIMESTAMP,
  height DECIMAL(38,2))`; the full oracle has 33,474 rows and empirical key
  `stay_id`.

The previous probe incorrectly treated the normalized FHIR effective time as
the only possible charttime. The chartevents ETL preserves the original
pre-`TIMESTAMPTZ` charttime in the UUIDv5 Observation id. The corrected mapping
therefore retains `getResourceKey()` and recovers the original charttime by an
exact UUID witness before reproducing the source full outer join.

## Canonical ViewDefinition projections

Use these names for the canonical mapping. An implementer may use an internal
`*_key` alias, but the key must remain a UUID/string join column and must not be
emitted as `subject_id` or `stay_id`.

### Observation (`height_observation`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_id" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(Quantity).system", "name": "quantity_system" },
    { "path": "(value).ofType(Quantity).code", "name": "quantity_code" }
  ]
}
```

The coding group must be constrained inside `forEach`, not filtered by
`meta.profile` and not cast before the system filter:

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

The four effective projections were probed even though only dateTime is
populated for these target rows. Projecting the unused variants makes the
choice behavior explicit and prevents a silent loss if a warehouse variant
changes.

### Patient (`height_patient`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_id" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

### ICU Encounter (`height_encounter`)

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_id" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter the Encounter view or its use with the exact ICU identifier system (or
`stay_id_str IS NOT NULL`). `Encounter.class` is not a stream discriminator.

## Source table to resource mapping

| Source table | FHIR resource | Role |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` | One chartevents Observation per served source row, subject to the upstream ETL's non-null-value and hard-coded duplicate exclusion. |
| FHIR `Patient` identifier spine | `Patient` | Resolves `Observation.subject` UUID to `subject_id_str`. |
| FHIR ICU `Encounter` identifier spine | `Encounter` | Resolves `Observation.encounter` UUID to `stay_id_str`. |

## Source column to FHIRPath mapping and types

| Source column / output | Canonical `{path, name}` mapping | FHIR type | Served/materialized type and target requirement |
|---|---|---|---|
| `chartevents.subject_id` → `subject_id` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }`; Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` then `string` | Both materialize as `VARCHAR`/string UUID values; cast `subject_id_str` to final `INTEGER`. |
| `chartevents.stay_id` → `stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }`; ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` then `string` | UUID/reference and identifier are `VARCHAR`; cast `stay_id_str` to final `INTEGER`. |
| `chartevents.charttime` → `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` plus the UUID-v5 correction below | `dateTime` | Alias is `VARCHAR`/string with an ISO offset. Cast directly to `TIMESTAMP_NTZ`; do not parse as an instant. The exact pre-normalization time is selected by the Observation.id witness. |
| `chartevents.valuenum` → numeric input | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` (`decimal`) | Raw Delta field is `decimal(32,6)` but the ViewDefinition alias is `VARCHAR`/string. Cast the alias to numeric for arithmetic. Preserve the uncast string for UUID matching. |
| `chartevents.valueuom` → unit input | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` (`string`) | `VARCHAR`; `Inch` for 226707 and `cm` for 226730. |
| `chartevents.valueuom` → unit code input | `{ "path": "(value).ofType(Quantity).code", "name": "quantity_code" }` | `Quantity.code` (`code`) | `VARCHAR`; same observed values as `quantity_unit` for both target codes. |
| Quantity unit system | `{ "path": "(value).ofType(Quantity).system", "name": "quantity_system" }` | `Quantity.system` (`uri`) | `VARCHAR`; observed as `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units`. |
| `chartevents.itemid` | Coding `forEach` `{ "path": "code", "name": "item_code" }` | `Coding.code` (`code`) | `VARCHAR` string. Filter exact string code after exact system filtering, then cast if an integer is needed. |
| Item dimension label | Coding `forEach` `{ "path": "display", "name": "item_display" }` | `Coding.display` (`string`) | `VARCHAR`; display is not a discriminator. |
| Item coding system | Coding `forEach` `{ "path": "system", "name": "item_system" }` | `Coding.system` (`uri`) | `VARCHAR`; exact chartevents system below. |
| `chartevents.value` (ETL identity input, not a canonical height output) | No independent final output path; for the numeric target rows it is serialized by the ETL as the Quantity value and is represented by `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | source `string`; FHIR `Quantity.value` is `decimal` | For all 142 demo target rows, the served Quantity alias string exactly equaled DuckDB `CAST(value AS VARCHAR)`. Use that alias string, not a re-formatted numeric, in the UUID witness. |
| Final `height` | No single stored path; derive from `quantity_value` and `item_code` | derived numeric | `226707`: `ROUND(quantity_value * 2.54, 2)`; `226730`: `ROUND(quantity_value, 2)`; retain only strict `120 < height < 230`; cast final output to `DECIMAL(38,2)`. |

The source SQL does not output `itemid`, `value`, `valueuom`, or `height_orig`.
The `value` mapping above is required only because the upstream ETL used it in
the opaque Observation identity. No `hadm_id` mapping is needed: it is not a
source output and is not carried by this height result.

## Confirmed code set and discriminator

The source literals are exactly `226707` and `226730`; no translation or
terminology expansion is performed.

| Source predicate | Served code | Served system | Display | Demo source rows (`total`, `valuenum` non-null, `value` non-null) | FHIR coding rows | Distinct resources | Codings/resource |
|---|---:|---|---|---:|---:|---:|---:|
| `itemid = 226707` | `"226707"` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Height` | `71, 71, 71` | 71 | 71 | `1.000` |
| `itemid = 226730` | `"226730"` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `Height (cm)` | `71, 71, 71` | 71 | 71 | `1.000` |

The embedded Pathling projection of `code.coding` found no other system for
either lifted code and no lifted code was dead in the served target. A fresh
embedded `src.read('CodeSystem')` probe raised `No data found for resource
type: CodeSystem` in this Delta warehouse, so code presence is established
from the actual Observation codings, not from a terminology resource. The
discriminator is exact `item_system + item_code`;
`meta.profile` is deliberately not used because merged warehouse variants can
collapse subtype profiles.

## Probe counts: total versus non-null

All counts in this section are embedded Pathling/Spark counts over the
authoritative demo Delta unless marked DuckDB.

| Target code | Total rows | `observation_id` | `encounter_id` | `patient_id` | `effective_datetime` | `effective_instant` | `effective_period_start` | `effective_period_end` | `quantity_value` | `quantity_unit` | `quantity_system` | `quantity_code` | `item_code/system/display` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `226707` | 71 | 71 | 71 | 71 | 71 | 0 | 0 | 0 | 71 | 71 | 71 | 71 | 71/71/71 |
| `226730` | 71 | 71 | 71 | 71 | 71 | 0 | 0 | 0 | 71 | 71 | 71 | 71 | 71/71/71 |

For supporting resources, `Patient` had 100 total, 100 resource keys and
100/100 patient identifier values; `Encounter` had 637 total, 637 resource
keys and Patient references, 140 ICU identifier values, and 275 hospital
identifier values. Among the 142 target Observations, the Patient and ICU
Encounter joins each resolved 142/142, and the Encounter's Patient reference
matched the Observation Patient reference 142/142. There were 60 distinct
subjects and 71 distinct ICU stays in the target.

The raw Delta schema confirmed `Observation.valueQuantity.value` as
`decimal(32,6)`, while the materialized `quantity_value` alias was
`StringType`. The other materialized aliases were: dateTime/string,
instant/timestamp, Period start/end/string, code/system/display/string, and
all UUID/reference/identifier projections/string. This is a target-type
requirement: a final numeric output must cast the Quantity alias, and a final
integer identifier output must cast the identifier value.

## Exact Observation.id / getResourceKey UUID-v5 construction

The authoritative ETL files are:

- `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql`
  lines 9, 21, 41, 45, and 67.
- `/Users/nau025/Documents/mimic-fhir/sql/fhir_etl/uuid_namespace.sql` line 27.

The ETL first computes the effective value as
`CAST(ce.charttime AS TIMESTAMPTZ)` (line 9), but computes the resource UUID
before that normalization (line 21):

```text
name = ce.stay_id || '-' || ce.charttime || '-' || ce.itemid || '-' || ce.value
uuid = uuid_generate_v5(ns_observation_chartevents, name)
```

The namespace chain is exactly:

```text
uuid_ns_oid()                                      = 6ba7b812-9dad-11d1-80b4-00c04fd430c8
uuid_generate_v5(uuid_ns_oid(), 'MIMIC-IV')        = 24ba6d92-ae8e-56f9-8898-873d8cba02da
uuid_generate_v5(MIMIC-IV, 'ObservationChartevents')
                                                     = 36e18860-b4aa-5577-bc80-a5b07922cd3d
```

`Observation.id` is that UUID and `getResourceKey()` materializes it as
`Observation/<uuid>`. The exact PostgreSQL textual inputs matter: use the
source wall-time text and `ce.value` text; do not use the normalized effective
instant, a rounded final height, or an arbitrarily formatted floating-point
number.

### Conditional recovery algorithm

For each target Observation, after joining its `encounter_id` to the ICU
Encounter identifier and filtering the two exact item codes:

1. Strip only the offset from `effective_datetime` by casting the string
   directly to `TIMESTAMP_NTZ`; this obtains the FHIR effective wall clock and
   avoids Spark timezone conversion.
2. Keep `observation_id` and extract its UUID after `Observation/`.
3. Build UUIDv5 candidate A from
   `stay_id_str`, candidate-A wall time, `item_code`, and the uncast
   `quantity_value` string. Candidate A is the served effective wall time.
4. If candidate A equals the resource UUID, use candidate-A wall time as the
   recovered charttime.
5. Otherwise build candidate B with exactly one hour subtracted from the
   `TIMESTAMP_NTZ` wall time. If candidate B equals the resource UUID, use the
   earlier wall time. This is the DST-gap recovery branch.
6. Never subtract one hour from every 03:xx row. A genuine 03:xx source row
   matches candidate A; only an exact candidate-B UUID permits the correction.
   Do not use Spark `DATE_FORMAT` to make the UUID name after subtraction,
   because it can re-normalize a `TIMESTAMP_NTZ` value in a session-zone DST
   gap. Preserve the wall-time string with an NTZ-safe cast/string operation.

The demo re-probe reproduced source UUIDs from the ETL namespace and source
text for 142/142 rows. It also reconstructed the served resource UUID from
the served stay identifier, item code, effective wall time, and Quantity alias
string for 142/142 rows. The one-hour-earlier candidate matched 0/142 in this
demo; the source contained one genuine 03:xx row for each code and both stayed
on the direct candidate. Attempt 0001's full-data diagnosis independently
reported the four height conflicts as candidate 03:xx versus oracle 02:xx,
with equal subject, stay, and height, exactly the case addressed by candidate
B.

## Oracle checks and derived output

Read-only DuckDB checks found 71 source rows per code after the ETL-relevant
non-null filters and duplicate exclusion. There were no duplicate
`(itemid, subject_id, charttime)` groups in the demo; the two code streams had
71 matching `(subject_id, charttime)` keys and no mismatched stay pair.

Joining the 142 FHIR rows to Patient and ICU Encounter identifiers and casting
the effective dateTime directly to `TIMESTAMP_NTZ` gave:

- source/FHIR alignment on `(itemid, subject_id, stay_id, charttime)`:
  **142/142 exact**;
- source `value` text versus served Quantity alias:
  **142/142 exact**;
- source `valuenum` numeric versus served Quantity numeric:
  **142/142 exact**;
- after code-specific conversion, cm precedence, and strict bounds:
  **69/69 exact full tuples**, with no FHIR-only or source-only rows.

The source full join remains on `subject_id + charttime`, not `stay_id`; do
not add `stay_id` to that join. Recover corrected charttime before the
`ht_cm`/`ht_in` split and full outer join. The source semantics remain:
`226730` cm is the left/COALESCE-preferred stream, `226707` inches is converted
by 2.54, both are rounded to two decimals, and final values are restricted to
`120 < height < 230`.

## Gaps and representability

- **`subject_id` and `stay_id`: absent but derivable exactly.** Observation
  stores UUID references, not numeric MIMIC ids. Patient and ICU Encounter
  identifier values supplied 142/142 exact joins in the demo; cast their FHIR
  strings to the manifest's integer outputs.
- **`height`: absent as one stored normalized field but derivable exactly.**
  Quantity value plus exact item code/unit reproduces the 69/69 demo output.
- **Original `charttime`: absent from `effectiveDateTime` alone but derivable
  exactly for this chartevents ETL when the UUID witness matches.** The ETL's
  `TIMESTAMPTZ` cast irreversibly changes a source wall time in a DST
  spring-forward gap, but the pre-cast time survives in Observation.id. The
  four full-data conflicts from attempt 0001 are therefore fixable by the
  conditional UUID test, not a reason to blanket-shift genuine 03:xx rows.
  If neither UUID candidate matches, the mapping has no warrant to invent a
  time and must retain/report the served wall time rather than apply a
  heuristic.
- **FHIR coverage:** no height-specific missing Observation was demonstrated
  in the authoritative demo. The upstream chartevents ETL does omit its one
  hard-coded duplicate and all rows with source `value IS NULL`; neither
  condition affected these 142 demo target rows. Those are potential
  full-data coverage gaps only if a source height row hits them.
- `height_orig`, source `value`, source `valueuom`, `itemid`, and `hadm_id` are
  not final columns of the canonical height SQL. The source `value` and
  `valueuom` paths above are retained only for exact FHIR identity/value
  interpretation; there is no missing final output column for them.

## Notes/fragments used

The corrected analysis was grounded in curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`,
especially the identifier spine, Quantity alias typing, direct `TIMESTAMP_NTZ`
rule, chartevents code-system rule, and chartevents ETL behavior. It read all
fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`: `README.md`, `arb.md`,
`blood_differential.md`, `cardiac_marker.md`, `chemistry.md`,
`code_status.md`, `coagulation.md`, `complete_blood_count.md`, `crrt.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`, and `height.md`.
The `height.md` effective-choice and UUID leads were rechecked against this
probe and the ETL; the unrelated fragments were treated as provisional leads,
not evidence, and were not adopted as height facts. The prior height source
carryover, attempt 0001 FHIR-prober evidence, implementer output, full
comparison, and mismatch diagnosis were also read. The canonical structural
reference was
`/Users/nau025/Documents/master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.

No attempt 0001 file was modified and no attempt 0002 implementation was
authored.
