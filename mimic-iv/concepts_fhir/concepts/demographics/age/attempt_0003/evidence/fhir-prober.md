# Evidence: fhir-prober

## Read and checked

The probe read `AGENTS.md`, `LOOP_CONTRACT.md`, curated
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, the age source carryover, the current
FHIR mapping conventions, and all existing `MIMIC_NOTES.d/` fragments as
provisional leads. It re-probed the authoritative demo Delta/Spark warehouse.

## Results

- Hospital Encounter is selected by identifier system
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`; demo counts are
  275 hospital, 140 ICU, and 222 ED Encounters.
- Patient count is 100. Encounter `getResourceKey()` and
  `subject.getReferenceKey(Patient)` are populated 637/637 and join exactly
  637/637. Hospital `period.start` is populated 275/275 and Patient
  `birthDate` is populated 100/100.
- Required mappings are `getResourceKey()` → `encounter_key`,
  `subject.getReferenceKey(Patient)` → `patient_key`, hospital identifier
  value → `hadm_id_str`, `period.start` → `period_start`, Patient
  `getResourceKey()` → `patient_key`, Patient identifier value →
  `subject_id_str`, and `birthDate` → `birth_date`.
- Identifier values are FHIR strings and must be cast to the manifest's integer
  `subject_id`/`hadm_id` outputs. Datetimes must be cast to
  `TIMESTAMP_NTZ` before year extraction.
- `anchor_age` and `anchor_year` have no FHIR path; the implementation must
  emit typed `CAST(NULL AS SMALLINT)` columns. Age is derived as
  `YEAR(CAST(period_start AS TIMESTAMP_NTZ)) - YEAR(CAST(birth_date AS DATE))`.
- The demo formula matched 275/275, but full-data representability is weaker:
  upstream `Patient.birthDate` uses `MIN(transfers.intime) - anchor_age`, so
  the anchor pair is not exactly recoverable. The established full evidence is
  460/431,231 age conflicts and 44/431,231 DST admission-time conflicts.
- Resource IDs remain opaque: no parsing, regeneration, hashing, hardcoding, or
  semantic inference from ID equality is used.

No new dataset-wide quirk was discovered beyond the curated notes, so no
`MIMIC_NOTES.d/age.md` fragment was appended.

## Artifacts

- Updated and recorded: `mimic-iv/concepts_fhir/carryover/age/fhir-prober.md`
- Carryover ledger: `mimic-iv/concepts_fhir/carryover/age/carryover.json`
- No attempt implementation artifacts were authored by this stage.
