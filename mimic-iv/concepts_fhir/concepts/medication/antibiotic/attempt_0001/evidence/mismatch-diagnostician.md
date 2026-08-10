Evidence block:

- Read the full comparison, run metadata, canonical SQL, all implementation ViewDefinitions/SQL, both carryovers, LOOP_CONTRACT.md, AGENTS.md, MIMIC_NOTES.md, and the cited prescription ETL SQL.
- Diagnosis: no fixable port bug. An exhaustive full-data `EXCEPT ALL` pairing accounted for the divergence: 43,453 candidate-only NULL `starttime`/`stoptime`/`stay_id` tuples pair with invalid or incomplete oracle intervals, and 123 valid tuples differ by exactly +3,600 seconds from upstream DST normalization.
- Citations: `mimic-fhir/sql/fhir_medication_request.sql:172-177` omits invalid/incomplete `dispenseRequest.validityPeriod`; `:55,124` shows `authoredOn` is pharmacy `entertime`, not a source endpoint; `:43-44` casts endpoints through `TIMESTAMPTZ`, irreversibly normalizing DST-gap times. Without the original start, the canonical ICU half-open temporal join cannot be inverted.
- The no-key `full_tuple_multiset` comparator mirrors each NULL/rewrite divergence as `only_candidate` and `only_oracle`; the apparent candidate-only rows are not invented prescriptions. Omitted `drug_type` is intrinsically absent but neutral for this full result, with zero residual tuples attributable to it.
- Both source and FHIR carryover stages are correct; no invalidation and no retry are indicated. Proceed to the equivalence judge with this ETL citation.
- Existing `MIMIC_NOTES.md` validity-period and datetime entries were updated with this attempt's full-data counts; no new dataset-wide entry was added.
