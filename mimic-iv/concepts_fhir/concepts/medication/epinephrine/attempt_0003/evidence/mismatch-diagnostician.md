Evidence

## Diagnosis

Root cause is not a port bug. `inputevents.linkorderid` is discarded by the upstream ICU MedicationAdministration ETL, while the comparator manifest key includes that unrepresentable column. The keyed diff cannot align any rows; its 24,470 `only_oracle` plus 24,470 `only_candidate` findings are explicitly VOID comparison-key artifacts.

The canonical query projects `linkorderid` directly but never uses it for filtering, joining, grouping, or computation (`mimic-iv/concepts/medication/epinephrine.sql:3-10`). Attempt 0003 correctly emits a typed NULL at `concept.sql:32-40`.

## Upstream evidence

`/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql` proves the loss:

- Lines 7-23 select source attributes retained by the ETL; `linkorderid` is not selected.
- Line 20 generates an opaque UUID from `stay_id`, `orderid`, and `itemid`; its UUID inputs do not include `linkorderid`.
- Lines 38-100 construct MedicationAdministration JSON with id, medication coding, subject, context, effective time, category, and dosage, but no `identifier`, `linkorderid`, or order-link reference.

Therefore no FHIR query can recover `linkorderid`: it exists in neither a semantic element nor a reference. Parsing or regenerating the UUID is prohibited and would not recover `linkorderid` anyway.

## Essentiality and grain

The loss is ancillary rather than essential. The source SQL uses `linkorderid` only as an output column. Full-oracle evidence records 24,470 rows, 24,466 distinct `(stay_id,starttime)` tuples (four collisions), but 24,470 distinct `(stay_id,starttime,endtime)` tuples. A unique clinical row identity therefore exists using representable columns; manifest key `(linkorderid,starttime)` is comparison metadata selected by the size-first key search, not proof that linkorderid defines semantic grain.

The DST replay attributed zero rows and is irrelevant to this residual. No retry is needed. Keep the typed-NULL declaration/current mapping and route this review to the equivalence judge with the ETL citation. Neither carryover stage is faulty.

## Evidence block

Concept `epinephrine`, attempt `0003`, verdict `review`, tier `contested`. Reported classes are 24,470 `only_oracle` and 24,470 `only_candidate`; both are VOID DIFF artifacts caused by unrepresentable `linkorderid` in manifest key `(linkorderid,starttime)`. There are zero actual `differing_conflict` and zero `differing_null_only` rows. Diagnosis: upstream ETL representation loss, not a fixable port bug. Citation: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`, especially UUID construction at line 20 and JSON projection at lines 42-100. No fragment was appended and no artifacts were modified.
