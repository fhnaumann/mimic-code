## ICU inputevent linkorderid is not represented in MedicationAdministration
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: dobutamine embedded Pathling/Spark probe over the authoritative demo Delta found 0/44 target resources with an identifier; the same raw-schema probe found 0/20,404 ICU `mimic-medication-icu` resources with an identifier, and `mimic-fhir/sql/fhir_medication_administration_icu.sql:19-23,38-69` writes no linkorderid/orderid identifier.

## ICU inputevent effective[x] conditionally encodes the rate-bearing interval
- Affected: `MedicationAdministration.effective[x]`
- Verified: `mimic-fhir/sql/fhir_medication_administration_icu.sql:61-69` writes `effectivePeriod` (source start/end) when rate is non-null and `effectiveDateTime` (source endtime only) otherwise; the authoritative Delta had 11,038 Period and 9,366 dateTime ICU inputevent resources, while dobutamine had Period.start/end 44/44 and dateTime 0/44.

## ICU inputevent Quantity values are served at decimal scale six
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: the embedded Pathling 9.6.0 schema reports both as `decimal(32,6)`; demo DuckDB/Delta comparison for dobutamine found `vaso_rate` 16/44 and `vaso_amount` 36/44 binary-exact after FLOAT casts, with all rates within 1e-6 and maximum amount difference 1.5258789e-05.

## ICU MedicationAdministration effective periods irreversibly normalize DST-gap wall times
- Affected: `MedicationAdministration.effectivePeriod.start`, `MedicationAdministration.effectivePeriod.end`, and `MedicationAdministration.id` for ICU inputevents
- Verified: `dobutamine` attempt 0002 had one oracle-only/candidate-only key substitution (`stay_id=37725403`, source `starttime=2165-03-10 02:28` versus FHIR `03:28`) and one `endtime` conflict at the same 02:28 boundary, both exactly the America/New_York spring-forward normalization. `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` casts both source endpoints through `TIMESTAMPTZ`, lines 61-65 write only those transformed values, and line 20 builds the opaque UUID from `stay_id-orderid-itemid` without either original timestamp, so a genuine 03:28 and a normalized 02:28 cannot be distinguished from served FHIR.
