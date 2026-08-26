# FHIR prober mapping: `sofa`

**Concept:** `score/sofa.sql`  
**Attempt:** `attempt_0001`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/sofa/source-analyst.md`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Probe engine:** embedded Pathling 9.6.0 / Spark 4.0.2, Spark session timezone UTC  
**Read-only oracle:** `/Users/nau025/warehouses/mimic4-demo.db` (DuckDB 1.5.5)

This is a mapping artifact only. No ViewDefinition or `concept.sql` was
authored. The HTTP Pathling server and raw NDJSON were not used. SOFA must
consume the completed dependency temp views named `bg`, `chemistry`,
`complete_blood_count`, `dobutamine`, `dopamine`, `enzyme`, `epinephrine`,
`gcs`, `icustay_hourly`, `norepinephrine`, `urine_output_rate`, `ventilation`,
and `vitalsign`; it must not inline or rederive any of them.

## Mapping decisions from the source analysis

The only direct raw relation in `sofa.sql` is `mimiciv_icu.icustays`. Its FHIR
equivalent is the ICU `Encounter` stream. The other relations are completed
derived dependencies. The source SQL's direct literals are dependency-output
values, not FHIR `Coding` filters:

| Source predicate | Published dependency field | FHIR type / target type | Probe result |
|---|---|---|---|
| `bg.specimen = 'ART.'` | `bg.specimen` | FHIR-derived string / published `STRING`; target predicate is exact string equality | 706/889 completed `bg` rows; DuckDB oracle 706/889 |
| `vd.ventilation_status = 'InvasiveVent'` | `ventilation.ventilation_status` | derived string / published `STRING` | 61/209 completed `ventilation` rows |
| `hr >= 0` | `icustay_hourly.hr` | generated `BIGINT` | completed demo spine ranges -24 through 488; SOFA retains nonnegative hours |

There are no direct itemid, ICD, or FHIR coding literals in `sofa.sql`.
Transitive itemid filters belong to the completed dependencies and are not to
be copied into SOFA.

## ICU Encounter support and identifier spine

The FHIR-side ICU Encounter support view needs these canonical columns. The
`_str` alias is a FHIR string and must be cast only when an integer MIMIC value
is required. The `_key` aliases are opaque type-prefixed resource/reference
keys and must never be parsed or regenerated.

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').system", "name": "stay_system" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "intime_datetime" },
    { "path": "period.end", "name": "outtime_datetime" }
  ]
}
```

| Source input / purpose | Canonical `{path, name}` | FHIR type | Served/materialized type and use |
|---|---|---|---|
| ICU Encounter identity | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | resource key `string` | `STRING`, `Encounter/<opaque-id>`; equality join and required published key |
| `icustays.subject_id` / dependency patient identity | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` | `STRING`, `Patient/<opaque-id>`; equality only |
| `icustays.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` `string` | `STRING`; `CAST(stay_id_str AS INTEGER)` is `stay_id` |
| ICU stream discriminator | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').system", "name": "stay_system" }` | `Identifier.system` `uri` | `STRING`; filter this exact URI, never `Encounter.class` |
| `icustays.hadm_id` / hospital join | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` on ICU Encounter, then `{ "path": "getResourceKey()", "name": "encounter_key" }` and `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` on the parent hospital Encounter | Encounter reference/resource keys `string`; identifier value `string` | Join lab dependencies by `parent_encounter_key = dependency.encounter_key`; cast `hadm_id_str` only if the numeric intermediate is needed |
| `icustays.intime` | `{ "path": "period.start", "name": "intime_datetime" }` | `Period.start` `dateTime` | ViewDefinition alias `STRING`; direct `TRY_CAST(... AS TIMESTAMP_NTZ)` |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime_datetime" }` | `Period.end` `dateTime` | ViewDefinition alias `STRING`; direct `TRY_CAST(... AS TIMESTAMP_NTZ)` |

Encounter `period.start` and `period.end` are direct `Period` endpoint fields,
not choice fields requiring `.ofType()`. The fresh probe found both populated
on 637/637 Encounters and on 140/140 ICU Encounters. The ICU identifier
system yielded 140 rows/resources; `stay_id_str`, `patient_key`,
`parent_encounter_key`, `period.start`, and `period.end` were each populated
140/140 on the selected stream. Joining the ICU identifier to the DuckDB
oracle gave exact `stay_id` 140/140, parent-derived `hadm_id` 140/140, period
start 140/140, and period end 140/140. The current rebuilt warehouse therefore
has no measured ICU Encounter endpoint loss. The served endpoint aliases still
carry ISO offsets; preserve the MIMIC wall clock with `TIMESTAMP_NTZ`.

