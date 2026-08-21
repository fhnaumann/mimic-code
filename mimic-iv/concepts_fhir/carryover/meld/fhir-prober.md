# FHIR probe and mapping: `meld`

**Probed:** 2026-08-21  
**Warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB 1.5.5, read-only  
**Canonical format:** `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`

No HTTP Pathling server, raw NDJSON, attempt ViewDefinition, or attempt SQL was
used or authored.  The Delta resource tables are the authoritative FHIR
representation.

## Scope and dependency boundary

The source specification is `mimic-iv/concepts/organfailure/meld.sql`.  Its
direct source table/resource mapping is:

| Source relation or role | FHIR resource or candidate view | Role in `meld` |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter`, selected by `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` | One-row-per-ICU-stay driving spine; supplies `subject_id`, `hadm_id`, `stay_id` and dead `intime`/`outtime` CTE columns |
| `icustays.subject_id` | `Patient` identifier reached through ICU `Encounter.subject` | Output patient identifier |
| `icustays.hadm_id` | Parent hospital `Encounter`, reached through ICU `Encounter.partOf` | Output admission identifier |
| `mimiciv_derived.first_day_lab` | Completed candidate temp view `first_day_lab` | `creatinine_max`, `bilirubin_total_max`, `inr_max`, `sodium_min` |
| `mimiciv_derived.first_day_rrt` | Completed candidate temp view `first_day_rrt` | `dialysis_present`, consumed as output/branch flag `rrt` |

`first_day_lab` and `first_day_rrt` are completed dependencies (attempt 0001,
controller status `COMPLETED`).  The implementation must consume the
unqualified completed temp views, not rederive laboratory or RRT data from
FHIR and not inline either dependency SQL.  Their published shapes retain the
FHIR equality keys and strip the paired integer MIMIC identifiers:

```text
first_day_lab:
  icu_encounter_key VARCHAR, patient_key VARCHAR,
  creatinine_max DOUBLE, bilirubin_total_max DOUBLE,
  inr_max DOUBLE, sodium_min DOUBLE

first_day_rrt:
  icu_encounter_key VARCHAR, patient_key VARCHAR,
  dialysis_present INTEGER
```

The candidate dependency artifacts were probed before identifier stripping;
the published-shape rule removes `subject_id`/`stay_id` because the paired
keys are present.  Demo population counts were:

| Published dependency field | Rows total | Rows non-null | Candidate type |
|---|---:|---:|---|
| `first_day_lab.icu_encounter_key` | 140 | 140 | `VARCHAR` / opaque `Encounter/<id>` |
| `first_day_lab.patient_key` | 140 | 140 | `VARCHAR` / opaque `Patient/<id>` |
| `first_day_lab.creatinine_max` | 140 | 140 | nullable `DOUBLE` |
| `first_day_lab.bilirubin_total_max` | 140 | 77 | nullable `DOUBLE` |
| `first_day_lab.inr_max` | 140 | 126 | nullable `DOUBLE` |
| `first_day_lab.sodium_min` | 140 | 140 | nullable `DOUBLE` |
| `first_day_rrt.icu_encounter_key` | 140 | 140 | `VARCHAR` / opaque `Encounter/<id>` |
| `first_day_rrt.patient_key` | 140 | 140 | `VARCHAR` / opaque `Patient/<id>` |
| `first_day_rrt.dialysis_present` | 140 | 6 | nullable `INTEGER` |

The completed dependency carryovers report exact keyed agreement with their
DuckDB source outputs for 140/140 demo ICU stays.  `dialysis_present` being
NULL on 134 demo stays is the expected LEFT-join result, not a missing FHIR
resource.  The consumer joins both dependencies on
`icu_encounter_key`, not on a stripped integer `stay_id`.

## Canonical ViewDefinition mappings

These are mapping specifications for the implementer, not attempt artifacts.
The `_str` aliases remain FHIR `string` values and are cast only by the final
candidate SQL.  The `_key` aliases are uncast, type-prefixed Pathling resource
keys and are equality-join/output columns only.

### ICU Encounter spine

Resource: `Encounter`; the ICU identifier restriction is required.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "name": "icu_encounter",
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "icu_encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "partOf.getReferenceKey(Encounter)", "name": "encounter_key" },
        { "path": "period.start", "name": "intime" },
        { "path": "period.end", "name": "outtime" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
      "column": [
        { "path": "value", "name": "stay_id_str" },
        { "path": "system", "name": "stay_id_system" }
      ]
    }
  ]
}
```

