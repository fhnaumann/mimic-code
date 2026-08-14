# FHIR prober mapping: `vitalsign`, attempt 0001

## Inputs and probe provenance

- Concept: `vitalsign` (`measurement/vitalsign.sql`), attempt `0001`.
- Source analysis: `mimic-iv/concepts_fhir/carryover/vitalsign/source-analyst.md`.
- Canonical source table: `mimiciv_icu.chartevents`.
- Authoritative FHIR warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`.
- Probe engine: embedded Pathling 9.6.0 on Spark 4.0.2. The Spark session was
  checked both at its default `Australia/Sydney` timezone and at
  `America/New_York`; the live Pathling server was not used.
- Read-only source oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- Structural reference:
  `/Users/nau025/Documents/master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- No ViewDefinition or `concept.sql` was authored by this stage.

The DuckDB source query has output types:

```text
subject_id       INTEGER
stay_id          INTEGER
charttime        TIMESTAMP
heart_rate       DOUBLE
sbp              DOUBLE
dbp              DOUBLE
mbp              DOUBLE
sbp_ni           DOUBLE
dbp_ni           DOUBLE
mbp_ni           DOUBLE
resp_rate        DOUBLE
temperature      DECIMAL(18,2)
temperature_site VARCHAR
spo2             DOUBLE
glucose          DOUBLE
```

The source natural grain is `(subject_id, stay_id, charttime)`. The source
filter is `stay_id IS NOT NULL` plus the 19 active itemids below. The apparent
`226329` temperature item is only in a SQL comment and is not an active code.

## Resource and stream mapping

| MIMIC-IV source role | FHIR resource/path | FHIR stream discriminator |
|---|---|---|
| `mimiciv_icu.chartevents` row | `Observation` | `code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` plus exact string `code` |
| `chartevents.subject_id` | `Observation.subject` → `Patient` | equality join on `Observation.subject.getReferenceKey(Patient)` to `Patient.getResourceKey()`; emit the Patient identifier value, not the reference key |
| `chartevents.stay_id` | `Observation.encounter` → ICU `Encounter` | equality join on `Observation.encounter.getReferenceKey(Encounter)` to `Encounter.getResourceKey()`; select the ICU Encounter by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` |

The exact system was observed on all 96,145 target coding rows. The
chartevents system is distinct from the shared `mimic-d-items` system used by
the `outputevents` and `datetimeevents` streams. Within the chartevents
system, exact item code is the source `d_items.itemid`; `d_items.itemid` is a
global key with one `linksto` value per item. Therefore system plus exact code
is the discriminator. Do not use `meta.profile`.

`Observation.getResourceKey()` was used only for distinct-resource counts and
may be projected as an opaque support key. It is not a source `subject_id`,
`stay_id`, `charttime`, itemid, or value, and no resource id is parsed,
regenerated, guessed, or used as a side channel.

## Canonical select.column projections

These are mapping projections for the implementer, not an attempt
ViewDefinition. The coding filter belongs inside the coding `forEach`.

### Observation flat columns

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_id" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(Quantity).system", "name": "quantity_system" },
    { "path": "(value).ofType(Quantity).code", "name": "quantity_code" },
    { "path": "(value).ofType(string)", "name": "string_value" },
    { "path": "issued", "name": "issued" }
  ]
}
```

### Observation coding group

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

The exact item code must be compared as a string before any integer cast. The
target code set can additionally be constrained in this `forEach` or in the
immediate source-system-filtered relation.

### Patient identifier spine

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

`subject_id_str` is FHIR `Identifier.value`, hence a FHIR `string`/materialized
`VARCHAR`; cast it to the final `INTEGER` output type only in the outer SQL.

