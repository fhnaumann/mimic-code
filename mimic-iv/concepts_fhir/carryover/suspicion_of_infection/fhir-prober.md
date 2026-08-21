# FHIR mapping and probe evidence: `suspicion_of_infection`

Probe date: 2026-08-21.  The authoritative data was the local Delta warehouse
`/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded Pathling
9.6.0 on Spark 4.0.2.  The source checks used the read-only DuckDB oracle
`/Users/nau025/warehouses/mimic4-demo.db`.  No live Pathling server was used.

Read first: `AGENTS.md`, `LOOP_CONTRACT.md`, the curated
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, every existing file in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/`, the source analysis for this concept,
the canonical SQL, the completed `antibiotic` carryover, the completed
`antibiotic` attempt, and the canonical ViewDefinition shape at
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
This file is mapping/probe evidence only; no ViewDefinition or `concept.sql`
was authored for this concept.

## Concept grain and candidate boundary

The canonical source is
`mimic-iv/concepts/sepsis/suspicion_of_infection.sql`.  Its only dependency is
the completed `antibiotic` relation.  The candidate must read the published
dependency as `FROM antibiotic`; it must not rederive prescriptions or ICU
assignment from FHIR resources in this concept.

The semantic output grain is one row per antibiotic-dependency row, including
ICU-stay fan-out copies.  The source key is `(subject_id, ab_id)`.  `ab_id` is
not a FHIR identifier: it is the source/target SQL `ROW_NUMBER()` over each
subject ordered by `starttime, stoptime, antibiotic, hadm_id, stay_id`.

The published `antibiotic` candidate shape contains these extra FHIR join keys
beside its manifest columns: `patient_key`, `encounter_key`, and
`icu_encounter_key`.  Pass them through to the target output because the
manifest requires resource keys beside `subject_id`, `hadm_id`, and `stay_id`.
They are opaque `Type/id` strings and are used only for equality joins,
grouping, and provenance.

## Resource mapping

