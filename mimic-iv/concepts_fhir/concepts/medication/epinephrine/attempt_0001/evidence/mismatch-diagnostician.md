# Mismatch-diagnostician evidence

The diagnostician inspected `LOOP_CONTRACT.md`, `MIMIC_NOTES.md` and all notes
fragments, the complete attempt artifacts and comparison report, the canonical
epinephrine SQL and oracle manifest, comparator implementation, and upstream
`mimic-fhir/sql/fhir_medication_administration_icu.sql` and UUID SQL.

Root cause is an intrinsic representability blocker, not a port bug. The
oracle requires key `(linkorderid, starttime)`, while the ICU FHIR ETL does not
read or write `inputevents.linkorderid`, has no usable
`MedicationAdministration.identifier`, and derives its opaque resource UUID
from `stay_id-orderid-itemid` instead. Demo source checks found 28/36 rows with
`orderid != linkorderid`, so even recovering orderid would not recover the
linkage. No exact FHIRPath exists.

The typed NULL declaration is factually correct but is rejected by the
comparator because an unrepresentable column cannot be part of the natural key;
removing the declaration would only conceal the same unalignable keyed result.
The full report is therefore an unresolvable `mismatch`, never a judge case.
No carryover stage was invalidated, no semantic counter was used, no retry was
made, and no new dataset-wide note was appended. The prescribed next action is
`mimic_utils block epinephrine` with the cited ETL and key evidence.