### ICU Encounter identifier spine

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }
  ]
}
```

Filter this Encounter relation to the ICU identifier system, equivalently
`stay_id_str IS NOT NULL`. `stay_id_str` is FHIR `string`/materialized
`VARCHAR`; cast it to final `INTEGER`. `Encounter.class` is not a stream
discriminator.

## Source column/output to FHIRPath mapping

| Source column or output | Canonical `{path, name}` mapping | FHIR type | Materialized type and required target type |
|---|---|---|---|
| `ce.subject_id` → `subject_id` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_id" }`, joined to Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` then `Identifier.value` `string` | reference and identifier aliases are `VARCHAR`; final `CAST(subject_id_str AS INTEGER)` |
| `ce.stay_id` → `stay_id` | Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" }`, joined to ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` then `Identifier.value` `string` | reference and identifier aliases are `VARCHAR`; final `CAST(stay_id_str AS INTEGER)` |
| `ce.charttime` → `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` | Pathling ViewDefinition alias is offset-bearing `VARCHAR`; direct `CAST`/`TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` preserves the served wall value. Keep the outer target as `TIMESTAMP_NTZ`, not plain Spark `TIMESTAMP`. |
| effective choice check | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }`; `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }`; `{ "path": "(effective).ofType(instant)", "name": "effective_instant" }` | `Period.start/end` are `dateTime`; `instant` is `instant` | the Period aliases materialize as `VARCHAR`, the instant alias as native Spark `TIMESTAMP`; all three are NULL on the 96,145-row target, so never COALESCE the unused native timestamp with the dateTime string |
| `ce.itemid` → code discriminator | coding group `{ "path": "code", "name": "item_code" }` | `Coding.code` (`code` primitive/string) | `VARCHAR`; exact string filter after exact system filter, then `CAST(item_code AS INTEGER)` if needed |
| code system | coding group `{ "path": "system", "name": "item_system" }` | `Coding.system` (`uri`) | `VARCHAR`; exact value is the chartevents d-items URI above |
| `d_items.label` (inspection only) | coding group `{ "path": "display", "name": "item_display" }` | `Coding.display` `string` | `VARCHAR`; not a source filter |
| `ce.valuenum` → numeric branches | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` `decimal` | Pathling alias is `VARCHAR`; raw Delta `valueQuantity.value` is `decimal(32,6)`. Cast the alias to numeric before predicates, conversion, `AVG`, and final DOUBLE/DECIMAL output. |
| `ce.valueuom` → numeric unit (not a final output) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }`; optionally `{ "path": "(value).ofType(Quantity).system", "name": "quantity_system" }`, `{ "path": "(value).ofType(Quantity).code", "name": "quantity_code" }` | `Quantity.unit` `string`; `Quantity.system` `uri`; `Quantity.code` `code` | all materialize as `VARCHAR`; `quantity_system` is the MIMIC units URI and `quantity_code` equals the unit where present |
| `ce.value` for item `224642` → `temperature_site` | `{ "path": "(value).ofType(string)", "name": "string_value" }` | `Observation.valueString` `string` | `VARCHAR`; exact source text is available for 3,794/3,794 target rows and feeds the source `MAX` |
| `ce.value` on numeric rows | no exact value path for the original text when `valuenum` is non-NULL; the FHIR ETL uses Quantity only | source `VARCHAR` absent from FHIR on numeric rows | Not needed by this SQL: numeric branches use `valuenum`, and only item `224642` uses source `value`. Do not use an opaque id to recover discarded numeric-row text. |
| `ce.storetime` | not used by canonical SQL; probe-only `{ "path": "issued", "name": "issued" }` | FHIR `instant` | populated on 96,145/96,145, but it is an instant rendered according to the Spark session timezone and is not a replacement for `effective_datetime`; no final vitalsign column uses it |
| `ce.hadm_id`, `warning`, `error`, `resultstatus`, other unreferenced fields | no mapping required | — | absent from the source query's semantics and final shape |

## Itemid-to-value-path and output mapping

All rows in this table use the constrained chartevents coding group above. The
numeric rows use `quantity_value`; only `224642` uses `string_value`.

