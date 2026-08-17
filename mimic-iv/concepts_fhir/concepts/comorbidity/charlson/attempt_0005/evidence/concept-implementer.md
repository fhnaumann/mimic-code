Implementation complete for `charlson`, attempt `0005`.

Evidence:
- Created:
  - `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/ViewDefinition.condition.json`
  - `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/ViewDefinition.encounter.json`
  - `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/ViewDefinition.patient.json`
  - `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/concept.sql`
- Used Condition, hospital Encounter, Patient, and the `age` dependency. Preserved all 17 flags, exact proprietary ICD systems/literals, opaque-key joins, hospital filtering, weighted arithmetic, manifest casts, and `patient_key`/`encounter_key`.
- Confirmed the reopened fix: `com` groups by `e.encounter_key`; `ag` projects `src_age.encounter_key`; both joins use `e.encounter_key`; hospital filtering remains `e.hadm_id_str IS NOT NULL`.
- Validated all ViewDefinition JSON files and ran `uv run mimic_utils lint-sql charlson`: clean.
- No `unrepresentable.json` was required. Age/anchor loss remains inherited through `age`; no estimate was introduced.
- Read the canonical SQL, source/FHIR carryover analyses, age attempt artifacts, manifest, full `MIMIC_NOTES.md`, and all `MIMIC_NOTES.d/*.md` fragments. Applied the identifier/opaque-key, hospital Encounter, Condition stream, and inherited age-divergence guidance. Other fragments were treated as provisional and not cited as evidence.
- No new dataset-wide quirk was discovered; no fragment was appended.
