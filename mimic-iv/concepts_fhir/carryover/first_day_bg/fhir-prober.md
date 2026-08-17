# FHIR probe and mapping: `first_day_bg`

**Concept:** `firstday/first_day_bg`  
**Attempt:** `0001`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/first_day_bg/source-analyst.md`  
**Probe date:** 2026-08-17  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2; no HTTP server and no
ndjson were used.  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (read-only)  
**Manifest:** 44 columns, 73,181 full-data rows, keyed by `stay_id`.

## Scope and resource mapping

The direct source table is `mimiciv_icu.icustays`.  Its FHIR resource is the
ICU `Encounter` stream selected by the identifier system
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`.  The patient spine
is `Patient`, joined through the ICU Encounter `subject` reference.  The
consumer does not read raw lab or chart tables: the completed `bg` dependency
attempt (`mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0006/`) was
materialised and its final result was exposed as the unqualified Spark temp
view `bg`, exactly as the dependency interface requires.

The authoritative Delta `Encounter` table has 637 resources.  Identifier
system counts were hospital 275, ICU 140, and ED 222.  The selected ICU view
therefore has 140 rows, one per demo `icustays` row.  `Encounter.class` was not
used: it does not discriminate these streams.  The source SQL has no literal
item/code filter; the ICU identifier system is a stream discriminator, not a
terminology code set.

## Canonical identifier and time projections

These are extraction mappings, not final output types.  FHIR identifier values
and resource/reference keys are strings.  The final SQL must cast
`subject_id_str` and `stay_id_str` to `INTEGER`; keys are used only for equality
joins.  No resource id is parsed, regenerated, hashed, hardcoded, or used to
infer a source value.

### Patient

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

| Mapping | FHIR type | Materialized type | Rows / non-null |
|---|---|---|---:|
| `Patient.getResourceKey()` → `patient_key` | opaque resource key string | `string` | 100 / 100 |
| `Patient.identifier.where(system='.../identifier/patient').value` → `subject_id_str` | `string` | `string` | 100 / 100 |

### ICU Encounter

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "period.start", "name": "period_start" }
  ]
}
```

Append this constrained identifier group to select only ICU stays:

```json
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    { "path": "system", "name": "identifier_system" },
    { "path": "value", "name": "stay_id_str" }
  ]
}
```

| Source column | Canonical FHIR extraction (`{path, name}`) | FHIR type | Materialized type | Rows / non-null | Final type |
|---|---|---|---|---:|---|
| `icustays.stay_id` | `{path: "value", name: "stay_id_str"}` inside the ICU `identifier` group | `string` | `string` | 140 / 140 | `INTEGER` |
| `icustays.subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` joined to Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `Reference(Patient)` plus `string` | `string` | 140 / 140 through the join; Patient 100 / 100 | `INTEGER` |
| `icustays.intime` | `{path: "period.start", name: "period_start"}` | `dateTime` | `string` with ISO offset | 140 / 140 | `TIMESTAMP_NTZ` |
| ICU Encounter resource join | `{path: "getResourceKey()", name: "encounter_key"}` | opaque resource key string | `string` | 140 / 140 | join-only |

All 140 ICU `stay_id_str` values were distinct.  The 140 ICU Encounter
`patient_key` values joined to Patient identifiers, and a DuckDB comparison of
the extracted/cast `(subject_id, stay_id, intime)` spine against
`mimiciv_icu.icustays` was exact for 140/140 rows.

## Dependency interface: unqualified `bg`

The dependency was not re-derived.  The completed `bg` attempt's five FHIR
views and SQL were executed with embedded Pathling, then the resulting 27
column DataFrame was registered as the unqualified temp view `bg`.  Its demo
shape was 889 rows with this exact Spark schema:

```text
subject_id:int, hadm_id:int, charttime:timestamp_ntz, specimen:string,
so2:double, po2:double, pco2:double, fio2_chartevents:float, fio2:double,
aado2:double, aado2_calc:decimal(38,4), pao2fio2ratio:double, ph:double,
baseexcess:double, bicarbonate:double, totalco2:double, hematocrit:double,
hemoglobin:double, carboxyhemoglobin:double, methemoglobin:double,
chloride:double, calcium:double, temperature:double, potassium:double,
sodium:double, lactate:double, glucose:double
```

`first_day_bg` reads only `bg.subject_id`, `bg.charttime`, and the 21
measurement columns below.  `bg.hadm_id`, `bg.specimen`,
`bg.fio2_chartevents`, and `bg.fio2` are not read by this consumer.

The FHIR provenance paths for direct `bg` values are the completed dependency's
lab Observation Quantity projection
`{path: "(value).ofType(Quantity).value", name: "quantity_value"}` under
the lab code system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`; `bg.charttime`
`{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` after
the dependency's wall-clock `TIMESTAMP_NTZ` cast.  `bg.subject_id` is the
Patient identifier projection above.  The dependency owns its literal itemid
filters; this consumer adds none.

