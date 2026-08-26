# FHIR prober mapping: `sepsis3`

**Concept:** `sepsis3`  
**Attempt:** `attempt_0001`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/sepsis3/source-analyst.md`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Probe engine:** embedded Pathling 9.6.0 / Spark 4.0.2, Spark session timezone UTC  
**Read-only oracle:** `/Users/nau025/warehouses/mimic4-demo.db`  

This is a mapping artifact only. No ViewDefinition or `concept.sql` was
authored for `sepsis3`. The target must consume the completed dependency views
under the unqualified stems `sofa` and `suspicion_of_infection`; it must not
rederive either dependency from raw FHIR resources.

## Resource and dependency map

| Source input | MIMIC-on-FHIR resource or derived view | Role in `sepsis3` |
|---|---|---|
| `mimiciv_derived.sofa` | completed published dependency view `sofa`; originally ICU `Encounter` plus completed observation/lab/medication dependencies | SOFA hourly rows, component scores, rolling 24-hour score, `endtime`, ICU and patient resource keys |
| `mimiciv_derived.suspicion_of_infection` | completed published dependency view `suspicion_of_infection`; originally completed `antibiotic` plus microbiology `Observation`/`Specimen` resources | Antibiotic/culture times, infection discriminator, specimen/positive-culture values, ICU and patient resource keys |
| ICU `stay_id` | `Encounter` filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | Numeric source identifier and exact ICU-stay join spine |
| `subject_id` | `Patient.identifier` on the patient reached by `patient_key` | Numeric source identifier; the key itself remains opaque |

`sofa` and `suspicion_of_infection` are not FHIR resources. Their published
columns are derived SQL values, so the FHIR provenance below is given where a
column has one; generated scores, windows, and selection fields have no single
FHIRPath and must be read from the published dependency.

## Published dependency boundary confirmed in the Delta warehouse

The dependency plan resolved, in dependency-first order, 21 completed views,
ending in `sofa` attempt 0002 and `suspicion_of_infection` attempt 0001. The
runner registered their **published** shapes, with paired integer identifiers
stripped where resource keys are present. The direct target interface is:

### `sofa` published interface

The embedded probe found 12,255 rows and the following Spark types. There is no
published `stay_id`; use `icu_encounter_key` to join to an ICU Encounter and
recover `stay_id_str` from `Encounter.identifier`, then cast it for the target.

| Published column | Published type | Rows / non-null rows | FHIR provenance or use |
|---|---|---:|---|
| `hr` | `BIGINT` | 12,255 / 12,255 | Generated hourly dependency value; not directly FHIR-mapped |
| `starttime` | `TIMESTAMP_NTZ` | 12,255 / 12,255 | Generated as `endtime - 1 HOUR`; selected by source but dropped before final output |
| `endtime` | `TIMESTAMP_NTZ` | 12,255 / 12,255 | Published hourly endpoint; source `sofa_time` and `rn_sus` tie-break |
| `pao2fio2ratio_novent` | `DOUBLE` | 87 / 87 | Completed `bg`/ventilation dependency value; not consumed by `sepsis3` |
| `pao2fio2ratio_vent` | `DOUBLE` | 398 / 398 | Completed `bg`/ventilation dependency value; not consumed by `sepsis3` |
| `rate_epinephrine` | `FLOAT` | 56 / 56 | Completed vasoactive dependency value; not consumed by `sepsis3` |
| `rate_norepinephrine` | `FLOAT` | 1,595 / 1,595 | Completed vasoactive dependency value; not consumed by `sepsis3` |
| `rate_dopamine` | `FLOAT` | 114 / 114 | Completed vasoactive dependency value; not consumed by `sepsis3` |
| `rate_dobutamine` | `FLOAT` | 322 / 322 | Completed vasoactive dependency value; not consumed by `sepsis3` |
| `meanbp_min` | `DOUBLE` | 11,237 / 11,237 | Completed vital-sign dependency value; not consumed by `sepsis3` |
| `gcs_min` | `FLOAT` | 3,220 / 3,220 | Completed GCS dependency value; not consumed by `sepsis3` |
| `uo_24hr` | `DOUBLE` | 5,235 / 5,235 | Completed urine-output dependency value; not consumed by `sepsis3` |
| `bilirubin_max` | `DOUBLE` | 285 / 285 | Completed enzyme dependency value; not consumed by `sepsis3` |
| `creatinine_max` | `DOUBLE` | 925 / 925 | Completed chemistry dependency value; not consumed by `sepsis3` |
| `platelet_min` | `DOUBLE` | 831 / 831 | Completed CBC dependency value; not consumed by `sepsis3` |
| `respiration` | `INTEGER` | 485 / 485 | Intermediate SOFA component; not consumed by `sepsis3` |
| `coagulation` | `INTEGER` | 831 / 831 | Intermediate SOFA component; not consumed by `sepsis3` |
| `liver` | `INTEGER` | 285 / 285 | Intermediate SOFA component; not consumed by `sepsis3` |
| `cardiovascular` | `INTEGER` | 11,327 / 11,327 | Intermediate SOFA component; not consumed by `sepsis3` |
| `cns` | `INTEGER` | 3,220 / 3,220 | Intermediate SOFA component; not consumed by `sepsis3` |
| `renal` | `INTEGER` | 5,774 / 5,774 | Intermediate SOFA component; not consumed by `sepsis3` |
| `respiration_24hours` | `INTEGER` | 12,255 / 12,255 | Source `respiration` output |
| `coagulation_24hours` | `INTEGER` | 12,255 / 12,255 | Source `coagulation` output |
| `liver_24hours` | `INTEGER` | 12,255 / 12,255 | Source `liver` output |
| `cardiovascular_24hours` | `INTEGER` | 12,255 / 12,255 | Source `cardiovascular` output |
| `cns_24hours` | `INTEGER` | 12,255 / 12,255 | Source `cns` output |
| `renal_24hours` | `INTEGER` | 12,255 / 12,255 | Source `renal` output |
| `sofa_24hours` | `INTEGER` | 12,255 / 12,255 | Source `sofa_score`; filter `>= 2` and Boolean input |
| `icu_encounter_key` | `STRING` | 12,255 / 12,255 | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` on ICU `Encounter`; opaque `Encounter/<id>` |
| `patient_key` | `STRING` | 12,255 / 12,255 | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`; opaque `Patient/<id>` |

### `suspicion_of_infection` published interface

The embedded probe found 903 rows. The dependency has no published
`subject_id`, `hadm_id`, or `stay_id`; paired resource keys replace those
integers. `icu_encounter_key` is nullable because the dependency includes
non-ICU antibiotic rows.

| Published column | Published type | Rows / non-null rows | FHIR provenance or use |
|---|---|---:|---|
| `ab_id` | `BIGINT` | 903 / 903 | Generated `ROW_NUMBER()` in completed `antibiotic`/suspicion SQL; not a FHIR resource id |
| `antibiotic` | `STRING` | 903 / 903 | Completed antibiotic dependency; ultimately Medication name identifier |
| `antibiotic_time` | `TIMESTAMP_NTZ` | 903 / 855 | Completed MedicationRequest validity-period start; source ordering and final output |
| `suspected_infection` | `INTEGER` | 903 / 903 | Derived culture-existence discriminator, values 0/1; final Boolean input |
| `suspected_infection_time` | `TIMESTAMP_NTZ` | 903 / 747 | Derived selected culture/antibiotic time; join anchor and row ordering |
| `culture_time` | `TIMESTAMP_NTZ` | 903 / 747 | Derived selected microbiology time; row ordering and final output |
| `specimen` | `STRING` | 903 / 747 | Derived selected Specimen type display; intermediate only in `sepsis3` |
| `positive_culture` | `INTEGER` | 903 / 747 | Derived through test `hasMember` to organism code/display; intermediate only |
| `patient_key` | `STRING` | 903 / 903 | Completed dependency patient resource key; exact subject join and required target key |
| `encounter_key` | `STRING` | 903 / 903 | Completed hospital Encounter resource key; not consumed by `sepsis3` predicates |
| `icu_encounter_key` | `STRING` | 903 / 433 | Completed ICU Encounter resource key; exact stay join and source `stay_id IS NOT NULL` discriminator |

The count probe used `count(*)` and `count(field)` over the materialized
published views. It also showed that the current published `sofa` and
`suspicion_of_infection` shapes are Spark `TIMESTAMP_NTZ`/numeric outputs, not
the string aliases emitted directly by a FHIR ViewDefinition.

## Canonical FHIR support mappings for stripped identifiers and joins

These are the support columns required to reproduce the source integer ids.
The aliases are FHIR strings and must be cast only in the final target SQL.

### ICU Encounter support

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').system", "name": "stay_system" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "period_start" },
    { "path": "period.end", "name": "period_end" }
  ]
}
```

