## Evidence

- Read: `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, canonical antibiotic SQL, replay attempt history, and fresh `comparison.full.json`.
- Checked: the independent judge verified the gap-shaped paired residual. `MedicationRequest.dispenseRequest.validityPeriod.start` and `.end` are absent for invalid or incomplete prescription intervals under `mimic-fhir/sql/fhir_medication_request.sql:172-177`; no alternate served element preserves the source endpoints. Direct and medication-mix mappings, filters, datetime casts, and ICU encounter linkage were exhausted.
- Result: `blocked`. The 43,453 null-only residual rows are intrinsic but essential: missing `starttime` removes 13,494 ICU assignments and destroys temporal event grain used by downstream infection-window logic. Fidelity is 692,009/735,462 (94.0917%); conflicts and true only-candidate/oracle rows are zero.
- Artifacts: judge evidence recorded here; comparator source is `comparison.full.json` in this attempt directory.
