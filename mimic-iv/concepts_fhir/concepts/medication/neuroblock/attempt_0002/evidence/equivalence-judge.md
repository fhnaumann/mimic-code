Evidence block:

Concept: neuroblock
Attempt: 0002

Judge verdict: `accept` for the `contested` review. `inputevents.orderid` is irreversibly incorporated into opaque `MedicationAdministration.id` by `mimic-fhir/sql/fhir_medication_administration_icu.sql:20,40,44`; the exhaustive resource construction at lines 43–100 provides no independent identifier, request, or orderid path. UUID inversion is forbidden.

The loss is ancillary: canonical `neuroblock.sql` selects orderid but does not use it for inclusion, grouping, aggregation, temporal logic, or clinical computation. The full-oracle representable-grain measurement establishes `(stay_id,starttime,endtime)` as unique across all 14,174 rows, resolving the one `(stay_id,starttime)` collision. Exact codes, both effective variants, numeric Quantity casts, TIMESTAMP_NTZ, and the ICU Encounter identifier mapping were applied.

The reported 14,174 `only_candidate` and 14,174 `only_oracle` rows are VOID DIFF artefacts of the declared NULL manifest key; 0.00% identical_fraction is not a fidelity measure here and no representable_fraction was emitted. No divergent dependencies. The dataset-wide ICU MedicationAdministration orderid omission is already recorded in `MIMIC_NOTES.d/neuroblock.md`; no new fragment entry was needed.
