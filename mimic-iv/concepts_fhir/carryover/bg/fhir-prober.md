# FHIR probe and mapping: `bg`

**Concept:** `measurement/bg`  
**Source analysis:** `carryover/bg/source-analyst.md`  
**Probed:** 2026-08-07  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, read with
Pathling 9.6.0 / Spark 4.0.2. No HTTP Pathling server was used.

## Scope and comparison shape

The oracle manifest declares 27 output columns, 511,637 full-data rows, no
unique natural key, and `full_tuple_multiset` comparison. Do not key the
candidate on `(subject_id, charttime)` or any other demo-derived key: `bg` is
explicitly one of the concepts whose apparent demo key is not unique on full
data. The candidate must preserve the 27 output names and types, including
`fio2_chartevents FLOAT` and `aado2_calc DECIMAL(38,4)`.

The source pivot groups by relational `labevents.specimen_id`. The FHIR
equivalent grouping spine is the Observation-to-Specimen reference below; it
is not a patient/time approximation.

## Resource, profile, and discriminator mapping

| Source table/stream | FHIR resource | Profile observed in the embedded demo | Discriminator to use |
|---|---|---|---|
| `mimiciv_hosp.labevents` | `Observation` | `http://mimic.mit.edu/fhir/mimic/StructureDefinition/mimic-observation-labevents` | `Observation.code.coding` system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` |
| `mimiciv_icu.chartevents` | `Observation` | `http://mimic.mit.edu/fhir/mimic/StructureDefinition/mimic-observation-chartevents` | `Observation.code.coding` system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` |
| `labevents.specimen_id` | `Specimen` join target | — | `Specimen.identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab` |
| `labevents.subject_id` / chart `subject_id` | `Patient` join target | — | `Patient.identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/patient` |
| lab `hadm_id` | hospital-stream `Encounter` join target | — | `Encounter.identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` |

The current embedded demo retains subtype `meta.profile` values, but another
MIMIC-on-FHIR warehouse variant has used the merged Observation profile. The
portable discriminator is therefore the base binding in `code.coding.system`
and item code, not `meta.profile`. This updates the earlier general note in
`MIMIC_NOTES.md`.

### Identifier and join spines

These are FHIRPath extraction columns, not final output types. Identifier
values are FHIR `string`/Pathling `VARCHAR`; the final SQL must cast the
numeric MIMIC IDs to `INTEGER`.

| Purpose | Canonical extraction (`{path, name}`) | FHIR type / observed materialized type |
|---|---|---|
| patient resource join | `{path: "getResourceKey()", name: "patient_key"}` on `Patient` | resource key string / `VARCHAR` |
| source `subject_id` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` on `Patient` | `string` / `VARCHAR`; cast to final `INTEGER` |
| Observation → Patient | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | reference key string / `VARCHAR` |
| Observation → Specimen | `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` | reference key string / `VARCHAR` |
| source `specimen_id` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", name: "specimen_id_str"}` on `Specimen` | `string` / `VARCHAR`; cast to grouping `INTEGER` if needed |
| Observation → Encounter | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` | reference key string / `VARCHAR` |
| source `hadm_id` | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` on `Encounter` | `string` / `VARCHAR`; cast to final `INTEGER` |

All joins above are left joins. In the demo, every targeted lab Observation
had a Patient and Specimen join. The targeted lab set had 8,706 rows: 8,024
had a hospital Encounter reference and those 8,024 `hadm_id` values agreed
with DuckDB exactly; the remaining 682 had no FHIR Encounter reference and
the corresponding source `hadm_id` was NULL. Do not inner-join lab
Observations to Encounter. Chart enrichments retain their ICU Encounter
reference for provenance, but `bg.sql` intentionally joins them only on
Patient plus time, not on `hadm_id` or `stay_id`.

## Choice types and timestamp handling

### Observation code

`Observation.code` is a `CodeableConcept`. The canonical coding projection is:

```json
{
  "forEach": "code.coding",
  "column": [
    {"path": "code", "name": "code"},
    {"path": "system", "name": "system"},
    {"path": "display", "name": "display"}
  ]
}
```

