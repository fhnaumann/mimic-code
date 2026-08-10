# Evidence: source-analyst

The source analyst read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical
`mimic-iv/concepts/medication/acei.sql`, the DAG, oracle manifest, and relevant
prescriptions DDL. The SQL is dependency-free and scans
`mimiciv_hosp.prescriptions`, retaining rows whose free-text `drug` contains
one of ten ACE inhibitor names case-insensitively. It outputs
`subject_id`, `hadm_id`, `pr.drug AS acei`, `starttime`, and `stoptime`, with no
output deduplication. The manifest has 112,014 rows and uses an unkeyed
full-tuple multiset comparison.

The analyst identified the applicable shared notes: medication-name coding
uses readable `Coding.code` even when display is null, and
`MedicationAdministration.effective[x]` is polymorphic and requires both
dateTime and Period variants. No new dataset-wide quirk was reported.

Artifact: `mimic-iv/concepts_fhir/carryover/acei/source-analyst.md`.
