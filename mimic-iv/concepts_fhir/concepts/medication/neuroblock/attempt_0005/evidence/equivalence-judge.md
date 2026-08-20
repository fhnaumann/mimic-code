# Equivalence-judge evidence — neuroblock attempt 0005

The independent judge returned `accept` for the `contested` review. It
confirmed `mimic-fhir/sql/fhir_medication_administration_icu.sql:20,40,44`
and exhaustive lines 42–101: `orderid` is used only in an opaque UUID and no
independent identifier, request, or orderid path is serialized. Recovering it
through resource-id parsing or UUID inversion is prohibited.

The judge ruled the loss ancillary rather than essential. Canonical
`neuroblock.sql:2–14` does not use orderid for inclusion, grouping,
aggregation, carry-forward, temporal logic, or clinical derivation, and the
full-oracle `(stay_id,starttime,endtime)` tuple is unique across all 14,174
rows. The manifest's orderid key is comparison metadata, so the
14,174/14,174 VOID DIFF counts do not measure fidelity. All defensible FHIR
mappings and required resource keys were applied. There are no divergent
dependencies.

Controller transition: `COMPLETED_WITH_DIVERGENCE`, accepted by the judge via
the cited justification. No new fragment entry was appended because the
neuroblock fragment already records the ICU MedicationAdministration
orderid-omission claim; the judge did not add a distinct unrecorded quirk.