The three extracted fields are FHIR `code`, `uri`, and `string` respectively
(all arrive as string-like columns in Spark). In the target probe, all 23,992
target rows had non-null `system`, `code`, and `display` (23,992/23,992 for
each). These are proprietary MIMIC item-code systems; do not invent LOINC
codes. MIMIC-IV 2.2 `d_labitems` has no LOINC columns.

Use these filters (the Pathling probe confirmed that the code-system binding
is the reliable discriminator):

```text
lab:   system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems
chart: system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
```

Terminology flags from the profile definitions: `Observation.code` is a
`CodeableConcept` with a **required** binding for both streams — lab uses
ValueSet `http://mimic.mit.edu/fhir/mimic/ValueSet/mimic-d-labitems`, and chart
uses ValueSet
`http://mimic.mit.edu/fhir/mimic/ValueSet/mimic-chartevents-d-items`. The
canonical projection remains `{path: "code", name: "code"}`,
`{path: "system", name: "system"}`, and `{path: "display", name: "display"}`
under `forEach: "code.coding"`. The source SQL's literal itemids are lifted
verbatim; no terminology translation is performed or required.

For the 25 source lab itemids, the exact lab filter is
`52033, 50801, 50802, 50803, 50804, 50805, 50806, 50807, 50808, 50809,
50810, 50811, 50813, 50814, 50815, 50816, 50817, 50818, 50819, 50820,
50821, 50822, 50823, 50824, 50825`. Item `50807` is a dead v1.0 comments
filter in this 2.2 demo and contributes no Observation; it is not an output
column. The chart filters are exactly `220277` and `223835`.

### Observation.value[x] (corrected for attempt 0004)

Project both variants because the resource field is polymorphic:

```json
{"path": "(value).ofType(Quantity).value", "name": "quantity_value"}
{"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"}
{"path": "(value).ofType(Quantity).code", "name": "quantity_code"}
{"path": "(value).ofType(string)", "name": "value_string"}
```

The FHIR semantic type of `Quantity.value` is `decimal`, but Pathling's
materialized ViewDefinition column was observed as `string`/`VARCHAR`; cast it
to the target numeric type in SQL. `Quantity.unit` and `.code` are strings and
are not output columns. The specimen-type item `52033` uses `valueString`, not
a CodeableConcept, and is the FHIR-side carrier for the source specimen text.
The numeric lab and chart items use `valueQuantity.value`; a few rows can use
the string variant when the source numeric value is absent, so numeric source
pivots must not fall back to `value_string`.

Target probe counts were 23,992 rows total, 22,957 Quantity values and 1,035
string values. Every target effective value was dateTime. No target value used
the `Period` or `instant` effective variants: dateTime 23,992/23,992,
`(effective).ofType(Period).start` 0/23,992, and
`(effective).ofType(instant)` 0/23,992. Therefore this concept can project
the dateTime variant only, but must not mistake the Pathling schema's other
choice columns for populated data.

### Corrected `52033` source-value rule and comments fallback

The mapping is not a claim that every `Observation.value.ofType(string)` is
relational `labevents.value`. The upstream ETL writes the choice as follows:
`mimic-fhir/sql/fhir_observation_labevents.sql:133-136` uses `lab_VALUE` when
present, but uses `lab_COMMENTS` when both `lab_VALUENUM` and `lab_VALUE` are
NULL. Consequently the FHIR resource has no provenance bit distinguishing a
real source text from a comments fallback.

For this concept the canonical source is specifically `labevents.value` for
item `52033`, and `bg.sql:14` expects NULL when that source value is NULL. The
reusable mapping therefore requires the implementer to normalize the extracted
string before the specimen pivot:

```text
{path: "(value).ofType(string)", name: "value_string"}
```

is the FHIR extraction, but the source-value projection is
`NULLIF(value_string, '___')` for code `52033`, not the raw `value_string`.
The known full-data failure was subject `18503414`, specimen `67072637`, at
`2130-12-15 13:43`: source `value=NULL`, `comments='___'`, while FHIR
`value_string='___'`. This marker normalization restores the canonical NULL.
There is no direct FHIR path for relational `labevents.comments`; it must not
be mapped as `specimen` or as a separate output column.

### Observation.effective[x]

```json
{"path": "(effective).ofType(dateTime)", "name": "effective_datetime"}
```

