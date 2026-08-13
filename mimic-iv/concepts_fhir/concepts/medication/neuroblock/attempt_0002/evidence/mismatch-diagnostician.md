Evidence block:

Concept: neuroblock
Attempt: 0002

The apparent `only_candidate`/`only_oracle` divergence is a manifest-key artefact: declared-unrepresentable `orderid` is the manifest key, so no candidate row can join. Both sides contain 14,174 rows and the schema matches; the comparator marks the result VOID DIFF.

The upstream ETL irreversibly transforms `inputevents.orderid` into opaque resource identity: `mimic-fhir/sql/fhir_medication_administration_icu.sql:20` includes orderid in UUID generation, and lines 40–44 serialize that UUID as `MedicationAdministration.id`. The resource construction contains no independent `identifier`, `request`, or semantic orderid field. UUID inversion is forbidden.

The diagnosis is an ancillary upstream transformation/representability gap, not a port bug. Full-oracle measurement supplied by the neuroblock fragment establishes the representable clinical grain `(stay_id,starttime,endtime)` as unique for all 14,174 rows; `(stay_id,starttime)` has one collision. The canonical SQL does not use orderid for filtering, grouping, aggregation, or clinical calculations. Keep typed NULL orderid and its declaration; do not retry or infer it from resource identity. No carryover stage is invalidated and no files were modified.
