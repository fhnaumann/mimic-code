Equivalence judge for `sepsis3` attempt_0001.

**Verdict: accept.** The full comparator result is `review`, tier `contested`:
380 `differing_conflict` rows and 177 `only_oracle` rows, with zero
`only_candidate` and zero null-only rows. Fidelity is 32,414/32,971 = 98.3106%;
there are no declared unrepresentable columns, so representable fidelity is
the same.

The judge found the 177 missing rows and all 380 conflicts wholly inherited from
already accepted dependencies. `sepsis3` preserves canonical
`sepsis3.sql:9-80`: SOFA >=2, inclusive -48/+24-hour join, one-row-per-stay
ordering, and dependency boundaries; it introduces no independent
representation loss.

Medication loss originates at
`mimic-fhir/sql/fhir_medication_request.sql:172-177`, whose guard emits
MedicationRequest validity endpoints only for complete, non-reversed intervals.
`authoredOn` is pharmacy entry time, other resources have different grains, and
opaque identifiers cannot recover the original endpoints. Accepted
`suspicion_of_infection` propagates this through `ab_id` ordering and culture
windows, changing Sepsis-3 inclusion, selected suspicion/SOFA rows, and timing.

SOFA loss crosses the ETL/encoder boundary at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99` (especially
line 94), where `ie.rate` is written unchanged and Pathling then encodes it at
`DECIMAL(32,6)`. The discarded digits are absent from all served carriers;
`mimic-iv/concepts/score/sofa.sql:278-285,370-375` amplifies the loss through
cardiovascular scoring and its 24-row window.

No DST divergence was accepted: the run used the rebuilt 2026-08-26 warehouse,
antibiotic attempt_0004 had zero post-rebuild DST conflicts, and this comparison
attributed 0/380. Direct divergent dependencies are `suspicion_of_infection`
attempt_0001 (`COMPLETED_WITH_DIVERGENCE`, judge-accepted) and `sofa`
attempt_0002 (`COMPLETED_WITH_DIVERGENCE`, human-accepted); nested `antibiotic`
attempt_0004 is human-accepted. The dependency contract requires accepting
this faithful consumer rather than re-blocking inherited loss, even where it
changes row inclusion or clinically meaningful outputs.

The judge read `MIMIC_NOTES.md` only and wrote nothing. No new dataset-wide
quirk was identified; no fragment was appended.