| Dependency column | FHIR/source provenance | Dependency FHIR/served type | `bg` rows / non-null | Consumer output |
|---|---|---|---:|---|
| `bg.subject_id` | Patient patient identifier value via Observation `subject` reference | `string` → `INTEGER` in `bg` | 889 / 889 | join predicate |
| `bg.charttime` | lab Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` → `timestamp_ntz` | 889 / 889 | temporal predicate |
| `bg.lactate` | Quantity value, lab code `50813` | `decimal` extraction → `DOUBLE` | 535 / 535 | `lactate_min`, `lactate_max` |
| `bg.ph` | Quantity value, lab code `50820` | `decimal` extraction → `DOUBLE` | 889 / 889 | `ph_min`, `ph_max` |
| `bg.so2` | Quantity value, lab code `50817` | `decimal` extraction → `DOUBLE` | 179 / 179 | `so2_min`, `so2_max` |
| `bg.po2` | Quantity value, lab code `50821` | `decimal` extraction → `DOUBLE` | 889 / 889 | `po2_min`, `po2_max` |
| `bg.pco2` | Quantity value, lab code `50818` | `decimal` extraction → `DOUBLE` | 889 / 889 | `pco2_min`, `pco2_max` |
| `bg.aado2` | Quantity value, lab code `50801` | `decimal` extraction → `DOUBLE` | 28 / 28 | `aado2_min`, `aado2_max` |
| `bg.aado2_calc` | dependency calculation from mapped PO2/PCO2 and lab FiO2, with chart FiO2 fallback | derived `DECIMAL(38,4)` | 563 / 563 | `aado2_calc_min`, `aado2_calc_max` |
| `bg.pao2fio2ratio` | dependency calculation from mapped PO2 and lab/chart FiO2 | derived `DOUBLE` | 563 / 563 | `pao2fio2ratio_min`, `pao2fio2ratio_max` |
| `bg.baseexcess` | Quantity value, lab code `50802` | `decimal` extraction → `DOUBLE` | 889 / 889 | `baseexcess_min`, `baseexcess_max` |
| `bg.bicarbonate` | Quantity value, lab code `50803` | `decimal` extraction → `DOUBLE` | 2 / 2 | `bicarbonate_min`, `bicarbonate_max` |
| `bg.totalco2` | Quantity value, lab code `50804` | `decimal` extraction → `DOUBLE` | 889 / 889 | `totalco2_min`, `totalco2_max` |
| `bg.hematocrit` | Quantity value, lab code `50810` | `decimal` extraction → `DOUBLE` | 133 / 133 | `hematocrit_min`, `hematocrit_max` |
| `bg.hemoglobin` | Quantity value, lab code `50811` | `decimal` extraction → `DOUBLE` | 133 / 133 | `hemoglobin_min`, `hemoglobin_max` |
| `bg.carboxyhemoglobin` | Quantity value, lab code `50805` | `decimal` extraction → `DOUBLE` | 7 / 7 | `carboxyhemoglobin_min`, `carboxyhemoglobin_max` |
| `bg.methemoglobin` | Quantity value, lab code `50814` | `decimal` extraction → `DOUBLE` | 6 / 6 | `methemoglobin_min`, `methemoglobin_max` |
| `bg.temperature` | Quantity value, lab code `50825` | `decimal` extraction → `DOUBLE` | 188 / 188 | `temperature_min`, `temperature_max` |
| `bg.chloride` | Quantity value, lab code `50806` | `decimal` extraction → `DOUBLE` | 90 / 90 | `chloride_min`, `chloride_max` |
| `bg.calcium` | Quantity value, lab code `50808` | `decimal` extraction → `DOUBLE` | 438 / 438 | `calcium_min`, `calcium_max` |
| `bg.glucose` | Quantity value, lab code `50809` | `decimal` extraction → `DOUBLE` | 227 / 227 | `glucose_min`, `glucose_max` |
| `bg.potassium` | Quantity value, lab code `50822` | `decimal` extraction → `DOUBLE` | 230 / 230 | `potassium_min`, `potassium_max` |
| `bg.sodium` | Quantity value, lab code `50824` | `decimal` extraction → `DOUBLE` | 112 / 112 | `sodium_min`, `sodium_max` |

The dependency is the source of truth for the two calculated fields.  The
consumer must use `bg.aado2_calc` and `bg.pao2fio2ratio` as supplied rather
than re-deriving them from other dependency columns.

## Join, temporal window, and grain

The probed consumer shape was equivalent to:

```sql
WITH icu AS (
  SELECT CAST(p.subject_id_str AS INTEGER) AS subject_id,
         CAST(e.stay_id_str AS INTEGER) AS stay_id,
         CAST(e.period_start AS TIMESTAMP_NTZ) AS intime
  FROM icu_encounter e
  JOIN patient p ON e.patient_key = p.patient_key
)
SELECT icu.subject_id, icu.stay_id,
       MIN(bg.lactate) AS lactate_min, MAX(bg.lactate) AS lactate_max,
       -- MIN/MAX for the remaining 20 mapped measurement columns
