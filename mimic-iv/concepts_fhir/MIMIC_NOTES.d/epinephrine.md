## ICU MedicationAdministration has no inputevent identifier or linkorderid
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: epinephrine embedded Pathling/Spark probe over the authoritative demo Delta counted 0/56,535 MedicationAdministration resources with a non-empty `identifier` array and 0/20,404 ICU medication resources; `mimic-fhir/sql/fhir_medication_administration_icu.sql:19-23,38-69` writes no identifier, `orderid`, or `linkorderid`.

## ICU MedicationAdministration effective[x] selects Period or endtime dateTime by rate presence
- Affected: `MedicationAdministration.effective[x]`
- Verified: `mimic-fhir/sql/fhir_medication_administration_icu.sql:61-69` writes `effectivePeriod` from source start/end when rate is non-null and `effectiveDateTime` from source endtime otherwise; the authoritative Delta ICU stream had 11,038 Period and 9,366 dateTime resources, while epinephrine had Period.start/end 36/36 and dateTime 0/36.

## ICU MedicationAdministration Quantity values are stored at decimal scale six
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: the embedded Pathling 9.6.0 raw Delta schema reports both fields as `decimal(32,6)`; the epinephrine target had 36/36 dose and rate values and DuckDB/FHIR FLOAT agreement within `1e-6` on all 36 rows.

## MedicationAdministration medication coding is one coding per resource in the served Delta
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: an unfiltered coding `forEach` over the authoritative Delta returned 56,535 coding rows for 56,535 distinct resource keys; the ICU system returned 20,404/20,404 and epinephrine code `221289` returned 36/36.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: `CodeSystem` terminology resources and validation of medication codes against a served CodeSystem
- Verified: embedded Pathling `src.read('CodeSystem')` raised `No data found for resource type: CodeSystem`; the epinephrine coding was nevertheless present as `MedicationAdministration.medication.coding` under the exact ICU system/code, and `mimic-fhir/sql/codesystem/cs-medication-icu.sql:10-15` shows the ETL terminology source is `d_items`.