| Source itemid / exact FHIR `code` | Served display | FHIR value path | Source branch/output and condition | Source rows = FHIR resources |
|---:|---|---|---|---:|
| `220045` | Heart Rate | `(value).ofType(Quantity).value` | `heart_rate`; `valuenum > 0 AND valuenum < 300` | 13,913 = 13,913 |
| `225309` | ART BP Systolic | Quantity value | `sbp`; `0 < valuenum < 400` | 486 = 486 |
| `225310` | ART BP Diastolic | Quantity value | `dbp`; `0 < valuenum < 300` | 486 = 486 |
| `225312` | ART BP Mean | Quantity value | `mbp`; `0 < valuenum < 300` | 488 = 488 |
| `220050` | Arterial Blood Pressure systolic | Quantity value | `sbp`; `0 < valuenum < 400` | 5,525 = 5,525 |
| `220051` | Arterial Blood Pressure diastolic | Quantity value | `dbp`; `0 < valuenum < 300` | 5,524 = 5,524 |
| `220052` | Arterial Blood Pressure mean | Quantity value | `mbp`; `0 < valuenum < 300` | 5,560 = 5,560 |
| `220179` | Non Invasive Blood Pressure systolic | Quantity value | `sbp` and `sbp_ni`; `0 < valuenum < 400` | 8,347 = 8,347 |
| `220180` | Non Invasive Blood Pressure diastolic | Quantity value | `dbp` and `dbp_ni`; `0 < valuenum < 300` | 8,349 = 8,349 |
| `220181` | Non Invasive Blood Pressure mean | Quantity value | `mbp` and `mbp_ni`; `0 < valuenum < 300` | 8,342 = 8,342 |
| `220210` | Respiratory Rate | Quantity value | `resp_rate`; `0 < valuenum < 70` | 13,913 = 13,913 |
| `224690` | Respiratory Rate (Total) | Quantity value | `resp_rate`; `0 < valuenum < 70` | 1,331 = 1,331 |
| `220277` | O2 saturation pulseoxymetry | Quantity value | `spo2`; `0 < valuenum <= 100` | 13,540 = 13,540 |
| `225664` | Glucose finger stick (range 70-100) | Quantity value | `glucose`; `valuenum > 0` | 1,637 = 1,637 |
| `220621` | Glucose (serum) | Quantity value | `glucose`; `valuenum > 0` | 931 = 931 |
| `226537` | Glucose (whole blood) | Quantity value | `glucose`; `valuenum > 0` | 209 = 209 |
| `223762` | Temperature Celsius | Quantity value | Celsius branch of `temperature`; `10 < valuenum < 50` | 391 = 391 |
| `223761` | Temperature Fahrenheit | Quantity value | Fahrenheit branch of `temperature`; `70 < valuenum < 120`, then `(valuenum - 32) / 1.8` | 3,379 = 3,379 |
| `224642` | Temperature Site | `(value).ofType(string)` | `temperature_site`; `MAX(string_value)` at `(subject_id, stay_id, charttime)` | 3,794 = 3,794 |

The target totals are 96,145 source rows and 96,145 FHIR Observation
resources. The source has no NULL `stay_id`, `subject_id`, `charttime`, or
`value` among these itemids. `valuenum` is non-NULL on every numeric item and
NULL on all 3,794 temperature-site rows.

## Confirmed coding system, code counts, and cardinality

The system was first established with an unconstrained `forEach:
"code.coding"` projection. The authoritative Delta's coding-system counts
were:

```text
chartevents d-items       668,862 coding rows / 668,862 resources
labitems d-labitems       107,727 / 107,727
shared ICU d-items          24,642 / 24,642
LOINC                         9,042 / 9,042
microbiology test             1,893 / 1,893
microbiology antibiotic       1,036 / 1,036
microbiology organism           338 / 338
```

For the constrained chartevents system and the exact source code set, every
code had one coding and one Observation resource. The ratio is
**96,145 / 96,145 = 1.000 overall and 1.000 for every code**. No listed code
was absent, no listed code occurred under another system, and the source and
FHIR counts above agree per code. The exact `system + code` rule is therefore
confirmed; no terminology translation is involved.

Quantity units observed from the served values were:

```text
220045 bpm (13,913)
220050/220051/220052/220179/220180/220181/225309/225310/225312 mmHg
220210/224690 insp/min
220277 %
223761 °F; 223762 °C
220621 mg/dL (922), NULL (9)
225664 NULL (1,637)
226537 mg/dL (188), NULL (21)
224642 has no Quantity unit (string value)
```

