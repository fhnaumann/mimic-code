## ICU inputevent linkorderid is not represented in MedicationAdministration
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: dobutamine embedded Pathling/Spark probe over the authoritative demo Delta found 0/44 target resources with an identifier; the same raw-schema probe found 0/20,404 ICU `mimic-medication-icu` resources with an identifier, and `mimic-fhir/sql/fhir_medication_administration_icu.sql:19-23,38-69` writes no linkorderid/orderid identifier.

## ICU inputevent effective[x] conditionally encodes the rate-bearing interval
- Affected: `MedicationAdministration.effective[x]`
- Verified: `mimic-fhir/sql/fhir_medication_administration_icu.sql:61-69` writes `effectivePeriod` (source start/end) when rate is non-null and `effectiveDateTime` (source endtime only) otherwise; the authoritative Delta had 11,038 Period and 9,366 dateTime ICU inputevent resources, while dobutamine had Period.start/end 44/44 and dateTime 0/44.

## ICU inputevent Quantity values are served at decimal scale six
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: the embedded Pathling 9.6.0 schema reports both as `decimal(32,6)`; demo DuckDB/Delta comparison for dobutamine found `vaso_rate` 16/44 and `vaso_amount` 36/44 binary-exact after FLOAT casts, with all rates within 1e-6 and maximum amount difference 1.5258789e-05.