This is the source `charttime` for both lab and chart streams. It is a FHIR
`dateTime`, extracted as an ISO string with an offset. Use
`CAST(effective_datetime AS TIMESTAMP_NTZ)` in Spark SQL: preserve the
de-identified MIMIC wall-clock value and discard the offset rather than
converting it as a real instant.

## Source-column to FHIR mapping

### `mimiciv_hosp.labevents`

The following source columns are used by the SQL. `subject_id`, `hadm_id`,
`specimen_id`, and `charttime` are carried at Observation/item level and then
collapsed by the Specimen spine.

| Source column / role | Canonical FHIR extraction (`{path, name}`) | FHIR type | Final/use type |
|---|---|---|---|
| `subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` plus Patient `identifier...value` → `subject_id_str` | `Reference(Patient)` + identifier `string` | cast to output `INTEGER` |
| `hadm_id` | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` plus Encounter `identifier.where(system='.../encounter-hosp').value` → `hadm_id_str` | `Reference(Encounter)` + identifier `string` | left join; cast to output `INTEGER` |
| `specimen_id` | `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` plus Specimen `identifier...specimen-lab.value` → `specimen_id_str` | `Reference(Specimen)` + identifier `string` | grouping key, cast if used in SQL |
| `itemid` | `{path: "code", name: "code"}` under `forEach: "code.coding"`; filter the lab system | `code`/`string` | SQL item discriminator |
| `charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` / extracted `VARCHAR` | cast `TIMESTAMP_NTZ`, output `TIMESTAMP` |
| `value` for item `52033` | `{path: "(value).ofType(string)", name: "value_string"}` | `string` | output `specimen VARCHAR` after `NULLIF(value_string, '___')`; raw FHIR string is not provenance-safe because of the ETL comments fallback |
| `valuenum` for numeric items | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value decimal` / extracted `VARCHAR` | cast to `DOUBLE`, then pivot |
| `valueuom` (not selected by source SQL) | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | `string` | not output |
| `storetime` | no output mapping required | — | source CTE-only column, dropped |
| item `50807` `value` (dead comments item) | `{path: "(value).ofType(string)", name: "comments_value_string"}` if projected | `string` | dropped; item absent in demo Delta |
| relational `labevents.comments` | no direct FHIRPath | — | dropped by canonical SQL; may be leaked into lab `valueString` by the upstream fallback, but is not a source specimen value |

Numeric item pivots and output aliases:

| Source itemid / label | FHIR code filter | Quantity extraction (`{path, name}`) | Output alias / target type |
|---|---|---|---|
| `50817` Oxygen Saturation | lab system + `code='50817'` | `{path: "(value).ofType(Quantity).value", name: "value_50817"}` | `so2` / `DOUBLE` |
| `50821` pO2 | lab system + `code='50821'` | `{path: "(value).ofType(Quantity).value", name: "value_50821"}` | `po2` / `DOUBLE` |
| `50818` pCO2 | lab system + `code='50818'` | `{path: "(value).ofType(Quantity).value", name: "value_50818"}` | `pco2` / `DOUBLE` |
| `50816` Oxygen / lab FiO2 | lab system + `code='50816'` | `{path: "(value).ofType(Quantity).value", name: "value_50816"}` | `fio2` / `DOUBLE`; apply source normalization |
| `50801` Alveolar-arterial Gradient | lab system + `code='50801'` | `{path: "(value).ofType(Quantity).value", name: "value_50801"}` | `aado2` / `DOUBLE` |
| `50820` pH | lab system + `code='50820'` | `{path: "(value).ofType(Quantity).value", name: "value_50820"}` | `ph` / `DOUBLE` |
| `50802` Base Excess | lab system + `code='50802'` | `{path: "(value).ofType(Quantity).value", name: "value_50802"}` | `baseexcess` / `DOUBLE` |
| `50803` Calculated Bicarbonate | lab system + `code='50803'` | `{path: "(value).ofType(Quantity).value", name: "value_50803"}` | `bicarbonate` / `DOUBLE` |
| `50804` Calculated Total CO2 | lab system + `code='50804'` | `{path: "(value).ofType(Quantity).value", name: "value_50804"}` | `totalco2` / `DOUBLE` |
| `50810` Hematocrit | lab system + `code='50810'` | `{path: "(value).ofType(Quantity).value", name: "value_50810"}` | `hematocrit` / `DOUBLE` |
| `50811` Hemoglobin | lab system + `code='50811'` | `{path: "(value).ofType(Quantity).value", name: "value_50811"}` | `hemoglobin` / `DOUBLE` |
| `50805` Carboxyhemoglobin | lab system + `code='50805'` | `{path: "(value).ofType(Quantity).value", name: "value_50805"}` | `carboxyhemoglobin` / `DOUBLE` |
| `50814` Methemoglobin | lab system + `code='50814'` | `{path: "(value).ofType(Quantity).value", name: "value_50814"}` | `methemoglobin` / `DOUBLE` |
| `50806` Chloride | lab system + `code='50806'` | `{path: "(value).ofType(Quantity).value", name: "value_50806"}` | `chloride` / `DOUBLE` |
| `50808` Free Calcium | lab system + `code='50808'` | `{path: "(value).ofType(Quantity).value", name: "value_50808"}` | `calcium` / `DOUBLE` |
| `50825` Temperature | lab system + `code='50825'` | `{path: "(value).ofType(Quantity).value", name: "value_50825"}` | `temperature` / `DOUBLE` |
| `50822` Potassium | lab system + `code='50822'` | `{path: "(value).ofType(Quantity).value", name: "value_50822"}` | `potassium` / `DOUBLE` |
| `50824` Sodium | lab system + `code='50824'` | `{path: "(value).ofType(Quantity).value", name: "value_50824"}` | `sodium` / `DOUBLE` |
| `50813` Lactate | lab system + `code='50813'` | `{path: "(value).ofType(Quantity).value", name: "value_50813"}` | `lactate` / `DOUBLE` |
| `50809` Glucose | lab system + `code='50809'` | `{path: "(value).ofType(Quantity).value", name: "value_50809"}` | `glucose` / `DOUBLE` |