For numeric rows, `quantity_system` was
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units` and
`quantity_code` equalled the unit when present. The materialized Quantity
alias was string-like, so it must not be emitted as the final numeric output
without a cast.

## Identifier, value, timestamp, and cardinality checks

The Patient projection had 100 rows, 100 resource keys, and 100 patient
identifier values. The Encounter projection had 637 rows and 140 ICU
identifier values. On the target Observation join:

```text
Observation rows                                  96,145
subject reference non-NULL                        96,145
encounter reference non-NULL                      96,145
Patient identifier values resolved                96,145
ICU Encounter identifier values resolved           96,145
subject and ICU Encounter patient agree            96,145
effective.ofType(dateTime)                        96,145
effective.ofType(Period).start                         0
effective.ofType(Period).end                           0
effective.ofType(instant)                             0
issued                                             96,145
value.ofType(Quantity).value                       92,351
value.ofType(string)                                3,794
```

The quantity/string counts sum to the target row count. The target therefore
has no value-choice rows requiring a CodeableConcept or another Observation
value variant. The dateTime/Period/instant probe aliases were kept separate;
the unused instant alias is a native Spark timestamp while the dateTime and
Period aliases are strings. Do not coalesce those aliases before casting.

The read-only DuckDB source checks found no active target row with a NULL
`value`, and the hard-coded global ETL exclusion
`(stay_id=34934165, charttime='2151-10-03 05:14:00')` matched zero target rows.
Thus the global `value IS NOT NULL` and hard-coded-duplicate ETL predicates
caused zero demo omissions for this item set. They remain coverage rules for a
full-data run; an omitted source row has no FHIR resource from which to derive
a replacement.

The source has 21,086 `(subject_id, stay_id, charttime)` groups, 18,696
multi-row groups, and maximum group size 13. Every itemid has zero repeated
rows at the source grain `(subject_id, stay_id, charttime, itemid)` in this
demo. Do not use `DISTINCT` as a general FHIR-side optimization: the source
aggregate consumes all rows, and the FHIR ETL retains resource rows. After
directly casting the served dateTime to `TIMESTAMP_NTZ`, the FHIR target has
21,084 groups, 18,694 multi-row groups, maximum group size 15, and 13 repeated
effective `(subject_id, stay_id, itemid, effective_datetime)` keys caused by
timestamp collisions.

The source/FHIR value-and-unit multiset comparison, ignoring effective time
but rounding the source FLOAT/FHIR decimal representation to three decimal
places, was **96,145/96,145 exact**. This includes the categorical
temperature-site text and all Quantity values. The source FLOAT versus served
decimal representation can differ in binary display (for example
`98.699997` versus `98.7`), so compare numeric values after the required cast
with an appropriate tolerance rather than requiring binary identity.

## Temperature and glucose details

The source temperature checks were:

```text
item 223761 Fahrenheit: 3,379 rows, 3,379 valid under 70 < v < 120
item 223762 Celsius:    391 rows,   388 valid under 10 < v < 50
item 223762 Celsius:    3 rows are invalid, including the demo's 99 °C value
```

The FHIR Quantity unit/code paths preserve `°F` and `°C`. The source-derived
temperature replay used Quantity values, converted Fahrenheit, excluded the
same invalid rows, averaged both units at the source grain, and rounded to two
decimal places. On the 21,083 shared output groups, the `temperature` column
agreed exactly on all 21,083; `temperature_site` also agreed exactly on all
21,083 shared groups.

The three glucose item streams all had positive source `valuenum` values:
`220621` 931/931, `225664` 1,637/1,637, and `226537` 209/209. Quantity units
are incomplete as recorded above, but the source SQL does not use
`valueuom`; Quantity numeric values are present on 2,777/2,777 rows. The
glucose replay agreed on 21,083/21,083 shared output groups; its source output
has 2,753 non-NULL glucose groups because multiple glucose rows can share an
output group.

## Oracle replay and effective-time gap

The FHIR replay used the exact source CASE predicates, Fahrenheit conversion,
two-decimal temperature round, lexical `MAX` for `temperature_site`, and
`GROUP BY (subject_id, stay_id, CAST(effective_datetime AS TIMESTAMP_NTZ))`.
The result was:

```text
source output groups                 21,086
FHIR output groups                   21,084
shared groups                       21,083
source-only groups                       3
FHIR-only groups                         1
```

The source-only groups were:

```text
(10003400, 32128372, 2137-03-10 02:00:00)
(10035631, 30932571, 2116-03-08 02:00:00)
(10035631, 30932571, 2116-03-08 02:52:00)
```

The FHIR-only group was `(10035631, 30932571, 2116-03-08 03:52:00)`. The
corresponding served effective times are the New York spring-forward-normalized
03:xx values. The 14 affected source rows are all at the two target stays and
02:00/02:52 times; they remain 96,145 FHIR resources but some share a served
effective key with genuine 03:xx rows. This is consistent with the
dataset-wide ETL transform at
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`.

On the 21,083 shared groups, the output comparison was:

```text
heart_rate       21,081/21,083
sbp              21,081/21,083
dbp              21,081/21,083
mbp              21,081/21,083
sbp_ni           21,082/21,083
dbp_ni           21,082/21,083
mbp_ni           21,082/21,083
resp_rate        21,081/21,083
temperature      21,083/21,083
temperature_site 21,083/21,083
spo2             21,081/21,083
glucose           21,083/21,083
```

These are a probe comparison, not a terminal verdict. The original source
wall time in a DST gap is not present in any FHIR element. Resource/reference
ids are opaque and cannot be used to recover it. This loss reaches 14/96,145
source Observation rows and 3/21,086 source output groups, but it is potentially
essential here because `charttime` is the output/natural key and the grouping
key; collision can change row inclusion and the values selected into the
averages. The served `effective_datetime` identifies the transformed time but
does not identify whether a 03:xx value was an original 03:xx event or a moved
02:xx event. A typed NULL cannot repair that key ambiguity. The equivalence
judge should assess the full concept and, if treating this contaminated
grouping as essential, consider a whole-concept representation block. No
terminal block or acceptance is made by this prober.

