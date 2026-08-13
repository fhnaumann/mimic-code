## ICU MedicationAdministration does not serialize inputevent linkorderid or patientweight
- Affected: `MedicationAdministration.identifier`, `MedicationAdministration.supportingInformation`, `MedicationAdministration.dosage`, and source `inputevents.linkorderid`/`patientweight`
- Verified: phenylephrine embedded Pathling/Spark probe over the authoritative demo Delta found `identifier.value` and `supportingInformation.reference` 0/625 target rows and 0/20,404 ICU resources; source DuckDB target had `linkorderid` and `patientweight` non-null on 625/625. The ICU ETL at `mimic-fhir/sql/fhir_medication_administration_icu.sql:19-23,38-100` writes neither value.

## ICU MedicationAdministration effective[x] selects Period or endtime dateTime by rate presence
- Affected: `MedicationAdministration.effective[x]`
- Verified: phenylephrine embedded Pathling/Spark probe found target `221749` Period.start/end 625/625 and dateTime 0/625; the complete ICU stream had Period.start/end 11,038/20,404 and dateTime 9,366/20,404, matching `mimic-fhir/sql/fhir_medication_administration_icu.sql:61-69`.

## ICU MedicationAdministration has one medication coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: phenylephrine embedded Pathling/Spark projection found exact system/code `mimic-medication-icu`/`221749` on 625 rows for 625 distinct resources; the complete ICU system was 20,404/20,404 and all MedicationAdministration codings were 56,535/56,535, each ratio 1.000.

## ICU MedicationAdministration Quantity values are served at decimal scale six
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: the embedded Pathling 9.6.0 Delta schema reported both raw values as `decimal(32,6)`; phenylephrine DuckDB/Delta equality join found rate within `1e-6` on 625/625 and amount within `1e-6` on 591/625 after FLOAT casts.

## ICU MedicationAdministration omits patientweight needed for weight-normalized rates
- Affected: `MedicationAdministration.dosage.rateQuantity` and concepts deriving `inputevents.rate / inputevents.patientweight`
- Verified: phenylephrine attempt_0001 full-data judge review confirmed the exhaustive ETL projection/resource construction at `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` preserves raw `rate`/`rateuom` but no `patientweight`; canonical `mimic-iv/concepts/medication/phenylephrine.sql:5-7` requires that denominator for `mcg/min` rows, making the clinically meaningful normalized rate unrecoverable.
