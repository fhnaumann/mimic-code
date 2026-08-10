# Source analyst evidence

Concept: `arb`.

Read `mimic-iv/concepts/medication/arb.sql`, `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`, and `mimic-iv/concepts_fhir/MIMIC_NOTES.md`. The SQL has no dependencies and reads `mimiciv_hosp.prescriptions`. It selects distinct prescription rows whose free-text `drug` contains, case-insensitively, one of 16 ARB generic/brand tokens: AZILSARTAN, CANDESARTAN, IRBESARTAN, LOSARTAN, OLMESARTAN, TELMISARTAN, VALSARTAN, SACUBITRIL, EDARBI, ATACAND, AVAPRO, COZAAR, BENICAR, MICARDIS, DIOVAN, or ENTRESTO. Output columns are `subject_id`, `hadm_id`, `arb` (the source drug text), `starttime`, and `stoptime`; there is no time-window or `drug_type` filter.

The FHIR mapping must use medication-name identifiers and support direct medication references plus prescription medication-mix ingredient references. Existing medication-name/mix quirks in `MIMIC_NOTES.md` apply; no new dataset-wide quirk was found.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/arb/source-analyst.md`, recorded with `mimic_utils carryover-record arb --stage source-analyst`.