`Observation.issued` is not a substitute temporal key. The ETL writes source
`storetime` after a `TIMESTAMPTZ` cast, so it is a FHIR `instant`. In the
embedded probe's default `Australia/Sydney` session, a served `issued` value
rendered the instant in the Sydney zone (for example source wall storetime
`2180-07-23 15:34:00` rendered as `2180-07-24 05:34:00`); changing the Spark
session to `America/New_York` rendered the source wall clock. Vitalsign does
not use `storetime`, so no issued-based ordering or output mapping is needed.

## Gaps and representability

| Information | Classification | Consequence |
|---|---|---|
| Numeric `subject_id` | Absent on Observation but exactly derivable | Equality-join the Observation subject reference to Patient and project the patient identifier system. All 96,145 target rows resolved. It is essential to the output key, but not a gap after this join. |
| Numeric `stay_id` | Absent on Observation but exactly derivable | Equality-join the Observation encounter reference to the ICU Encounter and project the ICU identifier system. All 96,145 target rows resolved. It is essential to the output key, but not a gap after this join. |
| Numeric source `valuenum` | Absent as a native output alias but derivable | `Quantity.value` is present on all 92,351 numeric target rows; cast the materialized string alias before arithmetic. Value/unit multiset comparison was 96,145/96,145 after type normalization. |
| Source `value` on numeric rows | Absent and not needed for this concept | The ETL writes Quantity when `valuenum` is non-NULL and drops the original numeric-row text. Vitalsign uses `value` only for item 224642, whose 3,794 string values are all preserved. The discarded numeric-row text is not a final output and does not affect this SQL's numeric branches; do not recover it from ids. |
| Original source `charttime` at DST spring-forward gaps | Not representable for 14 source rows | FHIR carries only transformed `effectiveDateTime`. The loss reaches 3/21,086 output groups and changes some shared aggregate columns. It can change key inclusion/grouping and therefore is potentially essential; the judge must assess the complete concept. No id-based recovery is permitted. |
| Source rows omitted by global ETL predicates | Not representable if present | The target demo has 0 NULL-`value` rows and 0 hard-coded duplicate rows, so measured loss is 0/96,145. If full data contains one, there is no FHIR resource/path from which to reconstruct it. |
| `storetime` | Not a gap for vitalsign | It is not read, filtered, grouped, ranked, or emitted by the canonical SQL. `issued` is ancillary only. |

## Curated notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

- Delta tables, not stale NDJSON or the live server, are authoritative.
- Itemid-derived Observation codes are verbatim and must be filtered by exact
  `system + code`; `meta.profile` is not a discriminator.
- Patient and ICU identifiers are `Identifier.value` strings; resource and
  reference ids are opaque and final numeric outputs need casts.
- ICU Encounter streams require the ICU identifier system, not `class`.
- Quantity ViewDefinition aliases are string-like and need numeric casts.
- Effective choice aliases can have mixed materialized Spark types and must be
  projected separately; datetimes must be cast directly to `TIMESTAMP_NTZ`.
- Categorical chartevents use `valueString`, and ICU temperature is split into
  Fahrenheit and Celsius item streams.
- The essential-loss/opaque-id policy forbids timestamp recovery through ids.

I read `MIMIC_NOTES.d/README.md` and all current concept fragments:
`arb.md`, `blood_differential.md`, `cardiac_marker.md`, `chemistry.md`,
`code_status.md`, `coagulation.md`, `complete_blood_count.md`, `crrt.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`,
`icp.md`, `icustay_detail.md`, `invasive_line.md`, `icustay_times.md`,
`kdigo_creatinine.md`, `milrinone.md`, `neuroblock.md`, `norepinephrine.md`,
`oxygen_delivery.md`, `phenylephrine.md`, `rhythm.md`, `rrt.md`,
`urine_output.md`, and `vasopressin.md`. The requested fragments were treated
as provisional leads. The chartevents system, Quantity/string choice,
effective-choice typing, ICU identifier spine, repeated-row, NULL-omission,
and DST leads were independently checked for this target; unrelated
medication/lab claims were not substituted as vitalsign evidence. The
historical UUID-recovery suggestions in sibling fragments were rejected under
the opaque-id policy.

The only new dataset-wide finding appended by this prober is recorded in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/vitalsign.md`. It sharpens the
session-timezone behavior of the chartevents `issued` instant; it does not
change the vitalsign source mapping because `storetime` is unused.