The complete Encounter identifier cross-tab was:

| `identifier.system` | rows/resources | `identifier.value` | period start/end | `partOf` |
|---|---:|---:|---:|---:|
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` | 222/222 | 222 | 222/222 | 172 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | 275/275 | 275 | 275/275 | 0 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | 140/140 | 140 | 140/140 | 140 |

`Encounter.class` does not discriminate the streams. A target ICU view must
filter `stay_system` or `stay_id_str IS NOT NULL`, not `icu_encounter_key IS
NOT NULL` and not class.

## Observation support shape for the dependency boundary

SOFA does not query raw Observations directly, but these are the paths used by
the completed Observation dependencies. They explain the FHIR provenance of
the dependency keys and the pafi/ventilation time/value types.

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(effective).ofType(instant)", "name": "effective_instant" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(string)", "name": "value_string" }
  ]
}
```

For a coded Observation dependency, the coding group is the canonical
`forEach` shape, constrained inside the iteration:

```json
{
  "forEach": "code.coding.where(system='<exact-served-system>')",
  "column": [
    { "path": "code", "name": "code" },
    { "path": "system", "name": "system" },
    { "path": "display", "name": "display" }
  ]
}
```

FHIR and served types for those paths are: resource/reference keys are opaque
`STRING`; `Observation.effectiveDateTime` is FHIR `dateTime` and the
ViewDefinition alias is `STRING`; Period endpoints are FHIR `dateTime` and
their aliases are `STRING`; `effective.instant` is FHIR `instant` and
materializes as a native Spark `TIMESTAMP`; Quantity.value is FHIR `decimal`,
raw Delta `DECIMAL(32,6)`, but a ViewDefinition value alias is string-like and
must be cast before arithmetic; Quantity.unit and valueString are strings.
Do not coalesce a string dateTime alias with the unused native instant alias.

The fresh all-Observation coding projection found 813,540 resources/coding
rows partitioned as follows. Every system had exactly one coding per resource.

| `code.coding.system` | coding rows | distinct resources | ratio |
|---|---:|---:|---:|
| `http://loinc.org` | 9,042 | 9,042 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | 668,862 | 668,862 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items` | 24,642 | 24,642 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | 107,727 | 107,727 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-antibiotic` | 1,036 | 1,036 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism` | 338 | 338 | 1.000 |
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-test` | 1,893 | 1,893 | 1.000 |

For the BG transitive dependency, the exact served raw filters are its own
filters, not SOFA filters. They are recorded here so an implementer does not
mistake `bg.specimen` for a coding system:

| source dependency code | served system | coding rows/resources |
|---:|---|---:|
| 52033 | `.../CodeSystem/mimic-d-labitems` | 1,033/1,033 |
| 50801 | `.../CodeSystem/mimic-d-labitems` | 28/28 |
| 50802 | `.../CodeSystem/mimic-d-labitems` | 889/889 |
| 50803 | `.../CodeSystem/mimic-d-labitems` | 13/13 |
| 50804 | `.../CodeSystem/mimic-d-labitems` | 889/889 |
| 50805 | `.../CodeSystem/mimic-d-labitems` | 7/7 |
| 50806 | `.../CodeSystem/mimic-d-labitems` | 101/101 |
| 50807 | `.../CodeSystem/mimic-d-labitems` | 0/0 (dead served filter) |
| 50808 | `.../CodeSystem/mimic-d-labitems` | 509/509 |
| 50809 | `.../CodeSystem/mimic-d-labitems` | 262/262 |
| 50810 | `.../CodeSystem/mimic-d-labitems` | 143/143 |
| 50811 | `.../CodeSystem/mimic-d-labitems` | 143/143 |
| 50813 | `.../CodeSystem/mimic-d-labitems` | 758/758 |
| 50814 | `.../CodeSystem/mimic-d-labitems` | 6/6 |
| 50815 | `.../CodeSystem/mimic-d-labitems` | 19/19 |
| 50816 | `.../CodeSystem/mimic-d-labitems` | 137/137 |
| 50817 | `.../CodeSystem/mimic-d-labitems` | 223/223 |
| 50818 | `.../CodeSystem/mimic-d-labitems` | 889/889 |
| 50819 | `.../CodeSystem/mimic-d-labitems` | 130/130 |
| 50820 | `.../CodeSystem/mimic-d-labitems` | 966/966 |
| 50821 | `.../CodeSystem/mimic-d-labitems` | 889/889 |
| 50822 | `.../CodeSystem/mimic-d-labitems` | 302/302 |
| 50823 | `.../CodeSystem/mimic-d-labitems` | 28/28 |
| 50824 | `.../CodeSystem/mimic-d-labitems` | 141/141 |
| 50825 | `.../CodeSystem/mimic-d-labitems` | 201/201 |
| 220277 | `.../CodeSystem/mimic-chartevents-d-items` | 13,540/13,540 |
| 223835 | `.../CodeSystem/mimic-chartevents-d-items` | 1,746/1,746 |

