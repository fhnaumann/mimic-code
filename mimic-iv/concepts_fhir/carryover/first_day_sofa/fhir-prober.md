# FHIR probe and mapping: `first_day_sofa`

**Concept:** `firstday/first_day_sofa`  
**Canonical source:** `mimic-iv/concepts/firstday/first_day_sofa.sql`  
**Probed:** 2026-08-25  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 / Spark 4.0.2, session timezone UTC  
**Read-only oracle:** `/Users/nau025/warehouses/mimic4-demo.db`  

This is a mapping artifact, not a ViewDefinition or candidate SQL. The source
SQL has no direct raw Observation/MedicationAdministration reads: its ten
`mimiciv_derived` dependencies must be consumed by their published, unqualified
view names. Resource and reference keys are opaque equality keys only.

## Scope and source shape

The source has one output row per `mimiciv_icu.icustays.stay_id`. The full oracle
manifest declares 73,181 rows, comparison key `stay_id`, and required opaque
FHIR key columns `patient_key`, `encounter_key`, and `icu_encounter_key`.
The relational output columns and required target types are:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
sofa INTEGER, respiration INTEGER, coagulation INTEGER, liver INTEGER,
cardiovascular INTEGER, cns INTEGER, renal INTEGER
```

The source SQL's dependency boundary is exactly:

```text
bg, dobutamine, dopamine, epinephrine, first_day_gcs, first_day_lab,
first_day_urine_output, first_day_vitalsign, norepinephrine, ventilation
```

Do not inline any dependency's raw FHIR extraction, item filter, aggregate, or
clinical calculation. Published dependency relations may strip integer
identifiers when their paired opaque keys are present; join them on
`patient_key`/`icu_encounter_key`, not on a regenerated or parsed resource id.

## Source table/relation to FHIR resource/interface

| MIMIC-IV source relation | FHIR resource or published interface | Role in this concept |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | One-row-per-stay spine; supplies `subject_id`, `stay_id`, `hadm_id` support, and `intime` |
| `icustays.subject_id` | ICU `Encounter.subject` → `Patient` | Patient equality key and final numeric `subject_id` |
| `icustays.stay_id` | ICU `Encounter.identifier` | Final numeric `stay_id` and dependency equality spine |
| `icustays.hadm_id` | ICU `Encounter.partOf` → hospital `Encounter.identifier` | Final numeric `hadm_id`; not the ICU identifier |
| `icustays.intime` | ICU `Encounter.period.start` | Closed `[-6 hours,+1 day]` window anchor |
| `mimiciv_derived.bg` | Published `bg` relation; upstream lab/chart `Observation` resources | `subject_id`/patient key, `charttime`, `pao2fio2ratio`, and `specimen` for respiration |
| `mimiciv_derived.norepinephrine` | Published medication dependency; upstream ICU `MedicationAdministration` | `stay_id`/ICU key, `starttime`, `vaso_rate` |
| `mimiciv_derived.epinephrine` | Published medication dependency; upstream ICU `MedicationAdministration` | `stay_id`/ICU key, `starttime`, `vaso_rate` |
| `mimiciv_derived.dobutamine` | Published medication dependency; upstream ICU `MedicationAdministration` | `stay_id`/ICU key, `starttime`, `vaso_rate` |
| `mimiciv_derived.dopamine` | Published medication dependency; upstream ICU `MedicationAdministration` | `stay_id`/ICU key, `starttime`, `vaso_rate` |
| `mimiciv_derived.ventilation` | Published ventilation relation; upstream chartevents `Observation` resources | `stay_id`/ICU key, `starttime`, `endtime`, `ventilation_status` |
| `mimiciv_derived.first_day_vitalsign` | Published vitalsign relation; upstream chartevents `Observation` resources | `mbp_min` |
| `mimiciv_derived.first_day_lab` | Published lab aggregate relation; upstream lab `Observation` + `Specimen` resources | `creatinine_max`, `bilirubin_total_max`, `platelets_min` |
| `mimiciv_derived.first_day_urine_output` | Published urine aggregate relation; upstream outputevents `Observation` resources | `urineoutput` |
| `mimiciv_derived.first_day_gcs` | Published GCS relation; upstream chartevents `Observation` resources | `gcs_min` |

The source's local CTEs (`vaso_stg`, `vaso_mv`, `pafi1`, `pafi2`,
`scorecomp`, `scorecalc`) are computed SQL relations, not FHIR resources.

## Canonical identity and time projections

These are the direct FHIR projections required by the consumer. FHIR identifier
values and ViewDefinition aliases are strings; only the final SQL casts the
numeric identifiers. Keys retain their type prefix and are never parsed.

### Patient

```text
{"path": "getResourceKey()", "name": "patient_key"}
{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
```

Types: resource key `string`/`STRING`; `Identifier.value` `string`/`STRING`.
`subject_id_str` becomes `CAST(subject_id_str AS INTEGER)` in final SQL.

### ICU Encounter

```text
{"path": "getResourceKey()", "name": "icu_encounter_key"}
{"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}
{"path": "period.start", "name": "intime_datetime"}
```

Use this constrained repeating group for the ICU stream:

```text
forEach: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')"
  {"path": "system", "name": "stay_id_system"}
  {"path": "value", "name": "stay_id_str"}
```

Types: `getResourceKey()` and `subject.getReferenceKey(Patient)` are opaque
`string` keys; `period.start` is FHIR `dateTime` materialized as an offset-
bearing `STRING`; identifier `system` is `uri`; identifier `value` is
`string`. Cast `intime_datetime` directly to `TIMESTAMP_NTZ`.

### Hospital Encounter support for `hadm_id`

```text
{"path": "getResourceKey()", "name": "encounter_key"}
{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str"}
```

On the ICU Encounter, use:

```text
{"path": "partOf.getReferenceKey(Encounter)", "name": "encounter_key"}
```

`partOf.getReferenceKey(Encounter)` and the hospital Encounter resource key
matched for 140/140 ICU Encounters in the demo; `hadm_id_str` was non-null and
agreed with the source `hadm_id` for 140/140. The ICU stream must still be
selected by its ICU identifier system; `Encounter.class` is not a stream
discriminator.

## Source-column to FHIRPath mapping

### Direct `icustays` columns

| Source column | Canonical mapping (`{path, name}`) | FHIR type / materialized type | Required target type/use | Probe population |
|---|---|---|---|---:|
| `subject_id` | ICU Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` → Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `Reference(Patient)` key + `Identifier.value string`; `STRING` aliases | `CAST(subject_id_str AS INTEGER)` → `subject_id INTEGER`; emit `patient_key` | 140/140 |
| `hadm_id` | ICU Encounter `{path: "partOf.getReferenceKey(Encounter)", name: "encounter_key"}` → hospital Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | `Reference(Encounter)` key + identifier `string`; `STRING` aliases | `CAST(hadm_id_str AS INTEGER)` → `hadm_id INTEGER`; emit `encounter_key` | 140/140 |
| `stay_id` | ICU Encounter identifier group `{path: "value", name: "stay_id_str"}` under the ICU identifier system | identifier `string`; `STRING` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER`; emit `icu_encounter_key` | 140/140 |
| `intime` | `{path: "period.start", name: "intime_datetime"}` | FHIR `dateTime`; materialized `STRING` | `CAST(intime_datetime AS TIMESTAMP_NTZ)` for all inclusive windows | 140/140 |
| ICU Encounter identity | `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque type-prefixed resource key `string` | Equality joins and required output key; uncast | 140/140 |
| Patient identity | Patient `{path: "getResourceKey()", name: "patient_key"}` | opaque type-prefixed resource key `string` | Equality joins and required output key; uncast | 140/140 |
| hospital Encounter identity | `{path: "getResourceKey()", name: "encounter_key"}` | opaque type-prefixed resource key `string` | `partOf` equality join and required output key; uncast | 140/140 |

Direct ICU spine oracle agreement was exact: `subject_id` 140/140,
`hadm_id` 140/140, `stay_id` 140/140, and wall-clock `intime` 140/140.
No direct ICU spine field was null in the 140-row demo ICU stream.

### Published dependency interface

The following are the columns actually read by this consumer. They are
published derived values, not additional ViewDefinition columns in this
concept. Their upstream FHIR provenance is included to make the type and loss
boundary explicit.

| Dependency column read | Upstream FHIR provenance (`{path, name}`) | FHIR type / published type | Population checked |
|---|---|---|---:|
| `bg.patient_key` (source SQL's `bg.subject_id` equality) | lab/chart Observation `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | opaque key `string`; published `STRING` | 889/889 |
| `bg.charttime` | Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | FHIR `dateTime`; published `TIMESTAMP_NTZ` | 889/889 |
| `bg.pao2fio2ratio` | no single FHIR element; completed `bg` calculation over lab Quantity values, effective times, and chart enrichments | derived nullable `DOUBLE` | 563/889 |
| `bg.specimen` | lab Observation code `52033`, `{path: "(value).ofType(string)", name: "value_string"}` in the upstream dependency | derived nullable `VARCHAR` | 872/889 |
| `norepinephrine.icu_encounter_key` | MedicationAdministration `{path: "context.getReferenceKey(Encounter)", name: "icu_encounter_key"}` | opaque key `string`; published `STRING` | 947/947 |
| `epinephrine.icu_encounter_key` | same `context.getReferenceKey(Encounter)` path | opaque key `string`; published `STRING` | 36/36 |
| `dobutamine.icu_encounter_key` | same `context.getReferenceKey(Encounter)` path | opaque key `string`; published `STRING` | 44/44 |
| `dopamine.icu_encounter_key` | same `context.getReferenceKey(Encounter)` path | opaque key `string`; published `STRING` | 28/28 |
| each vasoactive `starttime` | MedicationAdministration `{path: "(effective).ofType(Period).start", name: "effective_period_start"}` | FHIR `dateTime`; published `TIMESTAMP_NTZ` | 947/947, 36/36, 44/44, 28/28 |
| each vasoactive `vaso_rate` | MedicationAdministration `{path: "(dosage.rate).ofType(Quantity).value", name: "rate_value"}` | FHIR `Quantity.value decimal`; ViewDefinition alias `STRING`; published `FLOAT` | 947/947, 36/36, 44/44, 28/28 |
| `ventilation.icu_encounter_key` | chartevents Observation `{path: "encounter.getReferenceKey(Encounter)", name: "icu_encounter_key"}` | opaque key `string`; published `STRING` | 209/209 |
| `ventilation.starttime`, `endtime` | chartevents Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}`; interval construction is dependency logic | FHIR `dateTime`; published `TIMESTAMP_NTZ` | 209/209 each |
| `ventilation.ventilation_status` | no single FHIR element; completed CASE over oxygen-device/mode text | derived nullable `VARCHAR` | 209/209 |
| `first_day_vitalsign.mbp_min` | upstream chartevents Quantity `{path: "(value).ofType(Quantity).value", name: "quantity_value"}`; completed dependency aggregate | derived nullable `DOUBLE` | 139/140 |
| `first_day_lab.creatinine_max` | upstream lab Quantity `{path: "(value).ofType(Quantity).value", name: "quantity_value"}`; completed dependency aggregate | derived nullable `DOUBLE` | 140/140 |
| `first_day_lab.bilirubin_total_max` | same upstream lab Quantity path; completed dependency aggregate | derived nullable `DOUBLE` | 77/140 |
| `first_day_lab.platelets_min` | same upstream lab Quantity path; completed dependency aggregate | derived nullable `DOUBLE` | 139/140 |
| `first_day_urine_output.urineoutput` | upstream outputevents Quantity `{path: "(value).ofType(Quantity).value", name: "value_quantity"}`; completed first-day sum | derived nullable `DOUBLE` | 137/140 |
| `first_day_gcs.gcs_min` | upstream chartevents Quantity/component mapping owned by `gcs`; completed dependency value | derived nullable `FLOAT` | 140/140 |

For `bg`, the source SQL's `ie.subject_id = bg.subject_id` is implemented at
the published boundary as equality on the ICU Encounter's `patient_key` and
`bg.patient_key`. This is the same Patient reference identity, not an id
reconstruction. The source does not join `bg` by stay or admission.

For each medication dependency, the generic upstream coding and support paths
are:

```text
{"path": "getResourceKey()", "name": "medadmin_key"}
{"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}
{"path": "context.getReferenceKey(Encounter)", "name": "icu_encounter_key"}
{"path": "(effective).ofType(dateTime)", "name": "effective_datetime"}
{"path": "(effective).ofType(Period).start", "name": "effective_period_start"}
{"path": "(effective).ofType(Period).end", "name": "effective_period_end"}
{"path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value"}
{"path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit"}
```

The target's rate-bearing medication rows are Period-valued in the demo:
`effective_datetime` is 0/target rows and `effective_period_start/end` are
non-null for every target row. Both effective variants remain necessary in a
reusable ICU MedicationAdministration projection because the complete stream
contains both variants.

For the ventilation dependency, the upstream chartevents coding projection
uses:

```text
forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"
  {"path": "code", "name": "item_code"}
  {"path": "system", "name": "item_system"}
  {"path": "display", "name": "item_display"}
```

Categorical text uses `{path: "(value).ofType(string)", name: "value_string"}`;
numeric rows whose text carries a distinct label additionally use
`forEachOrNull: "component"` with `{path: "code.coding.code", name: "component_item_code"}`,
`{path: "code.coding.system", name: "component_system"}`, and
`{path: "value.ofType(string)", name: "component_text"}`. `ventilation_status`
itself remains a dependency-derived value and must be consumed from `FROM
ventilation`.

## Dependency code/discriminator confirmation

`first_day_sofa.sql` has **no direct `code.coding` filter**. Its direct literal
discriminators are dependency-output strings, not FHIR codings:

| Source predicate | Relation | Count in demo | Code system |
|---|---|---:|---|
| `bg.specimen = 'ART.'` | `mimiciv_derived.bg` | 706/889 relation rows | N/A; derived string |
| `vd.ventilation_status = 'InvasiveVent'` | `mimiciv_derived.ventilation` | 61/209 relation rows | N/A; derived string |
| `treatment = 'norepinephrine'` | local `vaso_stg` | 947 upstream rows | N/A; local label generated by this SQL |
| `treatment = 'epinephrine'` | local `vaso_stg` | 36 upstream rows | N/A; local label generated by this SQL |
| `treatment = 'dobutamine'` | local `vaso_stg` | 44 upstream rows | N/A; local label generated by this SQL |
| `treatment = 'dopamine'` | local `vaso_stg` | 28 upstream rows | N/A; local label generated by this SQL |

The upstream item-code ledgers were also checked against Delta and DuckDB so
that these dependency boundaries are not silently widened:

| Upstream stream | Served `code.coding.system` | Exact code counts (FHIR rows = distinct resources; source count equal) | Coding/resource ratio |
|---|---|---|---:|
| vasoactive `inputevents` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu` | `221906: 947`, `221289: 36`, `221653: 44`, `221662: 28` | 1.000 for each |
| `bg` lab items | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` | `50801:28, 50802:889, 50803:13, 50804:889, 50805:7, 50806:101, 50807:0, 50808:509, 50809:262, 50810:143, 50811:143, 50813:758, 50814:6, 50815:19, 50816:137, 50817:223, 50818:889, 50819:130, 50820:966, 50821:889, 50822:302, 50823:28, 50824:141, 50825:201, 52033:1033` | 8706/8706 = 1.000 |
| `bg` chart enrichments | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220277: 13,540`, `223835: 1,746` | 15,286/15,286 = 1.000 |
| `first_day_gcs` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220739: 3,274`, `223900: 3,266`, `223901: 3,251` | 9,791/9,791 = 1.000 |
| `first_day_urine_output` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items` | `226559:6685, 226560:496, 226561:90, 226584:0, 226563:0, 226564:0, 226565:0, 226567:15, 226557:0, 226558:0, 227488:32, 227489:31` | 7349/7349 = 1.000 |
| `first_day_vitalsign` | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220045:13913, 225309:486, 225310:486, 225312:488, 220050:5525, 220051:5524, 220052:5560, 220179:8347, 220180:8349, 220181:8342, 220210:13913, 224690:1331, 220277:13540, 225664:1637, 220621:931, 226537:209, 223762:391, 223761:3379, 224642:3794` | 96,145/96,145 = 1.000 |
| `ventilation` upstream | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `220339:1447, 223834:1090, 223835:1746, 223848:1292, 223849:1048, 224684:769, 224685:1331, 224686:661, 224687:1359, 224688:801, 224689:1314, 224690:1331, 224691:330, 224696:510, 224700:490, 226732:3145, 227287:145, 227582:13, 229314:402` | 19,224/19,224 = 1.000 |

The first-day lab aggregate's five dependency code sets are owned by
`complete_blood_count`, `chemistry`, `blood_differential`, `coagulation`, and
`enzyme`; their checked union was 71,457 FHIR codings over 71,457 distinct
Observation resources (1.000). `first_day_sofa` does not add or repeat those
filters.

The exact pair `system + code` is the discriminator. No `meta.profile` filter
is used. For the shared `mimic-d-items` system, `d_items.itemid` is a global
primary key with one `linksto`: the urine literals above have
`linksto='outputevents'`; this is why the exact code still separates
`outputevents` from `datetimeevents`.

## Output mapping

The score columns are computed SQL outputs, not individual FHIR elements:

| Output | Provenance | FHIR type/path status | Required type |
|---|---|---|---|
| `subject_id` | Patient identifier reached from ICU Encounter subject | identifier `string` at `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | `INTEGER` |
| `hadm_id` | hospital Encounter identifier reached through ICU `partOf` | identifier `string` at `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | `INTEGER` |
| `stay_id` | ICU Encounter identifier | identifier `string` at `{path: "value", name: "stay_id_str"}` in ICU identifier group | `INTEGER` |
| `sofa` | sum of six component CASE outputs with null-to-zero imputation | no single FHIRPath; computed from published dependency values | `INTEGER` |
| `respiration` | `pao2fio2_vent_min` / `pao2fio2_novent_min` and inclusive ventilation overlay | no single FHIRPath; computed | nullable `INTEGER` |
| `coagulation` | `first_day_lab.platelets_min` | no single FHIRPath; published aggregate | nullable `INTEGER` |
| `liver` | `first_day_lab.bilirubin_total_max` | no single FHIRPath; published aggregate | nullable `INTEGER` |
| `cardiovascular` | `first_day_vitalsign.mbp_min` plus four medication `vaso_rate` maxima | no single FHIRPath; computed | nullable `INTEGER` |
| `cns` | `first_day_gcs.gcs_min` | no single FHIRPath; published aggregate | nullable `INTEGER` |
| `renal` | `first_day_lab.creatinine_max` and `first_day_urine_output.urineoutput` | no single FHIRPath; published aggregates | nullable `INTEGER` |
| `patient_key` | Patient `{path: "getResourceKey()", name: "patient_key"}` | opaque resource key `string` | uncast key |
| `encounter_key` | hospital Encounter `{path: "getResourceKey()", name: "encounter_key"}` | opaque resource key `string` | uncast key |
| `icu_encounter_key` | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | opaque resource key `string` | uncast key |

Demo source output counts were 140/140 non-null for `subject_id`, `hadm_id`,
`stay_id`, `sofa`, `cns`, and `renal`; `respiration` 59/140,
`coagulation` 139/140, `liver` 77/140, and `cardiovascular` 139/140. These
component NULLs are source semantics and must remain typed NULLs; `sofa`
deliberately converts missing components to zero.

## Gaps and representability

1. **`hadm_id` is absent from the ICU identifier itself but derivable.** The
   ICU Encounter's `partOf` reference and the hospital Encounter's
   `encounter-hosp` identifier recover it for 140/140 demo ICU stays. This is
   not a loss and is not essential after the ordinary reference join.
2. **Published dependency integer identifiers may be absent but are
   derivable.** `bg.subject_id` and dependency `stay_id` values may be stripped
   when paired keys are published. Patient/ICU Encounter identifier values and
   opaque equality keys preserve the required joins. Do not parse ids. This is
   not a loss and does not change row inclusion when the published key joins
   are used.
3. **Computed dependency aggregates have no single FHIRPath.**
   `pao2fio2ratio`, `ventilation_status`, first-day extrema, urine total, and
   GCS are derivable only by their completed dependency transformations. They
   are not absent from this port boundary; consume the published fields.
4. **Historical DST transformation is not a current demo gap.** The shared
   notes record that the upstream `TIMESTAMPTZ` normalization was repaired by
   the UTC warehouse rebuild. The direct ICU `intime` check was 140/140 exact,
   and the rebuilt dependency probes preserved wall-clock dateTimes. If a
   future/full warehouse exhibits the old spring-forward shift, it can affect
   window membership and minima on the rows whose timestamps fall in that
   identifiable DST branch; it must be sent to the comparator/judge, not
   corrected through an opaque id. No whole-concept blocking recommendation is
   made from the current probe.
5. **`linkorderid` is not representable in ICU MedicationAdministration**, but
   `first_day_sofa` does not read it. It cannot affect this concept's row
   inclusion, grouping, time windows, or score values, so it is not a gap in
   the target output.
6. **GCS/ventilator categorical text is dependency-owned.** Earlier fragments
   described numeric chartevents text loss, but the established notes document
   the rebuilt `Observation.component.valueString` repair. This consumer must
   use the completed `first_day_gcs` and `ventilation` interfaces and must not
   recover labels from resource ids. The target itself has no additional
   unbounded representability gap after that dependency boundary.

No essential missing source field was found in the current served demo for the
direct ICU spine or the published columns read by this consumer. The source
fields that can change inclusion/grouping/clinical output are `stay_id`,
`subject_id`/patient key, `intime`, dependency timestamps, specimen/status
discriminators, and numeric dependency values; each is either present or
represented by an established completed dependency interface.

## Probe and oracle evidence

- ICU Encounter/Patient/hospital-reference probe over Delta: 140/140 exact for
  `subject_id`, `hadm_id`, `stay_id`, and wall-clock `intime`; all direct keys
  and identifiers non-null.
- Exact medication coding probe: codes `221906=947`, `221289=36`,
  `221653=44`, `221662=28`; each FHIR count equaled DuckDB source count and
  each coding/resource ratio was 1.000. Medication period starts and rates
  were populated for every target row; source/FHIR times matched 947/947 for
  norepinephrine and the corresponding exact target counts for the other
  three streams.
- Exact observation coding probe: all listed upstream code counts above came
  from constrained `code.coding` projections over Delta; every reported
  stream had one coding per resource. The two shared-system outputevent/
  datetimeevent streams were checked against `d_items.linksto`.
- Dependency output probe in DuckDB: `bg` 889 rows with `ART.` 706;
  `ventilation` 209 rows with `InvasiveVent` 61; all four vasoactive dependency
  row counts matched their exact FHIR item-code counts.
- Source target shape probe: demo `mimiciv_derived.first_day_sofa` has 140
  rows and 140 distinct `stay_id` values, with the null populations reported
  in the output table above.

## Notes and fragments consulted

Established `MIMIC_NOTES.md` entries that changed or constrained this mapping:

- identifier values are strings and must be cast; resource keys are separate
  required opaque output keys;
- resource keys are type-prefixed and equality-only;
- datetimes require direct `TIMESTAMP_NTZ` casts and current UTC rebuild status;
- Encounter streams require identifier-system filtering and ICU `partOf` is the
  hospital-admission join;
- Observation streams use exact `code.coding.system + code`, never
  `meta.profile`;
- `mimic-d-items` itemids are global and `linksto` warrants the outputevents
  discriminator;
- Quantity ViewDefinition aliases are string-like and need numeric casts;
- MedicationAdministration effective[x] and chartevents categorical values are
  polymorphic/choice-type fields;
- repaired chartevents component text must be owned by GCS/ventilation
  dependencies rather than recovered from ids.

Read as provisional leads and verified against the current Delta where
relevant: `first_day_gcs.md`, `first_day_urine_output.md`,
`first_day_vitalsign.md`, `first_day_bg.md`, `first_day_bg_art.md`,
`bg.md`, `gcs.md`, `urine_output.md`, `vitalsign.md`, `ventilator_setting.md`,
`oxygen_delivery.md`, `ventilation.md`, `dobutamine.md`, `dopamine.md`,
`epinephrine.md`, `norepinephrine.md`, `first_day_lab.md`,
`complete_blood_count.md`, `chemistry.md`, `blood_differential.md`,
`coagulation.md`, and `enzyme.md` where present. No new dataset-wide quirk
was discovered, so nothing was appended to `MIMIC_NOTES.d/first_day_sofa.md`.
