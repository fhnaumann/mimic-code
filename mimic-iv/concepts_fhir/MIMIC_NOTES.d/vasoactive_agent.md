## ICU MedicationAdministration omits inputevent patientweight
- Affected: `MedicationAdministration.dosage`, `MedicationAdministration.supportingInformation`, and source `mimiciv_icu.inputevents.patientweight`
- Verified: vasoactive_agent attempt_0001 embedded Pathling 9.6.0 probe over the authoritative Delta found no `patientweight` field in the raw dosage schema and `supportingInformation.reference` populated on 0/56,535 MedicationAdministration resources; all 1,750 vasoactive source rows had non-NULL patientweight.

## ICU MedicationAdministration trims inputevent unit strings before serialization
- Affected: `MedicationAdministration.dosage.rateQuantity.unit`, `MedicationAdministration.dosage.rateQuantity.code`, `MedicationAdministration.dosage.dose.unit`, `MedicationAdministration.dosage.dose.code`, and source `inputevents.rateuom`/`amountuom`
- Verified: vasoactive_agent attempt_0001 read `mimic-fhir/sql/fhir_medication_administration_icu.sql:13-15,85-99`, which applies `TRIM` before writing both Quantity units/codes; the Delta probe matched source units on all 1,750 target rows and found no padded demo unit values.

## ICU MedicationAdministration has one medication coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: vasoactive_agent attempt_0001 embedded Pathling probe counted 56,535 coding rows for 56,535 distinct MedicationAdministration keys overall and 20,404/20,404 for the ICU medication system; each of the seven target codes also had one coding per resource.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: served `CodeSystem` terminology resources and validation of ICU medication codes through a served CodeSystem
- Verified: vasoactive_agent attempt_0001 embedded Pathling `src.read("CodeSystem")` raised `No data found for resource type: CodeSystem`; the seven exact system/code pairs were instead confirmed directly on served MedicationAdministration codings and the DuckDB `d_items` dimension.
