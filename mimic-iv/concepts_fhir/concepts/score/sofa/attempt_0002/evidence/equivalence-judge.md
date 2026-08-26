## Equivalence judge evidence

The independent judge read `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, the
canonical SOFA SQL, both attempts' SQL/ViewDefinitions/comparisons/evidence,
carryover, run metadata, relevant dependency states, and the cited upstream
MedicationAdministration ETL.

Verdict: **blocked**. The divergence is intrinsic rather than a remaining SOFA
SQL/ViewDefinition bug. `mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`,
especially line 94, writes `ie_RATE` as the semantic
`MedicationAdministration.dosage.rateQuantity.value`; Pathling then
non-injectively encodes the FHIR decimal as `DECIMAL(32,6)`. Discarded digits
are absent from the scale/canonicalized companions and other values, and
opaque resource identity cannot be used for recovery.

Attempt_0002 exhausted the defensible SOFA correction by FLOAT-typing the
`15`, `0.1`, `5`, and `0` thresholds. The residual is 1,138 conflicts among
6,043,902 rows (99.9812% identical/representable): `cardiovascular` 294,
`cardiovascular_24hours` 1,022, `sofa_24hours` 1,022, and
`rate_norepinephrine` 1. The four vasoactive divergent dependencies carry the
loss; `vitalsign` is not causal because `meanbp_min` has no conflict. The
24-row carry-forward makes the lost threshold side alter clinically meaningful
cardiovascular and total SOFA outputs. Under the contract's essential-loss
rule, publishing ordinary SOFA values would conceal ambiguity, so the judge
blocked the concept despite the small affected fraction.

No files, fragments, or implementation artifacts were changed by the judge;
no HPC run or commit was performed. The cited upstream path and the full
comparison are the terminal evidence.
