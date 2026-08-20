# Equivalence judge evidence

- Concept: `phenylephrine`
- Attempt: `0003`
- Verdict: `accept` for the `contested` review; dependencies none and divergent dependencies `[]`.
- Evidence considered: full schema match; 193,260 oracle and candidate rows; zero true unpaired rows; 1,838 conflicts with 46 comparator-attributed DST rows; full-source replay closing all remaining residual endpoint groups and aligned values within tolerance; 191,422 null-only rows consisting of declared all-NULL `linkorderid` plus one row-level `vaso_rate` NULL.
- Cited upstream transformations: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` irreversibly casts/writes effective times through `TIMESTAMPTZ`; `:12,85-90` and `:14,91-99` serialize amount/rate at six-decimal Quantity precision; `:7-23,38-100` omits `linkorderid`, identifiers, and patientweight while retaining the rate-unit discriminator. The source wall times and discarded precision are not recoverable by FHIR query, and resource IDs remain opaque.
- Essentiality ruling: missing `linkorderid` is ancillary administrative linkage; the one identifiable `mcg/min` patientweight loss is an honest row-level NULL and does not affect inclusion, grain, grouping, or carry-forward; rate-null starttime is unexercised. Proven upstream DST loss is not essential-loss blocking under the contract.
- Result: the attempt faithfully reproduces every representable event and is accepted as `COMPLETED_WITH_DIVERGENCE`; no retry or carryover invalidation.
- Dataset-wide notes: no new quirk identified by the judge.