| Source value / operation | Canonical `{path, name}` | FHIR type | Probe result and target type |
|---|---|---|---|
| ICU resource key | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | resource key `string` | ICU stream 140/140; preserve `Encounter/<id>` as `STRING` |
| ICU patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` | ICU stream 140/140; equality join only, `STRING` |
| ICU parent hospital reference | `{ "path": "partOf.getReferenceKey(Encounter)", "name": "parent_encounter_key" }` | `Reference(Encounter)` | ICU stream 140/140; not needed by `sepsis3`, `STRING` |
| ICU stream discriminator | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').system", "name": "stay_system" }` | `uri` | 140/140 on ICU rows; filter this exact URI, not `Encounter.class` |
| Source `stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Identifier.value` `string` | 140/140 non-null on ICU stream; final `CAST(stay_id_str AS INTEGER)` |
| ICU period start/end | `{ "path": "period.start", "name": "period_start" }`; `{ "path": "period.end", "name": "period_end" }` | `dateTime` | 140/140 each on ICU stream; direct aliases are `STRING`, not used by target |

The direct ICU probe also found 497 non-ICU Encounter rows with no ICU
identifier and 140 ICU rows with all `icu_encounter_key`, `patient_key`,
`parent_encounter_key`, `stay_system`, and `stay_id_str` populated. The
patient support view found 100/100 `patient_key` and `subject_id_str` values.
The target must filter `stay_system` or `stay_id_str IS NOT NULL`; testing only
`icu_encounter_key IS NOT NULL` would admit the other Encounter streams if the
view were unfiltered.

