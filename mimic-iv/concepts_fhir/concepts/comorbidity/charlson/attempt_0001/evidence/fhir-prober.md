# FHIR-prober evidence — charlson attempt 0001

The prober read the source and age carryovers, `MIMIC_NOTES.md`, all notes
fragments as provisional leads, and the local authoritative Delta. It mapped
hospital admissions to `Encounter` selected by the exact hospital identifier
system, patients to `Patient.identifier`, and diagnoses to `Condition` joined
through opaque Encounter reference/resource keys. The demo had 275 hospital
Encounters, 4,506 hospital Conditions, one coding per Condition, and exact
identifier/reference/code tuple agreement with the demo relational oracle.
The served diagnosis systems were proprietary `mimic-diagnosis-icd9` and
`mimic-diagnosis-icd10`; all literal code tests were confirmed without
translation. `Patient.birthDate` is the only age-related field and cannot
exactly recover `anchor_age`/`anchor_year`; full-data age evidence bounds the
inherited age-score issue at 460/431,231 admissions. Diagnosis timing/status is
absent but ancillary to Charlson. Resource/reference ids were used only for
equality joins.

Artifacts:
- `mimic-iv/concepts_fhir/carryover/charlson/fhir-prober.md`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/charlson.md` (two provisional
  dataset-wide findings appended by the prober)
