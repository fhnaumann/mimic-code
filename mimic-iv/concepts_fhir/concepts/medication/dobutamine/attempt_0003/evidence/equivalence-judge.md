# Equivalence judge evidence

- Concept: `dobutamine`
- Attempt: `0003`
- Verdict: `accept` for the `review` / `gap_shaped` full-data result.
- Cited gap: `MedicationAdministration.identifier.value` and any other input-event/link-order identifier are absent from the ICU ETL (`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`); typed NULL faithfully explains 8,511 `differing_null_only` rows. All defensible mappings were used, and the loss is ancillary to this concept's `(stay_id,starttime)` grain and clinical outputs.
- Attributed remainder: the sole `endtime` conflict and the one `only_oracle`/`only_candidate` key pair are completely attributed with zero residual to the upstream `TIMESTAMPTZ` casts writing `MedicationAdministration.effectivePeriod.start/end` (`mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`). The affected fraction is 1/8,513 (0.0117%), consistent with DST-gap rarity; no resource-id inversion was used.
- Fidelity: 0/8,513 total identical because the declared gap is counted; 8,511/8,513 (99.9765%) representable fidelity.
- Divergent dependencies: none.

Judge justification: “ICU MedicationAdministration does not populate `identifier.value` or another recoverable input-event/link-order identifier; `fhir_medication_administration_icu.sql:7-23,38-100` omits `linkorderid` and uses `orderid` only inside an opaque UUID. Typed NULL therefore faithfully explains the 8,511 null-only rows. The remaining endtime conflict and re-keyed row are completely attributed, with zero residual, to the `TIMESTAMPTZ` casts writing `effectivePeriod.start/end` at lines 8-9 and 61-69. The ancillary identifier loss does not alter row inclusion, grain, grouping, carry-forward, or clinical outputs.”
