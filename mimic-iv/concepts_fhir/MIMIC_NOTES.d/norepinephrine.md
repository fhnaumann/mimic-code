## ICU MedicationAdministration does not serialize inputevent patientweight
- Affected: `MedicationAdministration.dosage`, `MedicationAdministration.supportingInformation`, and the source `inputevents.patientweight` value
- Verified: norepinephrine embedded Pathling/Spark probe over the authoritative demo Delta found source `patientweight` non-null on 947/947 `itemid=221906` rows, while no served `MedicationAdministration` resource had populated `supportingInformation` (0/56,535) or an alternate dosage weight field; the raw Delta schema contains no `patientweight` element. The missing value can affect the source `mg/kg/min` rate branch, although that branch was unexercised for norepinephrine (0/947).

## ICU MedicationAdministration does not serialize inputevent linkorderid
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: norepinephrine embedded Pathling/Spark probe over the authoritative demo Delta found no populated identifier array on 56,535/56,535 MedicationAdministration resources, including 0/947 target resources; the norepinephrine DuckDB source had `linkorderid` non-null on 947/947 rows and 184 distinct values.

## ICU MedicationAdministration effective[x] conditionally encodes inputevent timing
- Affected: `MedicationAdministration.effective[x]`
- Verified: norepinephrine embedded Pathling/Spark probe found target `221906` Period.start/end on 947/947 and dateTime on 0/947; the complete ICU stream had 11,038 Period resources and 9,366 dateTime resources, matching the ETL rule that non-null rate writes Period(start,end) while null rate writes dateTime(endtime).

## ICU MedicationAdministration Quantity values are served at decimal scale six
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: the authoritative Delta schema reported both fields as `decimal(32,6)`; norepinephrine DuckDB/Delta comparison found rate and amount within `1e-6` on 947/947 after FLOAT casts, but bitwise exact on only 1/947 and 2/947 respectively.

## ICU MedicationAdministration has one medication coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: norepinephrine embedded Pathling/Spark coding projection found 947 rows for exact system/code `mimic-medication-icu`/`221906` and 947 distinct target resources; the complete ICU stream was 20,404/20,404, ratio 1.000.

## ICU MedicationAdministration does not serialize inputevent linkorderid (full-data confirmation)
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: norepinephrine attempt_0001 full-data review covered 336,000 oracle and 336,000 candidate rows; `linkorderid` was non-null on all 336,000 source rows but necessarily NULL on all candidate rows. `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-23,38-100` reads and serializes timing, amount, rate, itemid, subject and ICU context but never selects or writes `linkorderid` or an `identifier`; line 20 uses source `orderid` only inside the opaque resource UUID and provides no recoverable linkage value. The comparator marked its keyed diff VOID because declared `linkorderid` is in manifest key `(linkorderid,starttime)`.

## ICU MedicationAdministration trims inputevent dosage units before serialization
- Affected: `MedicationAdministration.dosage.rateQuantity.unit`, `MedicationAdministration.dosage.dose.unit`, and source `inputevents.rateuom`/`amountuom` discriminators
- Verified: norepinephrine attempt_0002 implementation review of `mimic-fhir/sql/fhir_medication_administration_icu.sql:13-15,85-99` confirmed the ETL applies `TRIM` before writing both FHIR unit fields; the reusable Delta probe also found `mcg/kg/min` and `mg` on all 947 target rows.