The 25 lab codes produced 8,706 coding/resource rows and the two chart codes
produced 15,286 coding/resource rows. The combined BG target was 23,992/23,992
codings per resources (1.000). For all 25 lab codes and both chart codes,
`effective_datetime` was populated and `effective_period_start` and
`effective_instant` were 0; the pafi input is therefore a dateTime string that
the completed `bg` dependency has already cast to `TIMESTAMP_NTZ`.

For the ventilation transitive dependencies, the exact chartevents code set
and fresh coded counts were:

| code | rows/resources |
|---:|---:|
| 220339 | 1,447/1,447 |
| 223834 | 1,090/1,090 |
| 223835 | 1,746/1,746 |
| 223848 | 1,292/1,292 |
| 223849 | 1,048/1,048 |
| 224684 | 769/769 |
| 224685 | 1,331/1,331 |
| 224686 | 661/661 |
| 224687 | 1,359/1,359 |
| 224688 | 801/801 |
| 224689 | 1,314/1,314 |
| 224690 | 1,331/1,331 |
| 224691 | 330/330 |
| 224696 | 510/510 |
| 224700 | 490/490 |
| 226732 | 3,145/3,145 |
| 227287 | 145/145 |
| 227582 | 13/13 |
| 229314 | 402/402 |
| **total** | **19,224/19,224; ratio 1.000** |

The exact ventilation system is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
`system + exact code` is the discriminator; `meta.profile` is not. The
completed `ventilation` relation, not these raw observations, supplies
`ventilation_status` and its temporal episode endpoints.

## MedicationAdministration support shape for vasoactive dependencies