The remaining filtered lab items `50815` (O2 Flow), `50819` (PEEP), and
`50823` (Required O2) are represented by the same Quantity path but are
computed in the source CTE and dropped from the final 27-column SELECT. They
must not be added to the candidate output. `specimen_id` is likewise a
grouping spine, not an output column.

### ICU SpO2/FiO2 enrichments

| Source column / role | Canonical FHIR extraction (`{path, name}`) | FHIR type | Source logic to retain |
|---|---|---|---|
| chart `subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` plus Patient patient identifier | Patient reference + identifier `string` | cast to `INTEGER`; join only on patient |
| chart `charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` / extracted `VARCHAR` | cast `TIMESTAMP_NTZ` |
| chart `itemid` | `{path: "code", name: "code"}` under `forEach: "code.coding"` | `code`/`string` | filter chart system and `220277` or `223835` |
| chart `valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | FHIR `decimal` / extracted `VARCHAR` | cast numeric |
| `220277` O2 saturation | same code/time/value paths, code `220277` | Quantity | retain `0 < value <= 100`, average by `(subject_id, charttime)`, use the newest row in the 2-hour at-or-before window to select the specimen row; it is not output as `so2` |
| `223835` Inspired O2 Fraction | same code/time/value paths, code `223835` | Quantity | retain `0 < value <= 100`; normalize `.2 < value <= 1` to `value*100`, `1 < value < 20` to NULL, `20 <= value <= 100` as-is; group by patient/time, use newest positive value in the 4-hour at-or-before window; output `fio2_chartevents FLOAT` |

There is no hospital/ICU Encounter join in either enrichment. The exact
source windows are `charttime - 2 hours <= effective_datetime <= charttime`
for SpO2 and `charttime - 4 hours <= effective_datetime <= charttime` for
FiO2. Apply `ROW_NUMBER() OVER (PARTITION BY specimen_id ORDER BY charttime
DESC)` twice, retaining rank 1 after each left join. A no-match left join
still produces rank 1 and must preserve the NULL enrichment.

## Final output mapping

These are the output columns required by the oracle manifest. The FHIR paths
are the source projections above; computed columns have no single FHIR path.

| Output column | FHIR/source mapping | Target type |
|---|---|---|
| `subject_id` | Patient identifier value via Observation `subject.getReferenceKey(Patient)` | `INTEGER` |
| `hadm_id` | hospital Encounter identifier value via Observation `encounter.getReferenceKey(Encounter)`, `MAX` per specimen | `INTEGER` |
| `charttime` | Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}`, `MAX` per specimen | `TIMESTAMP` |
| `specimen` | lab Observation code `52033`, `{path: "(value).ofType(string)", name: "value_string"}`, normalized as `NULLIF(value_string, '___')` | `VARCHAR` |
| `so2` | lab code `50817`, Quantity value | `DOUBLE` |
| `po2` | lab code `50821`, Quantity value | `DOUBLE` |
| `pco2` | lab code `50818`, Quantity value | `DOUBLE` |
| `fio2_chartevents` | chart code `223835`, Quantity value after chart normalization and window selection | `FLOAT` |
| `fio2` | lab code `50816`, Quantity value after source percent/fraction normalization | `DOUBLE` |
| `aado2` | lab code `50801`, Quantity value | `DOUBLE` |
| `aado2_calc` | derived from `po2`, `pco2`, and lab FiO2 first, chart FiO2 fallback: rounded to 4 decimal places | `DECIMAL(38,4)` |
| `pao2fio2ratio` | derived from `po2` and lab FiO2 first, chart FiO2 fallback | `DOUBLE` |
| `ph` | lab code `50820`, Quantity value | `DOUBLE` |
| `baseexcess` | lab code `50802`, Quantity value | `DOUBLE` |
| `bicarbonate` | lab code `50803`, Quantity value | `DOUBLE` |
| `totalco2` | lab code `50804`, Quantity value | `DOUBLE` |
| `hematocrit` | lab code `50810`, Quantity value with `<=100` pivot condition | `DOUBLE` |
| `hemoglobin` | lab code `50811`, Quantity value | `DOUBLE` |
| `carboxyhemoglobin` | lab code `50805`, Quantity value | `DOUBLE` |
| `methemoglobin` | lab code `50814`, Quantity value | `DOUBLE` |
| `chloride` | lab code `50806`, Quantity value | `DOUBLE` |
| `calcium` | lab code `50808`, Quantity value | `DOUBLE` |
| `temperature` | lab code `50825`, Quantity value | `DOUBLE` |
| `potassium` | lab code `50822`, Quantity value | `DOUBLE` |
| `sodium` | lab code `50824`, Quantity value | `DOUBLE` |
| `lactate` | lab code `50813`, Quantity value with `<=10000` pivot condition | `DOUBLE` |
| `glucose` | lab code `50809`, Quantity value with `<=10000` pivot condition | `DOUBLE` |

