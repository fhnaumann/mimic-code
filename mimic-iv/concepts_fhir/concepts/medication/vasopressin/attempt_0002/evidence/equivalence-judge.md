# Equivalence-judge evidence — vasopressin attempt 0002

The independent equivalence judge read the authoritative `MIMIC_NOTES.md`,
the complete current comparison, canonical SQL, upstream ICU Medication-
Administration ETL, state/reopen history, and both attempt artifact sets. It
also confirmed `divergent_dependencies('vasopressin') == []`. No files or
controller state were changed.

Verdict: **accept** for the `review`, `gap_shaped` result. The judge found no
served mapping for `inputevents.linkorderid` at
`MedicationAdministration.identifier.value` or
`MedicationAdministration.supportingInformation.reference`; the ICU ETL does
not select or write it (`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-103`).
The resource id is opaque and cannot be inverted. The typed-NULL declaration
therefore explains the 25,891 `differing_null_only` rows, while the field is
ancillary to the `(stay_id,starttime)` grain, inclusion, grouping,
carry-forward, and vaso outputs. All defensible effective[x], Quantity, and
datetime mappings were tried.

The single `endtime` conflict was independently accepted as upstream loss:
`mimic-fhir/sql/fhir_medication_administration_icu.sql:9,61-69` writes the
TIMESTAMPTZ-transformed effective endpoint, and the comparator replayed 1/1
conflicts with zero residual at 1/25,892, consistent with DST-gap rarity. No
new dataset-wide quirk was identified for the fragment.