The ICU inputevent source maps to `MedicationAdministration`. The served R4
Encounter reference field is `context`, not `encounter`:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "medication_administration_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "context.getReferenceKey(Encounter)", "name": "icu_encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" },
    { "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" },
    { "path": "(dosage.dose).ofType(Quantity).value", "name": "dose_value" },
    { "path": "(dosage.dose).ofType(Quantity).unit", "name": "dose_unit" }
  ]
}
```

The coded group is:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='<exact-itemid>')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The four completed vasoactive dependencies use these exact codes:

| dependency | source itemid / FHIR code | served system | coding rows/resources | relevant shape |
|---|---:|---|---:|---|
| `dobutamine` | 221653 | `.../CodeSystem/mimic-medication-icu` | 44/44 | Period.start/end, rate and dose 44/44 |
| `dopamine` | 221662 | `.../CodeSystem/mimic-medication-icu` | 28/28 | Period.start/end, rate and dose 28/28 |
| `epinephrine` | 221289 | `.../CodeSystem/mimic-medication-icu` | 36/36 | Period.start/end, rate and dose 36/36 |
| `norepinephrine` | 221906 | `.../CodeSystem/mimic-medication-icu` | 947/947 | Period.start/end, rate and dose 947/947 |

The fresh ICU-system projection found 20,404 coding rows over 20,404 distinct
MedicationAdministration resources (1.000); the four target codes total
1,055/1,055 (1.000). `MedicationAdministration.identifier` was populated on
0/56,535 resources. This is not a SOFA input: `linkorderid` is not consumed
from any completed vaso dependency.

For all 1,055 target administrations, `context.getReferenceKey(Encounter)`,
`subject.getReferenceKey(Patient)`, Period.start, Period.end, rate value/unit,
and dose value/unit were non-null; `effective_datetime` was 0/1,055. The
ViewDefinition aliases for effective choices and Quantity values are
`STRING`; raw encoded quantities are `DECIMAL(32,6)`. The completed dependency
outputs already cast `vaso_rate` to `FLOAT` and start/end to `TIMESTAMP_NTZ`.
SOFA consumes those outputs and must not recompute a rate from raw dosage,
units, or the absent `patientweight` field.

## Completed dependency boundary

The runner registers a published dependency shape, not the attempt-shaped
candidate. When a paired resource key is projected, the corresponding MIMIC
identifier is stripped before the dependency is registered. The following is
the exact SOFA interface. Types are the published Spark types; the attempt
parquets used for the fresh ledger still contain the stripped integer columns
for comparison.

| temp view | source columns named by SOFA | published columns SOFA must use | origin / canonical FHIR mapping | published type |
|---|---|---|---|---|
| `icustay_hourly` | `stay_id`, `hr`, `endtime` | `icu_encounter_key`, `patient_key`, `hr`, `endtime` | ICU Encounter `{ "path": "getResourceKey()", "name": "icu_encounter_key" }`, `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; `hr`/`endtime` are completed generated dependency values | `STRING`, `STRING`, `BIGINT`, `TIMESTAMP_NTZ` |
| `bg` | `subject_id`, `charttime`, `specimen`, `pao2fio2ratio` | `patient_key`, `charttime`, `specimen`, `pao2fio2ratio` | Observation `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; effective `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }`; specimen is completed BG's 52033 string pivot | `STRING`, `TIMESTAMP_NTZ`, `STRING`, `DOUBLE` |
| `ventilation` | `stay_id`, `starttime`, `endtime`, `ventilation_status` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `ventilation_status` | Observation encounter reference `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` through completed ventilation; its episode endpoints derive from effective dateTime | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`, `STRING` |
| `vitalsign` | `stay_id`, `charttime`, `mbp` | `icu_encounter_key`, `patient_key`, `charttime`, `mbp` | chartevent Observation encounter reference, effective dateTime, completed `mbp` pivot | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `DOUBLE` |
| `gcs` | `stay_id`, `charttime`, `gcs` | `icu_encounter_key`, `patient_key`, `charttime`, `gcs` | chartevent Observation encounter reference, effective dateTime, completed GCS output | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `FLOAT` |
| `chemistry` | `hadm_id`, `charttime`, `creatinine` | `encounter_key`, `charttime`, `creatinine` | lab Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`; effective dateTime; Quantity.value | `STRING`, `TIMESTAMP_NTZ`, `DOUBLE` |
| `enzyme` | `hadm_id`, `charttime`, `bilirubin_total` | `encounter_key`, `charttime`, `bilirubin_total` | lab Observation encounter reference, effective dateTime, Quantity.value pivot | `STRING`, `TIMESTAMP_NTZ`, `DOUBLE` |
| `complete_blood_count` | `hadm_id`, `charttime`, `platelet` | `encounter_key`, `charttime`, `platelet` | lab Observation encounter reference, effective dateTime, Quantity.value pivot | `STRING`, `TIMESTAMP_NTZ`, `DOUBLE` |
| `urine_output_rate` | `stay_id`, `charttime`, `uo_tm_24hr`, `urineoutput_24hr` | `icu_encounter_key`, `patient_key`, `charttime`, `uo_tm_24hr`, `urineoutput_24hr` | ICU Observation encounter reference, effective dateTime, completed rate output | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `DECIMAL(38,2)`, `DOUBLE` |
| `epinephrine` | `stay_id`, `starttime`, `endtime`, `vaso_rate` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `vaso_rate` | MedicationAdministration `{ "path": "context.getReferenceKey(Encounter)", "name": "icu_encounter_key" }`; effective Period endpoints; dosage.rate Quantity.value | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`, `FLOAT` |
| `norepinephrine` | `stay_id`, `starttime`, `endtime`, `vaso_rate` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `vaso_rate` | same `context`/Period/rate mapping | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`, `FLOAT` |
| `dopamine` | `stay_id`, `starttime`, `endtime`, `vaso_rate` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `vaso_rate` | same `context`/Period/rate mapping | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`, `FLOAT` |
| `dobutamine` | `stay_id`, `starttime`, `endtime`, `vaso_rate` | `icu_encounter_key`, `patient_key`, `starttime`, `endtime`, `vaso_rate` | same `context`/Period/rate mapping | `STRING`, `STRING`, `TIMESTAMP_NTZ`, `TIMESTAMP_NTZ`, `FLOAT` |

