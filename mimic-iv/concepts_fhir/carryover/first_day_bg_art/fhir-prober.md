# FHIR probe and mapping: `first_day_bg_art`

**Concept:** `firstday/first_day_bg_art`  
**Source analysis:** `carryover/first_day_bg_art/source-analyst.md`  
**Probed:** 2026-08-20  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, embedded
Pathling 9.6.0 / Spark 4.0.2. No HTTP Pathling server was used.

## Manifest and source boundary

The full oracle manifest declares 44 compared columns, `comparison:
keyed_join`, natural key `stay_id`, required opaque key columns
`icu_encounter_key` and `patient_key`, and 73,181 full-data rows. The compared
columns are:

| Column | Manifest type |
|---|---|
| `subject_id`, `stay_id` | `INTEGER` |
| `lactate_min`, `lactate_max`, `ph_min`, `ph_max`, `so2_min`, `so2_max`, `po2_min`, `po2_max`, `pco2_min`, `pco2_max` | `DOUBLE` |
| `aado2_min`, `aado2_max` | `DOUBLE` |
| `aado2_calc_min`, `aado2_calc_max` | `DECIMAL(38,4)` |
| `pao2fio2ratio_min`, `pao2fio2ratio_max`, `baseexcess_min`, `baseexcess_max`, `bicarbonate_min`, `bicarbonate_max`, `totalco2_min`, `totalco2_max` | `DOUBLE` |
| `hematocrit_min`, `hematocrit_max`, `hemoglobin_min`, `hemoglobin_max`, `carboxyhemoglobin_min`, `carboxyhemoglobin_max`, `methemoglobin_min`, `methemoglobin_max` | `DOUBLE` |
| `temperature_min`, `temperature_max`, `chloride_min`, `chloride_max`, `calcium_min`, `calcium_max`, `glucose_min`, `glucose_max`, `potassium_min`, `potassium_max`, `sodium_min`, `sodium_max` | `DOUBLE` |

The candidate must additionally emit the two manifest `key_columns` as
unmodified, type-prefixed FHIR resource keys. They are Spark `STRING`/
`VARCHAR`, not manifest integer columns:

* `patient_key`: `Patient/<opaque-id>`
* `icu_encounter_key`: `Encounter/<opaque-id>`

The source query has one relation, `mimiciv_icu.icustays`, and one completed
derived dependency, `mimiciv_derived.bg`. The target must consume the completed
dependency as the unqualified Spark view `bg`; it must not rederive the
labevents/chartevents producer or inline `measurement/bg.sql`.

## ICU Encounter stream probe