`partOf.getReferenceKey(Encounter)` is the parent hospital Encounter key; it
is not an integer and must not be parsed.  Multiple ICU stays can share a
parent admission, so `encounter_key` is not unique in the ICU view, but the
hospital Encounter helper below is unique on that key and the join is
many-to-one.

### Hospital Encounter helper for `hadm_id`

Resource: `Encounter`, restricted to the hospital-admission identifier
system.  Its `encounter_key` joins to the ICU view's `partOf` key.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "name": "hospital_encounter",
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')",
      "column": [
        { "path": "value", "name": "hadm_id_str" },
        { "path": "system", "name": "hadm_id_system" }
      ]
    }
  ]
}
```

### Patient identifier helper

Resource: `Patient`.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "name": "patient",
  "resource": "Patient",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "patient_key" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient')",
      "column": [
        { "path": "value", "name": "subject_id_str" },
        { "path": "system", "name": "subject_id_system" }
      ]
    }
  ]
}
```

## Source-column to FHIRPath / dependency-column mapping

| Source column or expression | Canonical `{path, name}` or boundary | FHIR/served type | Required final type and use |
|---|---|---|---|
| `icustays.subject_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` on `Patient`, reached through ICU `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Identifier.value` is FHIR `string`; `patient_key` is opaque `Reference(Patient)` key `string` | `CAST(subject_id_str AS INTEGER) AS subject_id`; emit `patient_key` beside it |
| `icustays.hadm_id` | ICU `{ "path": "partOf.getReferenceKey(Encounter)", "name": "encounter_key" }` joined to hospital `{ "path": "getResourceKey()", "name": "encounter_key" }`, then `{ "path": "value", "name": "hadm_id_str" }` inside the restricted hospital identifier `forEach` | parent `Reference(Encounter)` key plus FHIR `string` identifier | `CAST(hadm_id_str AS INTEGER) AS hadm_id`; emit `encounter_key` beside it |
| `icustays.stay_id` | ICU `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` plus `{ "path": "value", "name": "stay_id_str" }` inside the restricted ICU identifier `forEach` | resource key `string`; identifier value FHIR `string` | `CAST(stay_id_str AS INTEGER) AS stay_id`; emit `icu_encounter_key` beside it and use it for dependency joins |
| `icustays.intime` | `{ "path": "period.start", "name": "intime" }` | FHIR `dateTime`, materialized as offset-bearing `STRING` | If carried through a view, `TRY_CAST(intime AS TIMESTAMP_NTZ)`; selected by the source CTE but dead after `cohort`, so it does not affect MELD |
| `icustays.outtime` | `{ "path": "period.end", "name": "outtime" }` | FHIR `dateTime`, materialized as offset-bearing `STRING` | Not used after `cohort`; no output or score dependency |
| `first_day_lab.stay_id` | Published dependency boundary; the source integer is replaced for consumers by `first_day_lab.icu_encounter_key` | published opaque `VARCHAR` key | `labs.icu_encounter_key = e.icu_encounter_key`; do not join on or reconstruct an integer stay id |
| `first_day_lab.creatinine_max` | Published dependency column `creatinine_max`; no new FHIR projection in `meld` | nullable `DOUBLE`, ultimately from completed lab dependency Quantity values | Pass through as target `DOUBLE`; controls the creatinine CASE branch and `meld_initial`/`meld` |
| `first_day_lab.bilirubin_total_max` | Published dependency column `bilirubin_total_max`; no new FHIR projection in `meld` | nullable `DOUBLE`, ultimately from completed lab dependency | Pass through as target `DOUBLE`; controls bilirubin score |
| `first_day_lab.inr_max` | Published dependency column `inr_max`; no new FHIR projection in `meld` | nullable `DOUBLE`, ultimately from completed coagulation dependency | Pass through as target `DOUBLE`; controls INR score |
| `first_day_lab.sodium_min` | Published dependency column `sodium_min`; no new FHIR projection in `meld` | nullable `DOUBLE`, ultimately from completed lab dependency | Pass through as target `DOUBLE`; controls sodium correction and final `meld` |
| `first_day_rrt.stay_id` | Published dependency boundary; use `first_day_rrt.icu_encounter_key` | published opaque `VARCHAR` key | `r.icu_encounter_key = e.icu_encounter_key`; do not rederive RRT |
| `first_day_rrt.dialysis_present` | Published dependency column `dialysis_present`, aliased by source SQL as `rrt` | nullable `INTEGER` | Pass through as target `INTEGER`; `rrt = 1` selects the creatinine-for-dialysis branch |
| `meld_initial` | No direct FHIR path; derived SQL over the four dependency inputs and `rrt` | no FHIR element; source target `DECIMAL(38,1)` | Preserve target `DECIMAL(38,1)` |
| `meld` | No direct FHIR path; derived SQL over `meld_initial` and the sodium score | no FHIR element; source target `DOUBLE` | Preserve target `DOUBLE` |
| `sodium_score`, `creatinine_score`, `bilirubin_score`, `inr_score` | No direct FHIR path; intermediate source-CTE expressions | derived numeric SQL values | Do not publish as FHIR columns; retain only as implementation intermediates |

