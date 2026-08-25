## Evidence block

**Concept:** `vasoactive_agent`  
**Attempt:** `0003`  
**Verdict:** `accept`  
**Tier:** `contested` (`paired_residual`)

The candidate and oracle each contain 665,529 rows; 665,527 are identical.
The only divergence is one `differing_conflict` on `norepinephrine` and one
`differing_null_only` on `phenylephrine`, with no missing or invented rows.

The norepinephrine conflict is inherited six-decimal precision loss in
`MedicationAdministration.dosage.rateQuantity.value`, written by
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`. The original
low-order precision is not present elsewhere in FHIR. The phenylephrine NULL
is inherited from omitted `inputevents.patientweight`, required by canonical
`phenylephrine.sql:5-7` and absent from the ETL projection at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`.

The phenylephrine absence is ancillary: its administration, boundaries, row
inclusion, grain, grouping, and timing remain intact; only one output rate
cell is NULL. Target `concept.sql:129-130,147-154,171-172` only propagates
dependency rates and introduces no independent divergence. No resource-id
inversion or estimate was used.

Acceptance justification: `vasoactive_agent` reproduces the canonical interval
construction and all 665,529 rows. Its sole norepinephrine conflict is
irrecoverable upstream Quantity precision loss, and its sole phenylephrine NULL
is an irrecoverable ancillary patientweight gap. The target is faithful as the
served representation allows.

No new dataset note was appended: the ICU MedicationAdministration
`patientweight` omission is already recorded in
`MIMIC_NOTES.d/vasoactive_agent.md`.