`mimiciv_icu.icustays` maps to FHIR `Encounter`, selecting the ICU stream by
the exact identifier system
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`. Do not use
`Encounter.class`: all three Encounter streams share the table and class does
not discriminate them.

The exact canonical ViewDefinition extraction paths are:

```json
{
  "resourceType": "ViewDefinition",
  "resource": "Encounter",
  "select": [{
    "column": [
      {"path": "getResourceKey()", "name": "icu_encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"},
      {"path": "period.start", "name": "intime_datetime"}
    ]
  }]
}
```

The source `subject_id` is reached through the patient reference; it is not
the resource key. The companion Patient view is:

```json
{
  "resourceType": "ViewDefinition",
  "resource": "Patient",
  "select": [{
    "column": [
      {"path": "getResourceKey()", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
    ]
  }]
}
```

`getResourceKey()` and `getReferenceKey(Patient)` are opaque FHIR key
strings. `identifier.value` is FHIR `string`, materialized as `VARCHAR`; the
final SQL must cast `subject_id_str` and `stay_id_str` to manifest `INTEGER`.
`period.start` is FHIR `dateTime`, materialized by Pathling as an ISO string
with an offset; the final SQL must use `TRY_CAST(intime_datetime AS
TIMESTAMP_NTZ)` (not an offset-aware timestamp conversion).

### Source-column mapping

| MIMIC source column / required output | Canonical `{path, name}` mapping | FHIR type / observed type | Final target/use type |
|---|---|---|---|
| `icustays.subject_id` | ICU Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` joined by equality to Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `Reference(Patient)` and `Identifier.value` `string`; both `VARCHAR` aliases | `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; retain `patient_key` |
| `icustays.stay_id` | ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | `Identifier.value` `string` / `VARCHAR` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; manifest natural key |
| `icustays.intime` | ICU Encounter `{path: "period.start", name: "intime_datetime"}` | FHIR `dateTime`, materialized `string` / `VARCHAR` | `TRY_CAST(intime_datetime AS TIMESTAMP_NTZ)` for the inclusive `[-6 hours,+1 day]` join window |
| required ICU Encounter resource key | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque resource key `string` / `VARCHAR`, including `Encounter/` prefix | emit verbatim as required key column; never cast, strip, parse, or regenerate |
| required Patient resource key | ICU Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` (byte-equal to Patient `getResourceKey()`) | opaque reference key `string` / `VARCHAR`, including `Patient/` prefix | emit verbatim as required key column and use for the `bg` join |

The ICU stream probe materialized 637 Encounter resources before filtering and
140 after `stay_id_str IS NOT NULL`. For the 140-row ICU stream, counts were:

* `icu_encounter_key`: 140/140 non-null; 140 distinct; all values had the
  `Encounter/` prefix.
* `patient_key`: 140/140 non-null; the equality join retained all 140 ICU
  resource rows (a patient can have more than one stay, so this is not a claim
  of 140 distinct patients).
* `stay_id_str`: 140/140 non-null; 140 distinct.
* `intime_datetime`: 140/140 non-null.

The companion Patient projection had 100/100 `patient_key` and 100/100
`subject_id_str` non-null. The ICU-to-Patient equality join had
`subject_id_str` populated for 140/140 ICU rows.

The exact DuckDB check was `SELECT subject_id, stay_id, intime FROM
mimiciv_icu.icustays` joined to the collected FHIR projection on
`(subject_id, stay_id)`: 140/140 source rows joined, `subject_id` 140/140
exact, `stay_id` 140/140 exact, and `intime` 140/140 exact in the demo.

## Completed dependency `bg`

The completed `bg` state is `COMPLETED_WITH_DIVERGENCE` (attempt 0007). Its
manifest declares 27 compared columns and key columns `encounter_key` and
`patient_key`; the published dependency shape is obtained by applying the
normal export identifier strip. Therefore `FROM bg` exposes the following
25 retained data columns plus the two resource keys:

| Published `bg` column | Published / observed type | Demo non-null count (of 889) | Consumer use |
|---|---:|---:|---|
| `charttime` | `TIMESTAMP` / Spark `timestamp_ntz` | 889 | inclusive temporal window |
| `specimen` | `VARCHAR` / Spark `string` | 872 | exact literal filter `ART.` |
| `so2` | `DOUBLE` / Spark `double` | 179 | `so2_min`, `so2_max` |
| `po2` | `DOUBLE` / Spark `double` | 889 | `po2_min`, `po2_max` |
| `pco2` | `DOUBLE` / Spark `double` | 889 | `pco2_min`, `pco2_max` |
| `aado2` | `DOUBLE` / Spark `double` | 28 | `aado2_min`, `aado2_max` |
| `aado2_calc` | `DECIMAL(38,4)` / Spark `decimal(38,4)` | 563 | `aado2_calc_min`, `aado2_calc_max` |
| `pao2fio2ratio` | `DOUBLE` / Spark `double` | 563 | `pao2fio2ratio_min`, `pao2fio2ratio_max` |
| `baseexcess` | `DOUBLE` / Spark `double` | 889 | `baseexcess_min`, `baseexcess_max` |
| `bicarbonate` | `DOUBLE` / Spark `double` | 2 | `bicarbonate_min`, `bicarbonate_max` |
| `totalco2` | `DOUBLE` / Spark `double` | 889 | `totalco2_min`, `totalco2_max` |
| `hematocrit` | `DOUBLE` / Spark `double` | 133 | `hematocrit_min`, `hematocrit_max` |
| `hemoglobin` | `DOUBLE` / Spark `double` | 133 | `hemoglobin_min`, `hemoglobin_max` |
| `carboxyhemoglobin` | `DOUBLE` / Spark `double` | 7 | `carboxyhemoglobin_min`, `carboxyhemoglobin_max` |
| `methemoglobin` | `DOUBLE` / Spark `double` | 6 | `methemoglobin_min`, `methemoglobin_max` |
| `temperature` | `DOUBLE` / Spark `double` | 188 | `temperature_min`, `temperature_max` |
| `chloride` | `DOUBLE` / Spark `double` | 90 | `chloride_min`, `chloride_max` |
| `calcium` | `DOUBLE` / Spark `double` | 438 | `calcium_min`, `calcium_max` |
| `glucose` | `DOUBLE` / Spark `double` | 227 | `glucose_min`, `glucose_max` |
| `potassium` | `DOUBLE` / Spark `double` | 230 | `potassium_min`, `potassium_max` |
| `sodium` | `DOUBLE` / Spark `double` | 112 | `sodium_min`, `sodium_max` |
| `lactate` | `DOUBLE` / Spark `double` | 535 | `lactate_min`, `lactate_max` |
| `patient_key` | opaque `VARCHAR` / Spark `string` | 889 | replacement for source `bg.subject_id` join |
| `encounter_key` | opaque `VARCHAR` / Spark `string` | 837 | available dependency key; not consumed here |

The producer's source output names `subject_id` and `hadm_id`, but both are
removed from the published dependency because the paired resource keys are
present. They are not valid columns to reference from the consumer's `FROM
bg`. The source predicate `ie.subject_id = bg.subject_id` must therefore be
implemented semantically as the permitted opaque-key equality
`icu.patient_key = bg.patient_key`. Do not join on `bg.hadm_id`, which is also
absent, and do not regenerate or parse a UUID.

The dependency probe found 889 rows, 706 rows with `specimen = 'ART.'`, 133
`VEN.`, 22 `MIX.`, 11 `CENTRAL VENOUS.`, and 17 NULL. The exact consumer
literal is not a FHIR `CodeableConcept` and has no `code.coding.system`; it is
a dependency `VARCHAR` discriminator inherited from the producer's specimen
text. Thus the consumer has no FHIR coded filter or coding-per-resource ratio
to report. The producer's itemid/system filters remain entirely inside the
completed `bg` dependency.

The demo temporal probe using the published dependency found 1,577 joined
same-patient ICU/BG pairs before the consumer window, 346 arterial rows in the
inclusive window, and 76 of 140 ICU stays with at least one matching arterial
row. The LEFT JOIN retains all 140 ICU stays.

## Final output mapping and key requirements

The 42 extrema columns have no individual FHIR element path: each is a
`MIN`/`MAX` aggregate over the named published `bg` numeric column after the
`specimen = 'ART.'` and `charttime` window predicates. Their manifest types are
`DOUBLE`, except both `aado2_calc_*` columns, which must remain
`DECIMAL(38,4)`. The output mapping is:

```text
{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}
  -> CAST(... AS INTEGER) AS subject_id
{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}
  -> CAST(... AS INTEGER) AS stay_id
{path: "getResourceKey()", name: "icu_encounter_key"}
  -> emit verbatim beside stay_id
{path: "subject.getReferenceKey(Patient)", name: "patient_key"}
  -> emit verbatim beside subject_id and join to bg.patient_key
```

The aggregate must group at ICU-stay grain. Grouping by `stay_id` is the
manifest natural key; retaining `patient_key` and `icu_encounter_key` in the
group/output is required for the published derived shape. Do not use a
resource key as `stay_id`, and do not drop either required key at the outermost
projection.

## Representability and gaps

* `subject_id`, `stay_id`, and the ICU resource key are representable. The
  identifier values and reference/resource keys were complete on all 140 demo
  ICU rows, and the opaque keys are used only for equality joins and
  provenance.
* ICU `intime` is carried by `Encounter.period.start`, but the upstream ICU
  ETL writes `CAST(icu.intime AS TIMESTAMPTZ)`. A source wall time in a DST
  spring-forward gap is not recoverable from the normalized FHIR dateTime;
  parsing or inverting the resource UUID is forbidden. This is a
  **not-representable-on-the-affected-rows** gap, not a reason to NULL all
  `intime`: the surviving `period.start` is the only faithful value available.
  The authoritative demo comparison reached 0/140 affected ICU starts and
  140/140 exact `intime` values. On full data, the field is potentially
  essential because a one-hour change can move a `bg` row across either
  inclusive window boundary and change every affected extrema column; the
  target-specific affected-row count must be measured by the full comparison.
  The curated DST policy treats this known upstream normalization as an
  intrinsic divergence rather than an ID-based recovery or a typed-NULL
  substitution.
* The completed `bg` dependency already carries its own known lab datetime
  normalization gap. Its full attempt 0007 had 70/511,637 dependency rows in
  the accepted residual; the demo `first_day_bg_art` aggregate matched the
  source oracle for all 140 stays after numeric decimal-scale normalization.
  This consumer must inherit the completed dependency result, not try to
  recover the discarded source wall time. Whether any full-data dependency
  rows cross this consumer's ICU window is a target-level comparison question.
* `icustays.los`, `outtime`, care units, and `hadm_id` are not consumed by this
  source SQL. Their omission from the FHIR mapping is therefore not a gap for
  this concept. In particular, do not add a hospital Encounter join merely to
  obtain an unused `hadm_id`.

## Verification summary

The probe registered the completed `bg` attempt-0007 ViewDefinitions, applied
the same published identifier strip used by dependency preprocessing, and
materialized the `bg` Spark temp view. It materialized ICU Encounter and
Patient projections with the paths above, counted every mapped input, and
compared the ICU projection to the DuckDB demo oracle. A Spark aggregate using
the published `bg` view produced 140 rows; keyed comparison to
`mimiciv_derived.first_day_bg_art` produced 140/140 matching stay keys and
semantic agreement on all 44 output values (the two DECIMAL columns compare
exactly after normalizing DuckDB's display scale; candidate schema is exactly
`DECIMAL(38,4)`).

No new dataset/IG-level quirk was established, so no section was appended to
`MIMIC_NOTES.d/first_day_bg_art.md`.