Fresh completed-demo boundary ledgers were: `icustay_hourly` 15,615 rows,
all keys/hr/endtime non-null; `bg` 889 rows, patient key/charttime 889/889,
specimen 872/889, ratio 563/889; `ventilation` 209 rows, all status and
start/end/key values non-null; `vitalsign` 21,086 rows with `mbp` 13,994
non-null; `gcs` 3,279 rows with `gcs` 3,279/3,279; `chemistry` 3,289 rows
with `encounter_key` 2,501/3,289, charttime 3,289/3,289, creatinine
3,003/3,289; `enzyme` 1,411 rows with `encounter_key` 1,005/1,411,
charttime 1,411/1,411, bilirubin 1,146/1,411; CBC 2,959 rows with
`encounter_key` 2,336/2,959, charttime 2,959/2,959, platelet 2,820/2,959;
`urine_output_rate` 7,317 rows with all four consumed fields 7,317/7,317;
and vaso rows/rates were dobutamine 44/44, dopamine 28/28, epinephrine 36/36,
norepinephrine 947/947. These nullable lab encounter keys are why SOFA's
hourly lab joins must remain LEFT joins; SOFA does not repair them with a
patient/time heuristic.

The published-strip check against the completed attempt SQLs dropped exactly:

```text
bg:                  subject_id, hadm_id
chemistry:           subject_id, hadm_id, specimen_id
complete_blood_count subject_id, hadm_id, specimen_id
enzyme:              subject_id, hadm_id, specimen_id
gcs:                 subject_id, stay_id
icustay_hourly:      stay_id
vitalsign:           subject_id, stay_id
urine_output_rate:   stay_id
ventilation:         stay_id
dobutamine/dopamine/epinephrine/norepinephrine: stay_id
```

No stripped identifier may be used in a SOFA dependency join. Use
`icu_encounter_key` for ICU-grained dependencies, `encounter_key` for lab
dependencies, and `patient_key` for the BG subject-level join. The ICU
Encounter's `partOf` key supplies the hospital `encounter_key` needed to
replace the source `co.hadm_id` equality.

## Exact pafi and ICU-spine mapping

The source pafi join is `icustays.subject_id = bg.subject_id`. At the
published boundary its exact FHIR-key form is:

```text
icu_encounter.patient_key = bg.patient_key
```

The pafi time field is the completed `bg.charttime` (`TIMESTAMP_NTZ`), whose
FHIR provenance is Observation `(effective).ofType(dateTime)`. The source
`specimen = 'ART.'` predicate is directly expressible on the completed `bg`
string output: the fresh published-shape candidate had 889 rows, 872 non-null
specimen values, 706 exact `ART.` values, and 563 non-null
`pao2fio2ratio` values. The read-only DuckDB `mimiciv_derived.bg` relation
returned the same 889 rows, 872 non-null specimen values, 706 `ART.` values,
and 563 non-null ratios; a multiset comparison of
`(subject_id, charttime, specimen, pao2fio2ratio)` was 889/889 exact.

The completed `ventilation` output had 209 rows: 61 `InvasiveVent`, 139
`SupplementalOxygen`, 5 `HFNC`, and 4 `NonInvasiveVent`; all start/end/key/status
values were populated. Its exact published pafi join is:

```text
icustay_hourly.icu_encounter_key = ventilation.icu_encounter_key
AND bg.charttime >= ventilation.starttime
AND bg.charttime <= ventilation.endtime
AND ventilation.ventilation_status = 'InvasiveVent'
```

The status restriction stays in the LEFT JOIN condition so a non-matching BG
row remains in the non-ventilated branch. No raw oxygen/ventilator Observation
is queried by SOFA.

The completed `icustay_hourly` output had 15,615 rows, with
`icu_encounter_key`, `patient_key`, `hr`, and `endtime` non-null on all rows;
`hr` ranged from -24 to 488. Its `(stay_id, hr, endtime)` multiset was
15,615/15,615 exact against `mimiciv_derived.icustay_hourly`. SOFA recovers
`stay_id` by joining `icu_encounter_key` to the ICU Encounter view and casting
`stay_id_str`; it derives `starttime` as `endtime - INTERVAL 1 HOUR`. There is
no direct FHIRPath for the generated `hr`, `starttime`, or completed hourly
`endtime`.

## Source-column to FHIR/dependency mapping