## Probe counts and oracle checks

The authoritative Delta probe found 23,992 targeted Observation coding rows:
8,706 lab rows and 15,286 chart rows. Every row had a non-null code system,
code, display, and dateTime effective value. The per-code total / Quantity /
string counts were:

```text
lab 50801 28/28/0    50802 889/889/0  50803 13/13/0   50804 889/889/0
    50805 7/7/0      50806 101/101/0  50808 509/509/0 50809 262/260/2
    50810 143/143/0  50811 143/143/0  50813 758/758/0 50814 6/6/0
    50815 19/19/0    50816 137/137/0 50817 223/223/0 50818 889/889/0
    50819 130/130/0  50820 966/966/0  50821 889/889/0 50822 302/302/0
    50823 28/28/0    50824 141/141/0  50825 201/201/0 52033 1033/0/1033
chart 220277 13540/13540/0  223835 1746/1746/0
```

DuckDB demo checks against the raw source gave the same counts for every
target lab item and both chart items. For all 8,706 target lab rows, the
Specimen identifier/itemid join was one-to-one and exact (8,706/8,706); the
following raw fields also agreed exactly: subject ID 8,706/8,706, charttime
8,706/8,706, Quantity/value numeric including NULLs 8,706/8,706, and the
52033 specimen string 1,033/1,033. The direct hospital Encounter identifier
matched source `hadm_id` 8,024/8,024 among non-null FHIR encounter links; the
682 missing links were source-null `hadm_id` rows. The chart resource probe
materialized all 15,286 source chart rows with the expected code/time/value
paths and ICU Encounter references.