The manifest target shape is:

```text
subject_id INTEGER, hadm_id INTEGER, stay_id INTEGER,
meld_initial DECIMAL(38,1), meld DOUBLE, rrt INTEGER,
creatinine_max DOUBLE, bilirubin_total_max DOUBLE,
inr_max DOUBLE, sodium_min DOUBLE
```

The required FHIR equality/output keys are `encounter_key`,
`icu_encounter_key`, and `patient_key`; all are uncast `VARCHAR` values with
the `Type/id` prefix.  The natural comparison key remains `stay_id`.

## Joins and cardinality

The identity-preserving join plan is:

```text
icu_encounter e
  LEFT JOIN patient p
    ON e.patient_key = p.patient_key
  LEFT JOIN hospital_encounter h
    ON e.encounter_key = h.encounter_key
  LEFT JOIN first_day_lab labs
    ON e.icu_encounter_key = labs.icu_encounter_key
  LEFT JOIN first_day_rrt r
    ON e.icu_encounter_key = r.icu_encounter_key
```

The two dependency joins are the published-shape form of the source
`ie.stay_id = dependency.stay_id` equalities.  This is an opaque-key equality
substitution, not parsing or regeneration of a resource id.  Keep both joins
LEFT-sided so an ICU stay remains present with nullable dependency values.

## Served-data counts and exact oracle check

The authoritative Delta has 637 total `Encounter` resources.  Exploding
`Encounter.identifier` gave:

```text
encounter-ed    222
encounter-hosp  275
encounter-icu   140
```

The restricted views gave these row/non-null/distinct counts:

| View and field | Total | Non-null | Distinct |
|---|---:|---:|---:|
| ICU `icu_encounter_key` | 140 | 140 | 140 |
| ICU `patient_key` | 140 | 140 | 100 |
| ICU `encounter_key` from `partOf` | 140 | 140 | 128 |
| ICU `period.start` | 140 | 140 | 140 |
| ICU `period.end` | 140 | 140 | 140 |
| ICU `stay_id_str` | 140 | 140 | 140 |
| ICU `stay_id_system` | 140 | 140 | 1 |
| hospital `encounter_key` | 275 | 275 | 275 |
| hospital `patient_key` | 275 | 275 | 100 |
| hospital `hadm_id_str` | 275 | 275 | 275 |
| hospital `hadm_id_system` | 275 | 275 | 1 |
| Patient `patient_key` | 100 | 100 | 100 |
| Patient `subject_id_str` | 100 | 100 | 100 |

The identifier systems were exactly:

```text
patient:       http://mimic.mit.edu/fhir/mimic/identifier/patient
hospital:      http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp
ICU:           http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu
```

A read-only DuckDB join, keyed by the ICU identifier value only for checking
the mapping, found 140/140 rows and exact agreement for `subject_id`,
`hadm_id`, `stay_id`, ICU `period.start`/`icustays.intime`, and ICU
`period.end`/`icustays.outtime`.  Datetimes were compared after the FHIR
offset-bearing string was cast as a wall-clock `TIMESTAMP_NTZ`; no
offset-aware timezone conversion was used.  No resource id was parsed,
regenerated, hashed, hardcoded, or used as a semantic side channel.

## Coding and discriminator confirmation

The direct `meld.sql` code set is empty.  It names no itemid, ICD, LOINC, or
other coded literal, so there is no `code.coding` `forEach`, no code-system
probe, no per-code count, and no codings-per-resource ratio for this concept.
The dependency item/code sets belong to the completed `first_day_lab` and
`first_day_rrt` concepts and must not be copied into this consumer.

The resource-stream discriminator is `identifier.system` plus the restricted
identifier value path, not `meta.profile` and not `Encounter.class`:

```text
ICU stays:  identifier.system = .../identifier/encounter-icu
admission:  identifier.system = .../identifier/encounter-hosp
patients:   identifier.system = .../identifier/patient
```