### Patient support

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

`subject_id` is `CAST(subject_id_str AS INTEGER)`. A resource key must never be
parsed or substituted for the identifier value.

## Source dependency-column to FHIRPath mapping

The following tables map every dependency column named by `sepsis3.sql`,
including fields selected into intermediate CTEs but dropped from the final
output. Direct FHIR paths are shown in canonical `{path,name}` form; a
`published dependency column` entry is intentional where the value is a
completed derived result rather than an individual FHIR element.

### `sofa` columns consumed by `sepsis3`

| Source column / alias | Canonical mapping | FHIR type / published type | Count and semantic use |
|---|---|---|---|
| `sofa.stay_id` | ICU `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` reached through `sofa.icu_encounter_key` | identifier string → `INTEGER`; key `STRING` | `sofa.icu_encounter_key` 12,255/12,255; ICU support 140/140; source join identity and final key |
| `sofa.starttime` | Published `sofa.starttime`; generated from published `endtime - INTERVAL 1 HOUR` | derived `TIMESTAMP_NTZ` | 12,255/12,255; selected into `s1` then dropped |
| `sofa.endtime` | Published `sofa.endtime`; origin is completed ICU hourly endpoint, ultimately ICU Encounter period/hour spine | derived `TIMESTAMP_NTZ` | 12,255/12,255; inclusive temporal join, window tie-break, final `sofa_time` |
| `sofa.respiration_24hours AS respiration` | Published `sofa.respiration_24hours` | derived `INTEGER` | 12,255/12,255; final `respiration` |
| `sofa.coagulation_24hours AS coagulation` | Published `sofa.coagulation_24hours` | derived `INTEGER` | 12,255/12,255; final `coagulation` |
| `sofa.liver_24hours AS liver` | Published `sofa.liver_24hours` | derived `INTEGER` | 12,255/12,255; final `liver` |
| `sofa.cardiovascular_24hours AS cardiovascular` | Published `sofa.cardiovascular_24hours` | derived `INTEGER` | 12,255/12,255; final `cardiovascular` |
| `sofa.cns_24hours AS cns` | Published `sofa.cns_24hours` | derived `INTEGER` | 12,255/12,255; final `cns` |
| `sofa.renal_24hours AS renal` | Published `sofa.renal_24hours` | derived `INTEGER` | 12,255/12,255; final `renal` |
| `sofa.sofa_24hours AS sofa_score` | Published `sofa.sofa_24hours` | derived `INTEGER` | 12,255/12,255; filter `>= 2`, repeated in `sepsis3`, final score |