| Source relation/input | MIMIC-on-FHIR resource(s) | Role in this concept |
|---|---|---|
| Completed `mimiciv_derived.antibiotic` | Published dependency relation `antibiotic`; originally `MedicationRequest` + `Medication`/mix + `Patient` + hospital/ICU `Encounter` | All antibiotic identity, time, name, admission, stay, and dependency resource-key inputs. Consume the relation, not raw FHIR again. |
| `mimiciv_hosp.microbiologyevents` culture rows | `Observation` with base binding `mimic-microbiology-test`, `Observation.hasMember` references to `Observation` with base binding `mimic-microbiology-organism`, and microbiology `Specimen` | Culture test/time, specimen, organism membership, and the positive-culture discriminator. |
| `microbiologyevents.micro_specimen_id` | `Specimen.identifier` with system `http://mimic.mit.edu/fhir/mimic/identifier/specimen-micro` | Exact specimen grouping/tie-break value, represented as a string identifier; the Specimen resource key is the join spine. |
| `microbiologyevents.org_itemid/org_name` | Micro-organism `Observation.code.coding` with system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism` | Exact organism code/display used to replay `positiveculture`. |

The micro-organism Observation has no usable direct specimen reference in the
served data.  Follow the test Observation's `hasMember` references to the
organism resources.  Do not join by parsing Observation ids.

## Canonical source-column to FHIRPath mappings

The aliases below are FHIR/ViewDefinition materialized types.  Identifier,
reference, code, display, and dateTime aliases are strings in the Pathling
ViewDefinition result.  The implementer must cast MIMIC numeric identifiers to
`INTEGER`, `ab_id` to `BIGINT`, text outputs to bounded `VARCHAR(255)`, and
dateTime aliases to `TIMESTAMP_NTZ` before the final manifest-shaped output.

### Completed `antibiotic` dependency

These mappings are inherited from the completed dependency; the target reads
the published columns and does not repeat the resource extraction.

| Source/dependency column | Canonical FHIRPath mapping (`{path,name}`) | FHIR type / materialized type | Target use |
|---|---|---|---|
| dependency `patient_key` | `{ "path": "getResourceKey()", "name": "patient_key" }` on `Patient`; equivalently the request-side `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | resource key string / `VARCHAR` | Join spine and required output key. |
| `subject_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Identifier.value` string / `VARCHAR` | Final `CAST(... AS INTEGER)`; dependency source identity. |
| dependency `encounter_key` | `{ "path": "getResourceKey()", "name": "encounter_key" }` on hospital `Encounter`; request side `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | resource/reference key string / `VARCHAR` | Hospital admission join and required output key. |
| `hadm_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Identifier.value` string / `VARCHAR` | Final `CAST(... AS INTEGER)` and source ordering tiebreak. |
| dependency `icu_encounter_key` | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` on ICU `Encounter`; ICU assignment side `{ "path": "partOf.getReferenceKey(Encounter)", "name": "hospital_encounter_key" }` | resource/reference key string / `VARCHAR` | Required output key; the dependency already performed the source half-open ICU interval join. |
| `stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` string / `VARCHAR`, nullable | Final `CAST(... AS INTEGER)`; source ordering tiebreak and output. |
| `antibiotic` (`prescriptions.drug`) | Direct/mix target Medication `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name').value", "name": "drug_name" }`; direct request reference `{ "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" }` | identifier value string / `VARCHAR` | Final bounded `VARCHAR`; source name/order value. |
| mix ingredient drug | On `forEach: "ingredient"`, `{ "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }`, then the same `drug_name` mapping above | repeated Reference key + string / `VARCHAR` | Dependency preserves mix ingredient multiplicity before target consumption. |
| `route` (dependency support, not read by this target) | On `forEach: "dosageInstruction.route.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-route')"`, `{ "path": "code", "name": "route_code" }`; `{ "path": "system", "name": "route_system" }` | Coding code/system strings / `VARCHAR` | Used upstream by `antibiotic`; not a target column. |
| `starttime` → `antibiotic_time` | `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | FHIR `dateTime` string / `VARCHAR` | `TRY_CAST(... AS TIMESTAMP_NTZ)`; precise culture windows and date truncation. |
| `stoptime` → `antibiotic_stoptime` | `{ "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }` | FHIR `dateTime` string / `VARCHAR` | `TRY_CAST(... AS TIMESTAMP_NTZ)`; dependency `ab_id` ordering only. |
| `pharmacy_id` (support only) | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" }` | `Identifier.value` string / `VARCHAR` | Selects prescription-backed MedicationRequest rows upstream; not in target output. |

For the dependency's Patient/Encounter identifiers, the exact stream rule is
`system` plus identifier value.  Hospital Encounter is selected by
`identifier.system=.../encounter-hosp`, ICU Encounter by
`.../encounter-icu`; `Encounter.class` is not a discriminator.

### Microbiology test Observation

Use a constrained coding group:
`forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-test')"`.
The following are the canonical column entries in that group:

| Source input | Canonical FHIRPath mapping (`{path,name}`) | FHIR type / materialized type | Use |
|---|---|---|---|
| test Observation key | `{ "path": "getResourceKey()", "name": "micro_test_key" }` | resource key string / `VARCHAR` | Opaque resource identity and provenance. |
| microbiology `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | Reference key string / `VARCHAR` | Equality join to dependency patient key; numeric id is available through Patient identifier if needed. |
| microbiology `hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` | Reference key string / `VARCHAR`, nullable | 1,355/1,893 test resources have this reference. The source aggregates `hadm_id` but never consumes it after `me` is built, so culture matching must not require it. |
| `test_itemid` | `{ "path": "code", "name": "test_code" }` | Coding code string / `VARCHAR` | Group support and provenance; not a target filter. |
| `test_itemid` system | `{ "path": "system", "name": "test_system" }` | `uri` string / `VARCHAR` | Exact stream discriminator. |
| `test_name` | `{ "path": "display", "name": "test_display" }` | Coding display string / `VARCHAR` | Not directly emitted by target; supports verification. |
| `micro_specimen_id` reference | `{ "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key" }` | Reference key string / `VARCHAR` | Equality join to microbiology Specimen. |
| precise/date-only culture time | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime` string / `VARCHAR` | `TRY_CAST(... AS TIMESTAMP_NTZ)`. ETL value is `MAX(COALESCE(charttime, chartdate))` within each `(micro_specimen_id,test_itemid)` group. |
| test-to-organism edge | On `forEach: "hasMember"`, `{ "path": "getReferenceKey(Observation)", "name": "micro_org_key" }` | repeated Observation reference key strings / `VARCHAR` | Join to micro-organism Observations. Use `forEachOrNull: "hasMember"` when retaining negative/no-organism tests; 1,641 test resources have no member and must not be dropped. |

The target uses the Specimen-level collection time to reproduce the source
`me` branch, because source `me` groups by `micro_specimen_id`, not by test:
`Specimen.collection.collectedDateTime` is the source `MAX(charttime)` across
the whole specimen.  When it is null, derive `chartdate` from the date of the
populated test `effective_datetime` values and use midnight, matching
`COALESCE(charttime, DATETIME(chartdate))`.

### Microbiology organism Observation

Use a constrained coding group:
`forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism')"`.

| Source input | Canonical FHIRPath mapping (`{path,name}`) | FHIR type / materialized type | Use |
|---|---|---|---|
| organism Observation key | `{ "path": "getResourceKey()", "name": "micro_org_key" }` | resource key string / `VARCHAR` | Equality target of test `hasMember`; never parse it. |
| `org_itemid` | `{ "path": "code", "name": "org_code" }` | Coding code string / `VARCHAR` | Cast only after constraining the organism system; compare exact string `90856`. |
| organism system | `{ "path": "system", "name": "org_system" }` | `uri` string / `VARCHAR` | Exact stream discriminator. |
| `org_name` | `{ "path": "display", "name": "org_display" }` | Coding display string / `VARCHAR` | Reproduces the source non-null/non-empty positivity predicate. |
| organism effective time | `{ "path": "(effective).ofType(dateTime)", "name": "org_effective_datetime" }` | FHIR `dateTime` string / `VARCHAR` | Not needed by target positivity, but available for audit; cast to `TIMESTAMP_NTZ` if used. |

The served micro-organism Observation has no specimen reference.  The exact
join is `micro_test.micro_org_key = micro_org.micro_org_key` after projecting
the test `hasMember` reference.  The test's code supplies the organism's
`test_itemid` context.

### Microbiology Specimen

Use a constrained identifier group:
`forEach: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-micro')"`,
and a constrained type coding group:
`forEachOrNull: "type.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-spec-type-desc')"`.

| Source input | Canonical FHIRPath mapping (`{path,name}`) | FHIR type / materialized type | Use |
|---|---|---|---|
| Specimen resource key | `{ "path": "getResourceKey()", "name": "specimen_key" }` | resource key string / `VARCHAR` | Equality join from test Observation. |
| `micro_specimen_id` | `{ "path": "system", "name": "specimen_id_system" }`; `{ "path": "value", "name": "micro_specimen_id_str" }` | Identifier system/value strings / `VARCHAR` | Exact grouping/tie-break value; cast the identifier value to the source integer type only if ordering by source `micro_specimen_id` is required. |
| specimen `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | Reference key string / `VARCHAR` | Equality/provenance; the test Observation also carries this reference. |
| `spec_itemid` | `{ "path": "code", "name": "specimen_type_code" }` | Coding code string / `VARCHAR` | Support only; target emits the description, not this code. |
| `spec_type_desc` → `specimen` | `{ "path": "display", "name": "specimen_type_display" }` | Coding display string / `VARCHAR` | Exact target `specimen` value for the selected culture. |
| `charttime` aggregate | `{ "path": "collection.collectedDateTime", "name": "collected_datetime" }` | FHIR `dateTime` string / `VARCHAR`, nullable | Source `MAX(charttime)` and precise/date-only discriminator. Cast to `TIMESTAMP_NTZ`. |

`Specimen.type.coding.system` observed in the authoritative Delta is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-spec-type-desc`.  It is a
proprietary flat binding; no served `CodeSystem` resource is available.

## Confirmed systems, code sets, and cardinality

The source SQL has one coded literal: `org_itemid != 90856`.  The rule is
system plus exact code, not `meta.profile`:

| Filter/source literal | FHIR projection | Source rows | FHIR rows | Coding rows / distinct resources |
|---|---|---:|---:|---:|
| `org_itemid != 90856`; checked code `90856` | `code.coding` in the organism system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism`, `{path: "code", name: "org_code"}` | **0** raw microbiology rows | **0** organism Observation codings | organism stream: 338/338 = **1.000** |

`90856` is absent in this demo on both sides; the source analysis did not mark
it dead, so this is a measured demo finding, not permission to remove the
predicate on full data.  The actual organism stream has 59 distinct codes and
338 code rows/resources.  All 338 source non-null-organism groups had a
non-null, non-empty `org_name`, and all 338 FHIR `display` values were
populated.

The non-filtered stream checks were:

| Stream | Observed system | Coding rows | Distinct resources | Distinct codes | Ratio |
|---|---|---:|---:|---:|---:|
| micro-test | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-test` | 1,893 | 1,893 | 71 | 1.000 |
| micro-organism | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism` | 338 | 338 | 59 | 1.000 |
| micro-susceptibility (not consumed by this SQL) | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-antibiotic` | 1,036 | 1,036 | 25 | 1.000 |
| micro Specimen type | `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-spec-type-desc` | 1,336 | 1,336 | 40 | 1.000 |

Every micro-test and micro-organism coding count was compared per exact code
with DuckDB: all 71 test-code counts and all 59 organism-code counts agreed.
The micro-susceptibility stream is not an input to `suspicion_of_infection`;
it was probed only to ensure that a susceptibility code is not accidentally
used as the positivity discriminator.

The completed antibiotic dependency has no formal itemid/ICD code filter.  Its
FHIR-side name discriminator is the exact identifier system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name` plus the
source SQL's case-insensitive literal drug-name fragments.  Its route
discriminator is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-route` plus exact
route code.  The current demo re-probe measured:

| Dependency stream | Rows/non-null |
|---|---:|
| MedicationRequest total / pharmacy identifier / medication reference | 17,552 / 15,225 / 15,225 |
| MedicationRequest validity start / end | 14,574 / 14,574 |
| MedicationRequest route codings / distinct coded requests | 15,219 / 15,219 (ratio 1.000) |
| Name-bearing Medication identifier values / resources | 1,480 / 1,480 (631 distinct drug strings) |
| Medication mix identifiers / mix resources | 314 / 314 |
| Mix ingredient references / mix resources | 634 / 314 (2.019 references per mix resource) |
| Patient identifier / Patient resources | 100 / 100 |
| Hospital Encounter identifier values / all Encounter resources | 275 / 637 |
| ICU Encounter identifier values / all Encounter resources | 140 / 637 |

The exact excluded dependency route-code counts, measured in the route coding
projection, are `OU=0`, `OS=1`, `OD=0`, `AU=0`, `AS=0`, `AD=0`, `TP=157`.
The previously completed dependency probe also confirmed the 105 literal
name fragments as an OR set: 944 source/FHIR expanded name rows, and 903
source/FHIR antibiotic rows after the route/name filters.  These literals are
free-text predicates, not terminology codes.  `Medication.code.coding` is not
the name discriminator (the observed direct/component code systems were 1,402
NDC, 72 formulary, and 6 name); `Medication.code.display` and route coding
display were null.

The coded-filter rule is therefore: constrain `system` inside each `forEach`,
then compare the exact string code.  Never use Observation `meta.profile`,
which is warehouse-version dependent, and never search medication display
text.

## Microbiology cardinality, aggregation, and exact oracle checks

The raw demo source had 2,899 microbiology rows, 1,336 distinct specimens,
1,893 distinct `(micro_specimen_id,test_itemid)` test groups, and 1,979
distinct `(micro_specimen_id,test_itemid,org_itemid)` groups.  The FHIR ETL
collapses these as follows:

- 1,336 micro Specimen resources: identifier, type, and subject were all
  populated 1,336/1,336; collection time was populated 1,291/1,336.
- 1,893 micro-test Observation resources, one test coding each.  There were
  338 `hasMember` references to 338 distinct organism resources, spread over
  252 tests and 227 specimens.  A `forEachOrNull` member projection expands
  to 1,979 rows (1,641 no-member rows plus 338 member rows); using an inner
  `forEach` would silently drop the no-organism tests.
- 338 micro-organism Observation resources, one organism coding each.  The
  exact source/FHIR group comparison on
  `(micro_specimen_id,test_itemid,org_itemid)` was 338/338 matched, with
  `org_name` display exact on 338/338 and effective time exact on 338/338.
- The specimen comparison on `micro_specimen_id` was 1,336/1,336 matched;
  `spec_type_desc`/type display was exact on 1,336/1,336 and `MAX(charttime)` /
  collection time was exact on the 1,291 non-null values.
- The micro-test comparison on `(micro_specimen_id,test_itemid)` was
  1,893/1,893 matched, with `MAX(COALESCE(charttime,chartdate))` exact on
  1,893/1,893.
- Replaying the source positivity expression from test `hasMember` → organism
  `code`/`display` gave exact specimen-level positivity on 227/227 specimens
  with organism members; source has 227 positive and 1,109 negative specimen
  groups.  The other 1,109 specimens have no member edge and must evaluate to
  `positiveculture=0`, not be removed.

The raw source `hadm_id` is not a culture join key in this concept.  The source
`me` CTE aggregates it and then discards it.  Culture matching is by
`subject_id` only, followed by the precise/date-only time predicate.  The
served test Encounter reference is present for 1,355/1,893 test resources,
matching the source groups with non-null `MAX(hadm_id)`, but requiring that
reference would be a semantic bug.

## DateTime and date-only behavior

Pathling materializes both `Observation.effective.ofType(dateTime)` and
`Specimen.collection.collectedDateTime` as strings with an offset, for example
`2180-06-26T18:30:00-04:00`.  Use `TRY_CAST(... AS TIMESTAMP_NTZ)`; do not use
an offset-aware `TIMESTAMP` cast or a session-zone conversion.  The source ETL
uses `TIMESTAMPTZ` when writing the micro test, organism, and Specimen times,
so full-data DST-gap conflicts are possible and the original wall time is not
recoverable from served FHIR.  The demo exact checks above found no such
conflict.

Source `me` is grouped by specimen.  For each specimen:

1. `Specimen.collection.collectedDateTime` is the exact source
   `MAX(charttime)` when any charttime exists.  This selects the precise-time
   branch for all tests in that specimen.
2. When collection time is absent, the source specimen has no charttime.  The
   test Observation still carries a populated `effectiveDateTime` at the
   chart-date midnight.  Taking its date recovers the source `MAX(chartdate)`
   for the date-only branch.
3. The target's selected culture time is
   `COALESCE(last72_charttime,next24_charttime)`, where date-only cultures are
   represented at midnight.  The target's suspected time is NULL when no
   specimen is selected, otherwise the prior selected culture time or the
   antibiotic time for a subsequent-only culture.

The source had 45/1,336 date-only specimen groups (`MAX(charttime) IS NULL`);
FHIR had 45/1,336 null collection times.  This is a surviving row-level
discriminator, not an id-derived inference.

## Source output mapping and types

The final source manifest shape is `(subject_id, stay_id, hadm_id, ab_id,
antibiotic, antibiotic_time, suspected_infection, suspected_infection_time,
culture_time, specimen, positive_culture)` with types:
`INTEGER, INTEGER, INTEGER, BIGINT, VARCHAR, TIMESTAMP, INTEGER, TIMESTAMP,
TIMESTAMP, VARCHAR, INTEGER`.  The candidate must also pass the required
`patient_key`, `encounter_key`, and `icu_encounter_key` resource-key columns.

| Source output | Canonical mapping/source | Final type | Notes |
|---|---|---|---|
| `subject_id` | Dependency Patient identifier `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `INTEGER` | Cast from dependency string; do not use a Patient resource key as the integer. |
| `stay_id` | Dependency ICU Encounter identifier `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | nullable `INTEGER` | Preserved dependency value; nullable for no ICU assignment. |
| `hadm_id` | Dependency hospital Encounter identifier `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `INTEGER` | Cast from dependency string. It does not constrain culture matching. |
| `ab_id` | No direct FHIR path; `ROW_NUMBER() OVER (PARTITION BY subject_id ORDER BY starttime,stoptime,antibiotic,hadm_id,stay_id)` over published `antibiotic` dependency columns | `BIGINT` | Natural/comparison key component and final culture-join identity. |
| `antibiotic` | Dependency name Medication identifier `{ "path": "value", "name": "drug_name" }` after direct/mix resolution | `VARCHAR` | Bounded cast in dependency; target passes it through. |
| `antibiotic_time` | Dependency MedicationRequest `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | `TIMESTAMP` | Cast `TIMESTAMP_NTZ`; precise window anchor and date truncation. |
| `suspected_infection` | No direct path; `CASE` on selected FHIR-derived specimen existence | `INTEGER` | 0 iff neither selected culture has non-null `specimen`; else 1. |
| `suspected_infection_time` | No direct path; selected culture time or dependency antibiotic time | nullable `TIMESTAMP` | NULL only when neither culture is selected. |
| `culture_time` | No direct path; selected dateTime from the test/Specimen mapping above | nullable `TIMESTAMP` | Prior culture wins; otherwise subsequent culture. |
| `specimen` | `{ "path": "display", "name": "specimen_type_display" }` in Specimen type coding | nullable `VARCHAR` | `COALESCE` of selected prior/subsequent specimen description. |
| `positive_culture` | No direct path; organism `code`/`display` reached through test `hasMember` | nullable `INTEGER` | `MAX` organism positivity per source specimen, then selected-culture `COALESCE`; NULL when no culture. |
| `patient_key` | Dependency `{ "path": "getResourceKey()", "name": "patient_key" }` | opaque key `VARCHAR` | Required alongside `subject_id`; preserve `Patient/<id>` prefix. |
| `encounter_key` | Dependency `{ "path": "getResourceKey()", "name": "encounter_key" }` | opaque key `VARCHAR` | Required alongside `hadm_id`. |
| `icu_encounter_key` | Dependency `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | opaque key `VARCHAR` | Required alongside `stay_id`. |

The target does not output `micro_specimen_id`, `specimen_key`, or
`micro_org_key`; they are internal grouping/join columns.  It also does not
output source `antibiotic_stoptime`, `antibiotic_date`, or `micro_seq`.

## Temporal windows and selection order to preserve

The FHIR candidate should implement the source predicates after the above
casts, retaining the source-only subject join:

- Prior culture: if `Specimen.collection.collectedDateTime` is non-null,
  `antibiotic_time > culture_time` and `<= culture_time + 72 hours`; otherwise
  `DATE(antibiotic_time)` is between culture date and culture date + 3 days,
  inclusive.
- Subsequent culture: if collection time is non-null,
  `antibiotic_time >= culture_time - 24 hours` and `< culture_time`; otherwise
  the antibiotic date is between culture date - 1 day and culture date,
  inclusive.
- For each `(subject_id,ab_id)`, order by culture date, culture time with NULLS
  LAST, positive flag descending, and source `micro_specimen_id` ascending;
  retain `micro_seq=1`.  Grouping by the opaque `specimen_key` is allowed, but
  use the represented `micro_specimen_id_str` value for the source numeric
  tiebreak rather than parsing a resource key.
- Keep both final joins as LEFT JOINs and keep `micro_seq=1` in the join
  condition.  Every antibiotic row must remain in the result when no culture
  matches.

## Representability gaps

### Inherited dependency gap: invalid/incomplete prescription validity

`MedicationRequest.dispenseRequest.validityPeriod.start/end` is absent when
the ETL's coalesced prescription interval is incomplete or reversed.  In the
demo completed `antibiotic` dependency, 48/903 rows have source reversed
intervals and FHIR NULL start/end; 31 of those also lose the source temporal
ICU assignment (`stay_id`).  `authoredOn` is not either endpoint.  This is
absent and not representable, not an invitation to estimate a time.

This loss is potentially essential for this target: `starttime` controls both
the 72-hour/24-hour culture inclusion windows and `antibiotic_time`, while
`starttime`/`stoptime` also control `ab_id`, the natural-key component that
attaches selected cultures.  The 48 dependency rows occur on 25 subjects;
602 of the 903 source suspicion rows belong to those subjects, which is the
bounded population where subject-local ordinal/culture attachment may be
affected.  The exact affected final rows must be established by the full
candidate comparison; this prober does not block the concept.  If the full
result cannot preserve the source `ab_id`/window semantics on this population,
recommend whole-concept blocking to the equivalence judge rather than
publishing apparently faithful ordinary values with an ambiguous key.

### Inherited dependency gap: `prescriptions.drug_type`

No FHIR element carries source `drug_type`; the medication-mix ingredient
ordering is not a typed representation of MAIN/BASE/ADDITIVE.  This target
does not read `drug_type` directly, but it consumes the completed dependency,
so it must inherit the dependency's boundary and never rederive that filter.
The demo had 3,677 BASE source rows overall and zero BASE rows matching the
antibiotic name fragments; the completed dependency therefore produced 903
demo rows with the representable filters.  Full-data neutrality is not
proven.  If an unrepresented drug-type state changes dependency row inclusion
or the target's `(subject_id,ab_id)` grain, it is essential and must be ruled
on by the judge; no approximation is proposed here.

### Absent but derivable source `chartdate`

There is no separate FHIR `chartdate` element.  For the 45 specimen groups
whose collection time is absent, the test `effectiveDateTime` retains the
date at midnight, and the collection-null discriminator identifies exactly
which rows take the date-only branch.  The source/FHIR micro-test effective
comparison was 1,893/1,893 exact and the date-only specimen count was 45/45.
This is a derivable row-level value; emit a typed NULL only if a malformed
FHIR datetime fails parsing, not as a whole-column approximation.

### Potential upstream transform: microbiology datetime DST normalization

The ETL writes micro test, organism, and Specimen collection times through
`TIMESTAMPTZ` (`mimic-fhir/sql/fhir_observation_micro_test.sql:16`,
`fhir_observation_micro_org.sql:15`, and `fhir_specimen.sql:9`).  The served
FHIR value is therefore the value to cast with `TIMESTAMP_NTZ`; the original
source wall time cannot be recovered by querying FHIR or by using an opaque
resource id.  The demo comparisons found 0 residual timestamp differences
for 1,893 test groups, 338 organism groups, and 1,291 non-null specimen
collection times.  A full-data spring-forward divergence would be an upstream
transformation review for the judge, not a reason to parse or regenerate an
id and not a claim that the target invented a row.

### No microbiology gap found in the authoritative demo

The following representable mappings were exact in the source/FHIR checks:
micro-test group/time 1,893/1,893; Specimen identifier/type 1,336/1,336;
non-null Specimen collection times 1,291/1,291; micro-organism group/name/time
338/338; and specimen-level positivity 227/227.  Micro-test Encounter
references are incomplete (1,355/1,893) but the source target discards
`hadm_id` before matching, so this is not a gap for this concept.

## Notes and provisional fragments

Curated `MIMIC_NOTES.md` entries that changed a mapping decision:

- **“Microbiology positivity links through micro-test, not micro-org”** forced
  the `Observation.hasMember` → organism join and the Specimen-from-test path;
  it also prevents an organism-side specimen join.
- **“Observation subtype profile metadata is warehouse-version dependent”**
  forced base binding system/code discrimination instead of `meta.profile`.
- **“Observation.code.coding.code is the source itemid, verbatim”** forced
  exact string code handling and made `90856` the only literal code check.
- **“The microbiology Observation streams aggregate rows”** forced grouping
  by the represented specimen/test/organism grain rather than assuming one
  FHIR Observation per raw microbiology row.
- **Identifier spine / opaque resource-key entries** forced Patient and
  Encounter identifier values for numeric output and preserved the three
  dependency resource keys as separate required columns.
- **Medication name/mix, route-display-null, and invalid-validity-period
  entries** forced the dependency's name-identifier and mix-ingredient paths,
  exact route-code filtering, and the inherited NULL endpoint gap.
- **FHIR datetime / `TIMESTAMP_NTZ` entries** forced direct NTZ casts and no
  id-based recovery of DST-shifted wall times.

I read `MIMIC_NOTES.d/README.md` and all supplied sibling fragments:
`first_day_weight.md`, `dobutamine.md`, `crrt.md`, `charlson.md`,
`oxygen_delivery.md`, `icp.md`, `complete_blood_count.md`, `coagulation.md`,
`norepinephrine.md`, `neuroblock.md`, `gcs.md`, `height.md`, `vitalsign.md`,
`first_day_vitalsign.md`, `icustay_times.md`, `phenylephrine.md`,
`first_day_bg.md`, `milrinone.md`, `icustay_detail.md`, `rhythm.md`,
`icustay_hourly.md`, `arb.md`, `rrt.md`, `ventilator_setting.md`,
`first_day_urine_output.md`, `cardiac_marker.md`, `kdigo_creatinine.md`,
`creatinine_baseline.md`, `blood_differential.md`, `weight_durations.md`,
`dopamine.md`, `code_status.md`, `chemistry.md`, and `urine_output.md`.
Sibling fragments were treated as provisional leads, never as evidence.  The
relevant `arb.md` MedicationRequest endpoint lead and datetime leads were
independently checked against this warehouse and the ETL SQL; the unrelated
ICU, lab, chartevent, race, and code-status claims were not adopted or cited
as evidence for this concept.  No sibling fragment changed a microbiology
mapping decision.

## New dataset-wide notes appended by this probe

Appended only to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/suspicion_of_infection.md`:

1. **Microbiology Specimen.identifier carries the relational
   micro_specimen_id** — 1,336/1,336 targeted Specimens had the exact
   `specimen-micro` identifier and all 1,893 test groups joined exactly.
2. **Microbiology date-only cultures are identified by absent
   Specimen.collection.collectedDateTime** — source and FHIR both had 45
   date-only specimen groups; test effective dates remained populated and
   exact.

These are dataset/IG-wide findings, not concept-specific output claims.