There is no code-coding fan-out to report.  The ICU identifier `forEach` has
one row per ICU Encounter (140/140), the hospital identifier `forEach` has one
row per hospital Encounter (275/275), and the Patient identifier projection
has one value per Patient (100/100).

## Gaps and representability

* **No measured gap for `subject_id`, `hadm_id`, or `stay_id`.** Patient and
  both Encounter identifier values were populated and the keyed oracle checks
  were 140/140 exact.  The ICU `partOf` reference was populated 140/140; the
  parent key's 128 distinct values correctly reflect multiple ICU stays in one
  hospital admission and do not fan out the hospital join.
* **No dependency-column gap at the `meld` boundary.** Both completed
  dependency views publish every field consumed by the source SQL, with typed
  nullable values.  A dependency aggregate NULL is an ordinary value on the
  affected ICU rows, not an absent row that should be filtered.
* **`intime`/`outtime` are representable but nonessential here.** They map to
  `Encounter.period.start`/`.end` and were exact on the 140-row demo check,
  but the source selects them into `cohort` and never uses them afterward.
  The established upstream Encounter ETL DST-gap normalization remains a
  possible datetime loss if a future edit uses these fields; it cannot affect
  the current MELD output because there is no temporal predicate or carry-
  forward in `meld.sql`.
* **Derived score columns have no direct FHIR element.** This is not a
  representability gap: the score is computed from the dependency columns
  that are available in the completed candidate views.  The implementation
  must not claim a FHIR path for `meld_initial` or `meld`.

No essential source loss was measured in this demo probe.  This is not a
terminal semantic decision; any full-data divergence remains for the
deterministic comparator and equivalence judge.

## Notes and provisional-fragment audit

The following curated `MIMIC_NOTES.md` entries changed this mapping decision:

* **MIMIC ids live in `identifier.value` as STRINGs** — drove the `_str`
  projections, final integer casts, and paired key outputs.
* **`getResourceKey()` is type-prefixed and opaque** — drove equality joins on
  `patient_key`, `encounter_key`, and `icu_encounter_key`, with no id parsing or
  regeneration.
* **Encounter has three identifier systems; class discriminates none** —
  drove the ICU and hospital identifier-system filters and rejected an
  `Encounter.class` discriminator.
* **FHIR datetimes carry an offset; cast to `TIMESTAMP_NTZ`** — established
  the correct type handling for the mapped period fields.  The related DST
  loss is nonessential to this particular SQL because `intime`/`outtime` are
  dead after `cohort`.
* **Essential source loss blocks only when it reaches a used branch** —
  confirmed that the dead period columns do not justify blocking this concept.

I read every existing fragment in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`:
`README.md`, `arb.md`, `blood_differential.md`, `cardiac_marker.md`,
`charlson.md`, `chemistry.md`, `code_status.md`, `coagulation.md`,
`complete_blood_count.md`, `creatinine_baseline.md`, `crrt.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `first_day_bg.md`,
`first_day_urine_output.md`, `first_day_vitalsign.md`, `first_day_weight.md`,
`gcs.md`, `height.md`, `icp.md`, `icustay_detail.md`, `icustay_hourly.md`,
`icustay_times.md`, `invasive_line.md`, `kdigo_creatinine.md`, `kdigo_uo.md`,
`milrinone.md`, `neuroblock.md`, `norepinephrine.md`, `oxygen_delivery.md`,
`phenylephrine.md`, `rhythm.md`, `rrt.md`, `suspicion_of_infection.md`,
`urine_output.md`, `vasopressin.md`, `ventilator_setting.md`, and
`weight_durations.md`.  All fragments were treated as provisional.  The
ICU-Encounter identifier/period leads in `icustay_detail.md`,
`icustay_times.md`, `first_day_vitalsign.md`, `first_day_weight.md`, and
`weight_durations.md` were checked against the current 140-row Delta probe;
their concept-specific full-data claims were not adopted as facts.  The
dependency-relevant leads in `first_day_bg.md`, `chemistry.md`,
`coagulation.md`, `complete_blood_count.md`, `blood_differential.md`, and
`rrt.md` were not used to rederive either dependency; their completed
candidate carryovers were inspected instead.  The remaining fragments were
read but are not relevant to `meld` and were not independently verified for
this concept.  There is no `first_day_lab.md` or `first_day_rrt.md` fragment.

No genuinely new dataset-wide quirk was observed.  `MIMIC_NOTES.md` was not
edited, and nothing was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/meld.md`.

This reusable mapping is the carryover artifact at:

`mimic-iv/concepts_fhir/carryover/meld/fhir-prober.md`