The focused re-probe separately counted code `52033` as 1,033 total,
1,033/1,033 non-null `value_string`, 0 quantity, 1,033 dateTime effective,
0 Period effective, 0 data-absent-reason, and 0 literal `___` strings in the
demo Delta. The DuckDB source had 1,033/1,033 non-null `value`, 0
`valuenum`-populated rows, 1,033 non-null `comments`, and 1,033 comments equal
to `___`; the specimen value join agreed exactly 1,033/1,033 with no missing or
extra specimen ids. This is why the FHIR string path remains the mapping, but
the marker must be normalized for the full-data exception identified in
attempt 0003.

The broader mapped-field count check was: lab `Observation` 8,706 rows with
resource key 8,706, patient key 8,706, specimen key 8,706, encounter key 8,024,
dateTime 8,706, Period 0, Quantity value 7,671, Quantity unit/code 7,312
each, string value 1,035, and code system/code/display 8,706 each; chart
`Observation` 15,286 rows with resource/patient/encounter/effective/code fields
15,286 each, Quantity value 15,286, unit/code 13,540 each, and no specimen or
string values. The corresponding DuckDB source counts were lab 8,706 total:
`subject_id`/`specimen_id`/`itemid`/`charttime`/`storetime` 8,706,
`hadm_id` 8,024, `value` 8,704, `valuenum` 7,671, `valueuom` 7,314,
`comments` 1,691; chart 15,286 total with every mapped source field non-null.

## Gaps and execution caveats

* **Unkeyed comparison:** the final candidate has no safe key. Do not add a
  synthetic key or join SpO2/FiO2 by `(subject_id, charttime)`; aggregate and
  compare as the manifest's full-tuple multiset.
* **Lab Encounter incompleteness:** this is an intrinsic nullable join. Use a
  left join. On the demo it does not lose a non-null source `hadm_id`; if a
  full-data row has a non-null source admission but no FHIR Encounter link,
  exact recovery is absent from that Observation. A patient-plus-time join to
  hospital Encounter is a fallback heuristic and can be ambiguous; it was not
  needed for the demonstrated 8,706-row mapping.
* **Absent but derivable:** `specimen_id` is not a final output column, but it
  is exactly derivable for grouping through `Observation.specimen` and
  `Specimen.identifier`; no information gap.
* **Dropped source fields:** `storetime`, `specimen_id`, relational
  `labevents.comments`, item 50807 `value`, `o2flow`/50815, `peep`/50819, and
  `requiredo2`/50823 are not in the oracle output. They are not candidate
  columns. Item 50807 has zero demo source/FHIR rows and no `d_labitems` entry.
  `labevents.comments` is particularly important: the ETL can place it in
  `Observation.valueString` only when numeric and source text are absent, but
  FHIR does not preserve that provenance. For the diagnosed `___` marker,
  `NULLIF(value_string, '___')` is the measured correction to canonical
  `labevents.value`.
* **No terminology translation:** all bg item codes are proprietary MIMIC
  lab/chart systems. The coding fields are CodeableConcept projections that
  should be retained, but there is no relational LOINC mapping to resolve.
* **Type caveat:** keep FHIR extraction aliases as strings until the final SQL
  cast. In particular, use `TIMESTAMP_NTZ` for dateTime strings, cast numeric
  Quantity values to `DOUBLE`, cast identifiers to `INTEGER`, cast chart FiO2
  to `FLOAT`, and explicitly produce `DECIMAL(38,4)` for `aado2_calc`.

## Fresh focused re-probe during attempt 0004 analysis re-entry

The reusable mapping above was rechecked rather than trusted. The fresh probe
used embedded Pathling 9.6.0 on Spark 4.0.2 over
`/Users/nau025/warehouses/mimic-iv-demo/delta`; no HTTP server was used and no
ViewDefinition or concept SQL was authored.

### Resource/profile/base-binding checks

The authoritative Delta resource totals were Observation 813,540, Specimen
12,458, Patient 100, and Encounter 637. For the exact source item sets, the
base-binding cross-tab was:

```text
lab system    8,706 rows  -> mimic-observation-labevents profile 8,706/8,706
chart system 15,286 rows  -> mimic-observation-chartevents profile 15,286/15,286
target total 23,992 rows; system/code/display non-null 23,992/23,992 each
```

