# Mismatch-diagnostician evidence

- Concept: `norepinephrine_equivalent_dose`, replay attempt `0003`.
- Verdict under diagnosis: `review`, tier `contested`, classification `unavailable_no_key`; schema matched.
- The target SQL faithfully reproduces the canonical formula and consumes the completed `vasoactive_agent` dependency. No target-side filter, grouping, or join bug was identified; no carryover invalidation is warranted.
- Full diff: oracle 619,330 rows; candidate 619,329; `only_oracle=1,707`, `only_candidate=1,706`; residual pairing was unanchored and paired 0.
- Primary inherited loss: ICU MedicationAdministration rate values are serialized at six-decimal precision. `mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99` selects/writes the rate, with no alternate element retaining discarded low-order digits. The downstream `vasoactive_agent` boundary/containment logic and target four-place rounding can therefore differ near boundaries.
- One missing interval: `phenylephrine.sql:5-7` needs `rate / patientweight` for `mcg/min`; `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` does not serialize `patientweight` or an exact normalized equivalent. This accounts for the one-row deficit where no other pressor is active. `linkorderid` omission is irrelevant to this concept.
- UTC rebuild reached this path: starttime drift fell 162→1, endtime 164→1, stay-id 24→1, and row delta +20→−1 versus the prior attempt. The remaining time/id marginal belongs to the missing interval, not a residual DST shift.
- Recommendation: do not retry or re-author; send to the equivalence judge as inherited upstream transformation/coverage loss.
- Relevant sibling fragments were checked as unconfirmed leads and corroborated by curated notes/upstream ETL; none was cited as evidence. No dataset-wide note was appended.
