## Evidence block

Concept `vasoactive_agent`, attempt `0003`, verdict `review`, tier
`contested`, classification `paired_residual`. Candidate and oracle each
contain 665,529 rows; 665,527 are identical. Divergence consists of one
`differing_conflict` on `norepinephrine` and one `differing_null_only` on
`phenylephrine`, with zero `only_oracle` and zero `only_candidate`.

Both residuals are inherited dependency divergence, not target logic. The
norepinephrine conflict is upstream six-decimal Quantity precision loss at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`; the original
low-order precision cannot be recovered by any FHIR query. The phenylephrine
NULL is the accepted row-level absence inherited from phenylephrine: canonical
`phenylephrine.sql:5-7` needs `patientweight`, omitted by
`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`.
`concept.sql:129-130,147-154,171-172` directly propagates these dependency
rates and introduces no transformation. No target fix or re-authoring is
indicated.

Completed divergent dependencies checked: dobutamine attempt_0004, dopamine
attempt_0003, epinephrine attempt_0003, milrinone attempt_0003, norepinephrine
attempt_0004, phenylephrine attempt_0004, and vasopressin attempt_0003. Only
norepinephrine and phenylephrine explain the target residuals; shared
`linkorderid` divergence is not consumed.

Curated `MIMIC_NOTES.md` entries and the provisional sibling leads
`MIMIC_NOTES.d/norepinephrine.md`, `phenylephrine.md`, `milrinone.md`,
`dobutamine.md`, and `vasoactive_agent.md` were checked. The fragments were
not cited as evidence. No carryover stage is at fault and no fragment entry
was appended.
