## ICU MedicationAdministration does not carry an inputevent identifier
- Affected: `MedicationAdministration.identifier` and recovery of `mimiciv_icu.inputevents.linkorderid`
- Verified: dopamine attempt_0001 authoritative Delta probe counted 56,535 `MedicationAdministration` resources and `identifier IS NOT NULL` on 0/56,535; the ICU ETL (`mimic-fhir/sql/fhir_medication_administration_icu.sql:20-23,38-100`) writes no inputevent identifier or `linkorderid`, while the dopamine DuckDB source has `linkorderid` non-null on 28/28 rows. The resource UUID uses `orderid` as an opaque input and cannot be inverted to `linkorderid`.

## ICU MedicationAdministration dosage quantities are limited to six decimal places in served Delta
- Affected: `MedicationAdministration.dosage.rateQuantity.value` and `MedicationAdministration.dosage.dose.value`
- Verified: dopamine attempt_0001 embedded Pathling probe saw raw Delta Quantity values as `decimal(32,6)` and 28/28 target rate and amount values populated; after the required `FLOAT` cast, source/FHIR values agreed bitwise on 7/28 rates and 22/28 amounts, but agreed within `1e-6` on 28/28 for each (maximum absolute difference `9.536743e-7`).
