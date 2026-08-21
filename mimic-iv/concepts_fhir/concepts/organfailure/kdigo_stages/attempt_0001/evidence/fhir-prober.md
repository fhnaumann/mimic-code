## Evidence block — `kdigo_stages`

Read:
- Source analysis and canonical SQL.
- `MIMIC_NOTES.md`.
- Canonical ViewDefinition reference.
- Relevant fragments: `README.md`, `crrt.md`, `kdigo_creatinine.md`, `kdigo_uo.md`, `urine_output.md`, `first_day_urine_output.md`, `weight_durations.md`, `first_day_weight.md`, `icustay_times.md`, `icustay_detail.md`, `rrt.md`, `creatinine_baseline.md`.
- Completed dependency mappings/attempt evidence for `kdigo_creatinine`, `kdigo_uo`, and `crrt`.

### Resource mappings

- `mimiciv_icu.icustays` → ICU `Encounter`, selected by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`.
- `icustays.subject_id` → ICU Encounter subject reference → `Patient.identifier`.
- `icustays.hadm_id` → ICU Encounter `partOf` reference → hospital `Encounter.identifier`.
- `icustays.stay_id` → ICU Encounter ICU identifier.
- `icustays.intime` → ICU Encounter `period.start`.

### Canonical mappings

- ICU Encounter key: `{path: "getResourceKey()", name: "icu_encounter_key"}`
- Patient reference: `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}`
- Hospital parent reference: `{path: "partOf.getReferenceKey(Encounter)", name: "parent_encounter_key"}`
- ICU stay identifier: `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}`
- ICU admission time: `{path: "period.start", name: "intime_datetime"}`
- Patient identifier: `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}`
- Hospital encounter key: `{path: "getResourceKey()", name: "encounter_key"}`
- Hospital admission identifier: `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}`

FHIR aliases are `STRING`/`VARCHAR`; cast identifier aliases to `INTEGER`. Resource/reference keys remain opaque, type-prefixed strings and must be emitted verbatim.

### Probe results

Embedded Pathling/Spark over `/Users/nau025/warehouses/mimic-iv-demo/delta`:

- ICU Encounter stream: 140/140 selected rows.
- ICU key, patient key, parent key, `stay_id_str`, and `intime_datetime`: 140/140 non-null.
- Hospital Encounter: 275/275 `hadm_id_str` non-null.
- Patient: 100/100 `subject_id_str` non-null.
- ICU parent → hospital Encounter key join: 140/140.
- ICU patient reference → Patient key join: 140/140.
- Identifier systems: ED 222, hospital 275, ICU 140; 637 identifier rows over 637 resources, ratio 1.000.
- Nested `subject.identifier.value` and `partOf.identifier.value`: 0/140; reference-key joins are required.
- `Encounter.period.start` is scalar `dateTime`; no choice-type datetime variants apply.

DuckDB agreement against `mimiciv_icu.icustays`: subject_id 140/140, hadm_id 140/140, stay_id 140/140, and intime wall-clock 140/140 exact.

### Dependency consumption

Consume completed views as tables named `kdigo_creatinine`, `kdigo_uo`, and `crrt`; do not rederive them from FHIR resources.

Join all dependencies to the ICU base using `icu_encounter_key`, not numeric IDs:

- `kdigo_creatinine`: `charttime`, creatinine values, `icu_encounter_key`, `patient_key`, `encounter_key`.
- `kdigo_uo`: `charttime`, rates/durations, weight, `icu_encounter_key`, `patient_key`.
- `crrt`: `charttime`, `crrt_mode`, `icu_encounter_key`, `patient_key`.

Build the event axis from distinct `(icu_encounter_key, charttime)` pairs. Partition smoothing by `patient_key`; emit numeric identifiers from the ICU/Patient/parent Encounter spine.

### Codes

`kdigo_stages.sql` has no coded filter, so its direct code set and coding-per-resource ratio are **N/A**. `crrt_mode IS NOT NULL` is non-coded and belongs to the completed `crrt` dependency.

### Gaps

- `subject_id` and `hadm_id`: absent as direct ICU Encounter fields but exactly derivable through FHIR reference-key joins; no demo gap.
- Original pre-ETL `intime` during DST spring-forward gaps: not representable from `Encounter.period.start`. Demo impact was 0/140, but the value is potentially essential because it controls the six-hour UO branch and smoothing order. Use `TIMESTAMP_NTZ`; never recover it from resource IDs. Full-data comparison/judge must assess downstream impact.
- Resource IDs are opaque and were not parsed, regenerated, or used to infer clinical values.

No new dataset-wide quirk was found. `MIMIC_NOTES.md` was not edited, and no entry was appended to `MIMIC_NOTES.d/kdigo_stages.md`.

Artifacts:
- Mapping: `mimic-iv/concepts_fhir/carryover/kdigo_stages/fhir-prober.md`
- Carryover recorded successfully with: `uv run mimic_utils carryover-record kdigo_stages --stage fhir-prober`
- Carryover ledger: `mimic-iv/concepts_fhir/carryover/kdigo_stages/carryover.json`

No attempt ViewDefinition, concept SQL, or commit was created.