The lab code totals were 50801 28, 50802 889, 50803 13, 50804 889, 50805 7,
50806 101, 50808 509, 50809 262, 50810 143, 50811 143, 50813 758, 50814 6,
50815 19, 50816 137, 50817 223, 50818 889, 50819 130, 50820 966, 50821 889,
50822 302, 50823 28, 50824 141, 50825 201, and 52033 1,033; 50807 was zero.
The chart totals were 220277 13,540 and 223835 1,746. These reproduce the
source DuckDB item counts exactly.

The portable discriminators remain the base bindings, not `meta.profile`:
`.../CodeSystem/mimic-d-labitems` for lab and
`.../CodeSystem/mimic-chartevents-d-items` for chart. The target profile check
is evidence for this Delta only; the shared merged-profile quirk in
`MIMIC_NOTES.md` still rules out profile filtering in the implementation.

### Fresh path counts and materialized types

The canonical path projections were materialized with resource keys,
reference keys, identifier values, code coding (`code`, `system`, `display`),
`(value).ofType(Quantity).value/unit/code`, `(value).ofType(string)`, and all
three effective variants. The materialized aliases were `VARCHAR` for keys,
identifier strings, codes, effective dateTime, and Quantity value; `Quantity`
is semantically decimal but its ViewDefinition value alias is string-like and
must be cast. The raw encoded `valueQuantity.value` field was
`DecimalType(32,6)`.

For lab targets (8,706 total), non-null counts were: observation key 8,706,
patient key 8,706, specimen key 8,706, encounter key 8,024,
`effective_datetime` 8,706, `effective_period_start` 0,
`effective_instant` 0, Quantity value 7,671, Quantity unit/code 7,312 each,
and string value 1,035. For chart targets (15,286 total), observation key,
patient key, encounter key, effective dateTime, Quantity value, code, system,
and display were 15,286/15,286; Period start, instant, and string value were
0/15,286. The target `effective` field is therefore dateTime-only, but the
polymorphic aliases remain useful evidence and must not be confused with
populated data.

The identifier/reference joins were checked by UUID keys: Patient 100/100
resource keys and patient identifiers; Specimen 12,458/12,458 resource keys
and 11,122/12,458 lab identifiers; hospital Encounter 637/637 resource keys
and 275/637 hospital identifiers. All 8,706 targeted lab observations joined
to Patient and Specimen. Lab Encounter join coverage was 8,024/8,706, exactly
the source non-null `hadm_id` count; it must remain a left join.

The specimen grouping spine was checked against DuckDB by `(specimen_id,itemid)`:
8,706 source rows, 8,706 FHIR rows, 8,706 unique keys, and exact agreement on
subject ID, specimen ID, hospital ID including NULLs, charttime, and numeric
value (8,706/8,706 for each). The target had 1,257 distinct specimen IDs on
both sides. This confirms grouping through
`Observation.specimen.getReferenceKey(Specimen)` → the lab Specimen identifier,
not patient/time.

The two ICU chart streams had 15,286 rows and exact per-code counts and values
against DuckDB. A fresh check also exposed the already dataset-wide DST-gap
transformation: source 02:00 SpO2 rows for subjects 10003400 and 10035631 are
written at FHIR 03:00, colliding with their source 03:00 rows. Thus the chart
stream has 15,286 rows but only 15,284 distinct
`(subject_id,itemid,effective_datetime)` keys; this is not a source filter or
join error and is covered by the sharpened `MIMIC_NOTES.md` entry.

### Focused 52033 comments-fallback check

The fresh code-52033 probe returned 1,033/1,033 string values, 0 Quantity
values, 1,033/1,033 dateTime values, 0 Period/instant values, and 0 literal
`___` strings. DuckDB returned 1,033 rows with source `value` non-null in
1,033/1,033, `valuenum` non-null in 0/1,033, `comments` non-null in 1,033/1,033,
and `comments='___'` in 1,033/1,033. The values agreed 1,033/1,033. The full
data exception remains the known ETL comments fallback: normalize the FHIR
string with `NULLIF(value_string, '___')` for the source 52033 specimen pivot;
there is no FHIR path for relational `comments` provenance.

This fresh probe sharpens the existing carryover by recording the raw and
materialized datatypes, the 15,284 effective-time collision count, and the
resource/profile/base-binding totals. It does not change the literal itemids,
27-column output shape, canonical paths, or left-join/grouping decisions above.
