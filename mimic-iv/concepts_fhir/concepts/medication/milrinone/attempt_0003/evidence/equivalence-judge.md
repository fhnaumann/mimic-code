# Equivalence-judge evidence — milrinone attempt 0003

- Independent verdict: `accept` for the `gap_shaped` review.
- The ICU MedicationAdministration FHIR representation has no
  `linkorderid` element: it is absent from `MedicationAdministration.identifier`,
  `supportingInformation`, and the ICU ETL projection at
  `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`.
- This explains all 9,573 `differing_null_only` rows on the declared typed-NULL
  `linkorderid`; there were no row-presence divergences or conflicts, and all
  9,573 rows matched on representable columns.
- The exact medication code/system, ICU Encounter identifier mapping, both
  effective[x] variants, `TIMESTAMP_NTZ`, Quantity casts, and permitted opaque
  equality joins were exhausted. Resource-id inversion is forbidden.
- `linkorderid` is ancillary and does not affect inclusion, the comparison key
  `(stay_id,starttime)`, grouping, windows, or clinical values. There are no
  divergent dependencies.

The judge's justification was recorded verbatim in the controller transition.
No new dataset-wide quirk was found and no notes fragment was appended.