FROM icu
LEFT JOIN bg
  ON icu.subject_id = bg.subject_id
 AND bg.charttime >= icu.intime - INTERVAL 6 HOURS
 AND bg.charttime <= icu.intime + INTERVAL 1 DAY
GROUP BY icu.subject_id, icu.stay_id
```

The bounds are inclusive and span 30 hours: `[intime - 6 hours,
intime + 24 hours]`.  The Delta probe counted 1,577 same-subject
Encounter/`bg` pairs before the time predicate, 434 pairs after the inclusive
predicate, and 434 strict-interior pairs.  There were 0 lower-boundary and 0
upper-boundary rows in this 100-patient demo, so the inclusive rule is encoded
and checked but has no boundary case in the served sample.  The 434 matched
rows contributed to 95 ICU stays; the `LEFT JOIN` retained all 140 stays, with
45 stays having only aggregate NULLs.

The final probe produced exactly 140 rows and 140 distinct `stay_id` values
(zero duplicate key rows).  The output has 44 columns: `subject_id INTEGER`,
`stay_id INTEGER`, 40 `DOUBLE` min/max columns except
`aado2_calc_min`/`aado2_calc_max`, which are `DECIMAL(38,4)`.  The non-null
counts for each aggregate pair over the 140 output rows were:

| Output pair | Rows / non-null for min | Rows / non-null for max |
|---|---:|---:|
| `lactate` | 140 / 86 | 140 / 86 |
| `ph` | 140 / 95 | 140 / 95 |
| `so2` | 140 / 59 | 140 / 59 |
| `po2` | 140 / 95 | 140 / 95 |
| `pco2` | 140 / 95 | 140 / 95 |
| `aado2` | 140 / 8 | 140 / 8 |
| `aado2_calc` | 140 / 65 | 140 / 65 |
| `pao2fio2ratio` | 140 / 65 | 140 / 65 |
| `baseexcess` | 140 / 95 | 140 / 95 |
| `bicarbonate` | 140 / 1 | 140 / 1 |
| `totalco2` | 140 / 95 | 140 / 95 |
| `hematocrit` | 140 / 41 | 140 / 41 |
| `hemoglobin` | 140 / 41 | 140 / 41 |
| `carboxyhemoglobin` | 140 / 6 | 140 / 6 |
| `methemoglobin` | 140 / 5 | 140 / 5 |
| `temperature` | 140 / 35 | 140 / 35 |
| `chloride` | 140 / 40 | 140 / 40 |
| `calcium` | 140 / 66 | 140 / 66 |
| `glucose` | 140 / 47 | 140 / 47 |
| `potassium` | 140 / 48 | 140 / 48 |
| `sodium` | 140 / 42 | 140 / 42 |

## Final source-column to FHIRPath mapping

The source table → resource mapping is:

| MIMIC-IV source | FHIR resource/interface | Role |
|---|---|---|
| `mimiciv_icu.icustays` | `Encounter` with ICU identifier system | driving ICU-stay row, `stay_id`, `subject_id`, `intime` |
| `mimiciv_icu.icustays.subject_id` | `Patient.identifier` reached through `Encounter.subject` | patient join and final `subject_id` |
| completed `mimiciv_derived.bg` interface | unqualified `bg` temp view | `subject_id`, `charttime`, and the 21 aggregate inputs |

| Source column | Canonical mapping (`{path, name}`) | FHIR/served type | Final target type |
|---|---|---|---|
| `icustays.stay_id` | `{path: "value", name: "stay_id_str"}` in `identifier.where(system='.../encounter-icu')` | `string` | `INTEGER` |
| `icustays.subject_id` | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` → Patient `{path: "identifier.where(system='.../identifier/patient').value", name: "subject_id_str"}` | Reference key + `string` | `INTEGER` |
| `icustays.intime` | `{path: "period.start", name: "period_start"}` | `dateTime` / `string` alias | `TIMESTAMP_NTZ` |
| `bg.subject_id` | dependency output `bg.subject_id`; underlying Patient identifier mapping above | `INTEGER` | join-only |
| `bg.charttime` | dependency output `bg.charttime`; underlying `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `timestamp_ntz` | temporal join |
| `bg.lactate` | dependency output; lab Quantity value code `50813` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.ph` | dependency output; lab Quantity value code `50820` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.so2` | dependency output; lab Quantity value code `50817` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.po2` | dependency output; lab Quantity value code `50821` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.pco2` | dependency output; lab Quantity value code `50818` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.aado2` | dependency output; lab Quantity value code `50801` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.aado2_calc` | dependency output calculation from mapped Quantity values | `DECIMAL(38,4)` | `MIN`/`MAX` `DECIMAL(38,4)` |
| `bg.pao2fio2ratio` | dependency output calculation from mapped Quantity values | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.baseexcess` | dependency output; lab Quantity value code `50802` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.bicarbonate` | dependency output; lab Quantity value code `50803` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.totalco2` | dependency output; lab Quantity value code `50804` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.hematocrit` | dependency output; lab Quantity value code `50810` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.hemoglobin` | dependency output; lab Quantity value code `50811` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.carboxyhemoglobin` | dependency output; lab Quantity value code `50805` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.methemoglobin` | dependency output; lab Quantity value code `50814` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.temperature` | dependency output; lab Quantity value code `50825` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.chloride` | dependency output; lab Quantity value code `50806` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.calcium` | dependency output; lab Quantity value code `50808` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.glucose` | dependency output; lab Quantity value code `50809` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.potassium` | dependency output; lab Quantity value code `50822` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |
| `bg.sodium` | dependency output; lab Quantity value code `50824` | `DOUBLE` | `MIN`/`MAX` `DOUBLE` |

## Gaps and representability

* No source field used by this consumer was absent in the demo mapping.  The
  ICU identifier, Patient identifier, `Encounter.period.start`, dependency
  `subject_id`/`charttime`, and all 21 measurement inputs were populated at
  the stated row counts.
* `bg.hadm_id`, `bg.specimen`, `bg.fio2_chartevents`, and `bg.fio2` are not
  gaps: they are dependency columns that the source SQL does not read.
* `Encounter.period.start` is the served representation of `icustays.intime`.
  The shared datetime note establishes that the upstream ETL can normalize a
  spring-forward-gap wall time through `TIMESTAMPTZ`; the original wall time
  is then **not representable** by any FHIR query.  In this demo the measured
  loss is 0/140 ICU starts, and the DuckDB spine check was 140/140 exact.  If a
  full-data ICU start is shifted, only `bg` rows at the two temporal-window
  boundaries can change inclusion; the full comparison must count that row
  effect before calling it essential.  This probe does not recommend a
  whole-concept block.
* Resource/reference ids remain opaque identity.  They can support the
  equality joins and stay-level grouping above, but cannot recover an omitted
  `stay_id`, `subject_id`, `intime`, or measurement value.

## Oracle check

The FHIR ICU spine joined to the DuckDB `mimiciv_icu.icustays` table exactly:
140/140 rows agreed on `subject_id`, `stay_id`, and `intime`.  The 44-column
FHIR aggregate was compared with DuckDB `mimiciv_derived.first_day_bg` by
`stay_id`: 140/140 keys, no missing or extra rows, and 140/140 rows exact on
all columns.  The comparison-only projection cast the two decimal aggregate
columns to `DOUBLE` to avoid pandas Decimal-versus-float representation noise;
the actual probed output schema retained `DECIMAL(38,4)`.

## Notes and provisional leads

The established `MIMIC_NOTES.md` entries that changed a mapping decision were:

* MIMIC ids live in `identifier.value` as strings, so `subject_id` and
  `stay_id` use identifier values plus final integer casts, never resource keys.
* Encounter streams are selected by `identifier.system`; `Encounter.class` is
  not a discriminator, so the ICU system filter is mandatory.
* FHIR datetimes carry offsets but represent MIMIC wall-clock values, so
  `period.start` is cast to `TIMESTAMP_NTZ`, not an offset-aware `TIMESTAMP`.
* Resource/reference ids are opaque identity only.

I read the provisional lab/time fragments
`MIMIC_NOTES.d/chemistry.md`, `coagulation.md`,
`complete_blood_count.md`, `blood_differential.md`,
`cardiac_marker.md`, and `icustay_times.md`.  Their leads were checked against
the authoritative Delta probe where relevant: this consumer has no direct
Observation coding filter or Quantity extraction, and its ICU period/time
mapping was checked 140/140 against DuckDB.  No new dataset-wide quirk was
established, so no `MIMIC_NOTES.d/first_day_bg.md` entry was appended.
