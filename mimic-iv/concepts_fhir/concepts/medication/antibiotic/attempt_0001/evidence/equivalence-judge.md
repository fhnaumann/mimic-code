Evidence block:

- Judge verdict: `accept` for attempt 0001, tier `contested`, `full_tuple_multiset`, `unavailable_no_key`.
- FHIR paths and ETL citations: `MedicationRequest.dispenseRequest.validityPeriod.start/end` are absent for invalid/incomplete intervals because `mimic-fhir/sql/fhir_medication_request.sql:172-177` omits the period; `authoredOn` at `:55,124` is pharmacy `entertime` and cannot substitute. The same ETL's `:43-44` applies irreversible `TIMESTAMPTZ` normalization to valid DST-gap endpoints.
- No-key ambiguity was resolved by exhaustive multiset pairing: all 43,453 NULL-time tuples paired with invalid/incomplete oracle tuples and all 123 remaining tuples paired with documented +3,600-second rewrites, leaving no invented or residual rows. All direct and mix mappings and source filters were exhausted; absent `drug_type` caused no residual divergence.
- Fidelity: 691,886/735,462 exact tuples implied (94.075%); `identical_fraction` and `representable_fraction` were not emitted for this unkeyed comparison.
- No divergent dependencies and no carryover invalidation required. The judge did not edit files or MIMIC_NOTES.md.