| SOFA source input | Canonical `{path, name}` or published dependency key | FHIR type / published type | Semantic use |
|---|---|---|---|
| `icustays.stay_id` | ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` joined by `icu_encounter_key` | FHIR string / `STRING`, cast `INTEGER` | ICU spine identity, joins, output key, window partition |
| `icustays.hadm_id` | ICU `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` → parent `{ "path": "getResourceKey()", "name": "encounter_key" }` / `hadm_id_str` | reference key `STRING`; identifier string; optional cast `INTEGER` | Replace source admission equality for chemistry/enzyme/CBC; intermediate only |
| `icustays.subject_id` | ICU `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; Patient identifier path if numeric value is ever needed | reference key `STRING`; Patient identifier string | Exact subject-level pafi join to `bg.patient_key`; intermediate only |
| `icustay_hourly.hr` | published dependency `hr` | generated `BIGINT` | Hour grain, `hr >= 0`, ROWS window ordering |
| `icustay_hourly.endtime` | published dependency `endtime` | completed `TIMESTAMP_NTZ` | Hour interval upper endpoint and final output |
| `co.starttime` | `endtime - INTERVAL 1 HOUR` | generated `TIMESTAMP_NTZ` | Strict lower bound for hourly joins and final output |
| `bg.subject_id` | published `bg.patient_key`; origin `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | opaque `STRING` | Exact subject equality to ICU Encounter patient key |
| `bg.charttime` | published `bg.charttime`; origin `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `TIMESTAMP_NTZ` | pafi and hourly time membership |
| `bg.specimen` | published `bg.specimen`; upstream lab code 52033 `{ "path": "(value).ofType(string)", "name": "value_string" }` | `VARCHAR`/`STRING` | Exact `ART.` filter |
| `bg.pao2fio2ratio` | published `bg.pao2fio2ratio` | `DOUBLE` | P/F ratio for respiration branch |
| `ventilation.stay_id` | published `ventilation.icu_encounter_key`; origin MA/Observation ICU encounter reference | opaque `STRING` | ICU interval join; do not use stripped integer |
| `ventilation.starttime`, `endtime` | published dependency endpoints; origin Observation effective dateTime choices | `TIMESTAMP_NTZ` | Inclusive ventilation interval |
| `ventilation.ventilation_status` | published dependency CASE output | `VARCHAR`/`STRING` | Exact `InvasiveVent` discriminator |
| `vitalsign.stay_id` | published `icu_encounter_key`; Observation `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` | opaque `STRING` | ICU time-window join |
| `vitalsign.charttime` | published `charttime`; Observation `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `TIMESTAMP_NTZ` | MAP window |
| `vitalsign.mbp` | published `mbp` | `DOUBLE` | `meanbp_min` and cardiovascular branch |
| `gcs.stay_id` | published `icu_encounter_key`; Observation encounter reference | opaque `STRING` | ICU time-window join |
| `gcs.charttime` | published `charttime`; Observation effective dateTime | `TIMESTAMP_NTZ` | CNS window |
| `gcs.gcs` | published `gcs` | `FLOAT` | CNS branch; preserve completed dependency output, including its repaired component logic |
| `enzyme.hadm_id` | published `encounter_key`; lab Observation encounter reference | nullable opaque `STRING` | Hospital admission equality, LEFT join |
| `enzyme.charttime` | published `charttime`; lab Observation effective dateTime | `TIMESTAMP_NTZ` | Liver window |
| `enzyme.bilirubin_total` | published `bilirubin_total`; lab Quantity.value pivot | `DOUBLE` | Liver maximum and score |
| `chemistry.hadm_id` | published `encounter_key`; lab Observation encounter reference | nullable opaque `STRING` | Hospital admission equality, LEFT join |
| `chemistry.charttime` | published `charttime`; lab Observation effective dateTime | `TIMESTAMP_NTZ` | Renal window |
| `chemistry.creatinine` | published `creatinine`; lab Quantity.value pivot | `DOUBLE` | Renal maximum and score |
| `complete_blood_count.hadm_id` | published `encounter_key`; lab Observation encounter reference | nullable opaque `STRING` | Hospital admission equality, LEFT join |
| `complete_blood_count.charttime` | published `charttime`; lab Observation effective dateTime | `TIMESTAMP_NTZ` | Coagulation window |
| `complete_blood_count.platelet` | published `platelet`; lab Quantity.value pivot | `DOUBLE` | Platelet minimum and score |
| `urine_output_rate.stay_id` | published `icu_encounter_key`; ICU Observation encounter reference | opaque `STRING` | ICU time-window join |
| `urine_output_rate.charttime` | published `charttime`; Observation effective dateTime | `TIMESTAMP_NTZ` | Urine window |
| `urine_output_rate.uo_tm_24hr` | published dependency output | `DECIMAL(38,2)` | Inclusive `[22,30]` eligibility and divisor |
| `urine_output_rate.urineoutput_24hr` | published dependency output | `DOUBLE` | Scaled urine rate and renal branch |
| each vaso `.stay_id` | published `icu_encounter_key`; MA `{ "path": "context.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` | opaque `STRING` | End-aligned ICU interval join |
| each vaso `.starttime` | published `starttime`; MA `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `TIMESTAMP_NTZ` | Strict lower interval boundary |
| each vaso `.endtime` | published `endtime`; MA Period.end plus dateTime fallback | `TIMESTAMP_NTZ` | Inclusive upper interval boundary |
| each vaso `.vaso_rate` | published `vaso_rate`; MA `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | dependency `FLOAT` | Hourly maximum and cardiovascular score |

Every dependency value above is consumed as published. In particular, SOFA
must not rederive GCS, urine rates, ventilation episodes, vasoactive rates,
hourly grids, lab pivots, or BG P/F ratios from raw FHIR resources.

## SOFA output provenance and types

The source final grain is `(stay_id, hr)` and the manifest comparison key is
`(stay_id, starttime)`. The FHIR support keys are `icu_encounter_key` and
`patient_key`, emitted verbatim beside any integer identifier in a target
attempt. Source/output type mapping is:

| output columns | origin | FHIR/dependency type | target type |
|---|---|---|---|
| `stay_id` | ICU identifier through `icustay_hourly.icu_encounter_key` | FHIR identifier string → cast | `INTEGER` |
| `hr` | `icustay_hourly.hr` | dependency `BIGINT` | `BIGINT` |
| `starttime` | `endtime - 1 hour` | generated `TIMESTAMP_NTZ` | `TIMESTAMP` |
| `endtime` | `icustay_hourly.endtime` | dependency `TIMESTAMP_NTZ` | `TIMESTAMP` |
| `pao2fio2ratio_novent`, `pao2fio2ratio_vent` | BG/ventilation time-window aggregates | `DOUBLE` | `DOUBLE` |
| `rate_epinephrine`, `rate_norepinephrine`, `rate_dopamine`, `rate_dobutamine` | vaso interval `MAX(vaso_rate)` | `FLOAT` | `FLOAT` |
| `meanbp_min`, `bilirubin_max`, `creatinine_max`, `platelet_min`, `uo_24hr` | completed dependency aggregates | `DOUBLE` | `DOUBLE` |
| `gcs_min` | completed GCS aggregate | `FLOAT` | `FLOAT` |
| `respiration`, `coagulation`, `liver`, `cardiovascular`, `cns`, `renal` | SOFA CASE expressions | derived nullable integer | `INTEGER` |
| `respiration_24hours`, `coagulation_24hours`, `liver_24hours`, `cardiovascular_24hours`, `cns_24hours`, `renal_24hours` | 24-row rolling maxima | derived integer | `INTEGER` |
| `sofa_24hours` | sum of six rolling scores | derived integer | `INTEGER` |

The 29-column output order and exact score boundaries remain those in the
source analyst carryover; there is no single FHIRPath for a score or rolling
window output.

## Gaps and representability

* **Absent but derivable, not a loss:** `stay_id` is absent from the published
  `icustay_hourly` relation because its paired `icu_encounter_key` is present;
  the ICU Encounter identifier value recovered it 140/140. Likewise, source
  `hadm_id` is absent from lab dependency interfaces but the ICU Encounter
  `partOf` key and parent hospital Encounter identifier recover it 140/140.
  These are key-interface requirements, not reasons to parse a UUID.
* **Absent but derivable, not a loss:** source `subject_id` for pafi is
  replaced by the equality-preserving `patient_key` join. The ICU Encounter
  and BG patient keys were populated on the relevant demo rows; do not cast or
  parse the key to obtain the integer.
* **Nullable dependency joins:** lab `encounter_key` is missing on 788/3,289
  chemistry rows, 406/1,411 enzyme rows, and 623/2,959 CBC rows in the fresh
  completed-demo ledgers. This is a nullable upstream dependency field, not a
  SOFA FHIR gap: the source SOFA joins these inputs with LEFT JOINs and must
  preserve the hourly spine with NULL analytes. A patient/time heuristic must
  not manufacture an admission key.
* **Not an input loss for SOFA:** ICU `MedicationAdministration.identifier`
  and `inputevents.linkorderid` are absent (identifier array 0/56,535), and
  `patientweight` is not served, but SOFA reads neither. It consumes the
  completed `vaso_rate` outputs. The same applies to raw medication amount and
  link-order fields.
* **Not an input loss for SOFA:** historical GCS chartevents text-loss and
  resource-ID recovery proposals in the provisional GCS fragment are not
  mappings. SOFA consumes the completed `gcs` output and must not rederive it.
* **Datetime choice coverage:** BG/chart Observation targets used for the
  transitive inputs were dateTime-only (23,992/23,992; Period and instant
  variants 0). Vaso MA targets were Period-only (1,055/1,055; dateTime 0).
  Both variants are nevertheless part of the reusable MA mapping because the
  general ICU stream has both forms; cast each string variant to
  `TIMESTAMP_NTZ` before coalescing. No relevant current demo row was lost.
* **Precision boundary inherited from dependencies:** raw FHIR Quantity values
  are served at `DECIMAL(32,6)`, while vaso dependency outputs are `FLOAT`.
  SOFA must preserve the completed dependency values and let the full
  comparison assess any inherited threshold effects; it must not claim to
  recover discarded raw precision from a resource id or alternate field.

No SOFA-specific essential representation loss was found in the fresh demo
probe. The potentially essential values are precisely the preserved dependency
keys, times, nullness, and numeric outputs because they determine row
inclusion, hourly grouping, interval membership, rolling windows, and scores.
The completed dependency boundary supplies each of them. This is evidence for
the implementer and judge, not a terminal accept/block decision.

## Curated notes and provisional fragments

Established entries in `MIMIC_NOTES.md` that changed this mapping were:

* Delta tables, not stale `Mimic*.ndjson.gz` or the live server, are the source
  of truth.
* MIMIC identifiers are string-valued `identifier.value`; resource/reference
  keys are opaque type-prefixed strings and must be emitted/used as keys,
  never parsed as `stay_id`, `hadm_id`, or a timestamp.
* ICU Encounter streams are selected by the exact `encounter-icu`
  `identifier.system`; `Encounter.class` is not a discriminator.
* Itemid-derived Observation codes are verbatim and require exact
  `system + code`; profiles are not a discriminator.
* Observation effective and MedicationAdministration effective are
  polymorphic; project variants separately and cast served wall-clock strings
  to `TIMESTAMP_NTZ`.
* Quantity aliases are string-like and raw FHIR decimals are encoded at six
  places; numeric dependency outputs must be consumed at their published
  types.
* Lab Observation encounter references can be incomplete, so lab-derived
  dependencies must be nullable/LEFT-joined; the SOFA consumer must preserve
  that output rather than infer admissions.
* ICU MedicationAdministration does not serialize `linkorderid`; this field is
  not consumed by SOFA.

Fragments read as provisional leads before probing were:
`MIMIC_NOTES.d/README.md`, `chemistry.md`, `complete_blood_count.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`,
`icustay_hourly.md`, `icustay_times.md`, `icustay_detail.md`,
`norepinephrine.md`, `oxygen_delivery.md`, `urine_output.md`,
`ventilation.md`, `ventilator_setting.md`, and `vitalsign.md`. There is no
`bg.md`, `enzyme.md`, or pre-existing `sofa.md`. The medication identifier,
context-reference, effective-choice, Observation coding, ICU identifier, and
completed-output claims relevant to this mapping were independently checked.
The historical DST and resource-ID recovery claims in sibling fragments were
not adopted; the current rebuilt ICU period and dependency-grid checks were
exact on the demo, and resource IDs remain opaque. Raw GCS/ventilation text
derivation was deliberately not repeated because SOFA consumes completed
dependencies.

Two dataset/IG-wide findings discovered and appended to the owned provisional
fragment are recorded in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/sofa.md`:
Encounter ICU period endpoints are direct populated dateTime fields, and ICU
MedicationAdministration uses `context`, not `encounter`, for its Encounter
reference.

No ViewDefinition or `concept.sql` was authored. This file is the reusable
FHIR-prober carryover for the SOFA loop.
