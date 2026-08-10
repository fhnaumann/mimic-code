Evidence block — concept `acei`, stage `fhir-prober`.

Read the authoritative LOOP_CONTRACT.md and MIMIC_NOTES.md, the reusable source
analysis at `mimic-iv/concepts_fhir/carryover/acei/source-analyst.md`, and the
authoritative demo Delta with embedded Pathling 9.6.0 on Spark 4.0.2. The
prescription source maps to hospital MedicationRequest, with drug identity
reached through `medicationReference` to Medication. Patient and hospital
admission identifiers come from `identifier.value` and must be cast from FHIR
VARCHAR to INTEGER; the medication name comes from the
`mimic-medication-name` Medication identifier value; validity start/end map to
`dispenseRequest.validityPeriod.start/end` and must be cast to TIMESTAMP_NTZ.

The ten source ACEI substring predicates were confirmed against the served
Delta: 107/107 demo rows and exact per-name counts. The output is the drug name
under column `acei`, not the flag. Twelve source rows have `starttime > stoptime`;
the upstream ETL omits their validity Period, so both FHIR timestamps are
intrinsically absent and must remain typed NULLs after the FHIR mapping.

Concept-level mapping was written to and recorded in
`mimic-iv/concepts_fhir/carryover/acei/fhir-prober.md`. The probe added these
dataset-wide MIMIC_NOTES.md entries (existing entries were reused):
`Prescription Medication.code prefers NDC/formulary; the source drug name is in
an identifier` and `MedicationRequest omits invalid or incomplete prescription
validity periods`. No immutable attempt artifact was modified.