The source `WHERE sofa_24hours >= 2` is a dependency-value filter, not a FHIR
coding filter. It must remain in the target SQL over `sofa.sofa_24hours`.

### `suspicion_of_infection` columns consumed by `sepsis3`

| Source column | Canonical mapping / dependency path | FHIR type / published type | Count and semantic use |
|---|---|---|---|
| `soi.subject_id` | `soi.patient_key` → Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | identifier string → `INTEGER`; key `STRING` | `patient_key` 903/903; Patient support 100/100; final `subject_id` |
| `soi.stay_id` | `soi.icu_encounter_key` → ICU `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | nullable identifier string → nullable `INTEGER` | ICU key 433/903; `icu_encounter_key IS NOT NULL` exactly represents source `stay_id IS NOT NULL`; final `stay_id` |
| `soi.ab_id` | Published `suspicion_of_infection.ab_id` | generated `BIGINT` | 903/903; selected but not used by `sepsis3` |
| `soi.antibiotic` | Published dependency `antibiotic`; upstream Medication `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name').value", "name": "drug_name" }` | identifier string / `STRING` | 903/903; selected but dropped by `sepsis3` |
| `soi.antibiotic_time` | Published dependency `antibiotic_time`; upstream MedicationRequest `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | FHIR dateTime string → `TIMESTAMP_NTZ` | 903/855; window ordering and final `antibiotic_time` |
| `soi.culture_time` | Published dependency `culture_time`; upstream micro-test `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` and Specimen `{ "path": "collection.collectedDateTime", "name": "collected_datetime" }`, with date-only derivation | FHIR dateTime strings → nullable `TIMESTAMP_NTZ` | 903/747; window ordering and final `culture_time` |
| `soi.suspected_infection` | Published dependency `suspected_infection`; derived from selected culture existence | derived `INTEGER` (0/1) | 903/903; Boolean operand of `sofa_score >= 2 AND suspected_infection = 1` |
| `soi.suspected_infection_time` | Published dependency `suspected_infection_time`; derived selected culture time or antibiotic time | nullable derived `TIMESTAMP_NTZ` | 903/747; temporal join anchor, first window ordering field, final output |
| `soi.specimen` | Published dependency `specimen`; upstream Specimen type coding `{ "path": "display", "name": "specimen_type_display" }` | coding display string → nullable `VARCHAR` | 903/747; selected but dropped by `sepsis3` |
| `soi.positive_culture` | Published dependency `positive_culture`; upstream micro-test `forEachOrNull: "hasMember"` with `{ "path": "getReferenceKey(Observation)", "name": "micro_org_key" }`, joined by key to organism `{ "path": "display", "name": "org_display" }` and `{ "path": "code", "name": "org_code" }` | derived nullable `INTEGER` | 903/747; selected but dropped by `sepsis3` |

The microbiology support views were also materialized directly for verification:
the `micro_test` view had 1,979 fan-out rows (all `micro_test_key`, patient,
specimen, effective time, and test-code values non-null; 338 `micro_org_key`
edges), `micro_org` had 338/338 for key, time, code, system, and display, and
`micro_specimen` had 1,336/1,336 for key, patient, identifier system/value,
type code/system/display, with `collected_datetime` 1,291/1,336. The 1,979
micro-test rows are the expected `hasMember` fan-out; the completed dependency
groups back to 1,893 test resources before producing suspicion rows.

## Exact target join, time, and row-selection semantics

The source integer join is represented without parsing ids:

```text
soi.icu_encounter_key = sofa.icu_encounter_key
```

Both are opaque ICU Encounter resource keys. The target may recover and emit
the integer `stay_id` from the ICU Encounter identifier, but must not join on a
cast integer where the published dependency has only its key. The published
dependency `soi.icu_encounter_key IS NOT NULL` is the exact replacement for
`WHERE soi.stay_id IS NOT NULL`; it is not a heuristic.

The source temporal join is inclusive at both endpoints:

```text
sofa.endtime >= soi.suspected_infection_time - INTERVAL 48 HOURS
AND sofa.endtime <= soi.suspected_infection_time + INTERVAL 24 HOURS
```

`sofa.endtime` and `soi.suspected_infection_time` are both published
`TIMESTAMP_NTZ`. A null suspected-infection time makes both comparisons false,
so the inner join removes that row. The target must not use `starttime` for the
join. After the join, retain `ROW_NUMBER() OVER (PARTITION BY
soi.icu_encounter_key ORDER BY suspected_infection_time, antibiotic_time,
culture_time, sofa.endtime) = 1`. This is the key-preserving form of the
source `PARTITION BY soi.stay_id`; preserve the source engine's ordinary NULL
ordering and do not add an unrequested tie-breaker.

The `sepsis3` expression remains `sofa_score >= 2 AND
suspected_infection = 1`. The first conjunct is already guaranteed by the
SOFA filter but must remain in the Boolean derivation.

## Confirmed code-set status

There are **no direct coded filters in `sepsis3.sql`**: no itemid, ICD code,
or FHIR coding system is named. The literals are numeric/time semantics only:
SOFA threshold `2`, infection flag `1`, the `[-48,+24]` hour window, and
`rn_sus = 1`. Therefore there is no sepsis3 code set, per-code count, or
codings-per-resource ratio to report. The microbiology organism literal `90856`
belongs to the completed `suspicion_of_infection` dependency boundary and must
not be reintroduced as a new target filter.

## Oracle manifest shape

Read-only `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`
declares:

| Property | Confirmed value |
|---|---|
| Output columns | `subject_id INTEGER`, `stay_id INTEGER`, `antibiotic_time TIMESTAMP`, `culture_time TIMESTAMP`, `suspected_infection_time TIMESTAMP`, `sofa_time TIMESTAMP`, `sofa_score INTEGER`, `respiration INTEGER`, `coagulation INTEGER`, `liver INTEGER`, `cardiovascular INTEGER`, `cns INTEGER`, `renal INTEGER`, `sepsis3 BOOLEAN` |
| Comparison | `keyed_join` |
| Natural key | `stay_id` |
| Required FHIR comparison keys | `icu_encounter_key`, `patient_key` (emit alongside `stay_id`/`subject_id`; they are not replacements for the manifest source key) |
| Key probes | 2 |
| Full oracle rows | 32,971 |
| Content hash | `303735228387322374588155` |

The final target types are the manifest types. FHIR identifier values and
ViewDefinition dateTime aliases are strings, so the implementer must cast
identifiers to `INTEGER` and published/derived time aliases as needed to
`TIMESTAMP_NTZ` (normalized as `TIMESTAMP` by the manifest). Resource keys
remain uncast `STRING` values with the `Patient/` or `Encounter/` prefix.

## Gaps and inherited dependency losses

### Source identifiers stripped from published dependencies — absent but derivable

`subject_id` and `stay_id` are absent from the published dependency views, but
their values are represented by Patient/ICU Encounter `identifier.value` and
the resource keys provide exact equality joins. Demo coverage was Patient
`subject_id_str` 100/100, ICU `stay_id_str` 140/140, `sofa.icu_encounter_key`
12,255/12,255, and `suspicion_of_infection.icu_encounter_key` 433/903. This is
not an id-parsing side channel. `encounter_key` is also present in the
suspicion interface, though `sepsis3` does not consume source `hadm_id`.

### Generated dependency values — absent as individual FHIR elements but available at the required boundary

SOFA rolling scores/components, `sofa.endtime`, suspicion culture selection,
`ab_id`, `suspected_infection`, and `positive_culture` have no one-to-one
FHIRPath. They are present in the completed published dependency views and are
therefore derivable only by consuming `sofa` and `suspicion_of_infection` as
required. Re-deriving them from FHIR would cross the dependency boundary and
could change grouping, temporal selection, or row inclusion.

### Inherited suspicion dependency loss — potentially essential; bound before target run

The completed suspicion dependency's invalid/incomplete prescription validity
periods omit `MedicationRequest.dispenseRequest.validityPeriod.start/end`.
In the demo boundary, `antibiotic_time` is missing on 48/903 rows and 31 of
those also lose the ICU assignment (`icu_encounter_key`/source `stay_id`). In
the completed full comparison, 2,983 rows were `differing_null_only`; column
level null-only counts included `stay_id` 27,411 and `antibiotic_time` 45,436,
and 269,997 rows had inherited conflicts, with 462,482/735,462 rows identical.
The missing times affect culture-window inclusion and the suspicion ordinal;
the missing ICU assignment affects `sepsis3`'s row-eliminating stay filter.
This reaches rows the target cannot identify from a missing integer alone, so
the sepsis3 full comparison must measure whether the dependency's accepted
divergence changes selected sepsis rows. It is not a reason to estimate times
from `authoredOn` or parse a resource id.

### Inherited SOFA precision loss — potentially selection-relevant, not a new mapping gap

The completed full `sofa` comparison had 1,138 conflicts among 6,043,902 rows
(cardiovascular 294, cardiovascular_24hours 1,022, sofa_24hours 1,022, and one
rate conflict), attributed in its accepted dependency record to Pathling's
six-decimal decimal encoding and its threshold effect. Because `sepsis3`
filters `sofa_24hours >= 2` and uses the selected SOFA row, this inherited
value divergence can be clinically/row-selection relevant. The target must
consume the completed `sofa` output unchanged; whether it reaches the 32,971
sepsis3 rows is a full-run question, not something to repair with an opaque
resource key.

No sepsis3-specific unrepresentable raw FHIR field was found beyond these
inherited dependency transformations. The prober does not make the terminal
equivalence or blocking decision.

## Evidence and note provenance

Read before probing: `AGENTS.md`, `.opencode/skills/fhir-mapping/SKILL.md`,
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, the canonical source analysis, the
canonical `sepsis3.sql`, both dependency SQLs, the oracle manifest, and the
canonical ViewDefinition format supplied by the sofa-provisioning reference.
Relevant provisional fragments read were `MIMIC_NOTES.d/sofa.md`,
`MIMIC_NOTES.d/suspicion_of_infection.md`, `MIMIC_NOTES.d/icustay_detail.md`,
`MIMIC_NOTES.d/icustay_times.md`, and `MIMIC_NOTES.d/README.md`. The sofa and
suspicion fragments were treated as leads and their relevant claims were
verified against the Delta probes; the unrelated race and chartevent leads
were not adopted.

Curated `MIMIC_NOTES.md` entries that changed this mapping were:

- **MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a UUID**:
  forced separate integer identifier and opaque resource-key columns.
- **`getResourceKey()` is type-prefixed; `Resource.id` is the bare UUID**:
  forced preservation of `Patient/` and `Encounter/` prefixes and equality-only
  joins.
- **Encounter has three identifier systems — class discriminates none of them**:
  forced the ICU `identifier.system` filter and `stay_id_str` path.
- **FHIR datetimes carry an offset — cast to `TIMESTAMP_NTZ`**:
  forced the published time type and no session-zone conversion.
- **Essential source loss blocks the whole derived concept** and the
  precision/encoder entries: recorded the inherited losses as potentially
  selection-relevant rather than inventing values.

The only new dataset/IG-level entry appended by this probe was the ICU
Encounter period endpoint claim in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sepsis3.md`; it records 140/140
`period.start` and `period.end` values on the ICU stream. No other fragment was
edited and `MIMIC_NOTES.md` was not edited.
