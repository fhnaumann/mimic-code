## ICU MedicationAdministration uses `context` for the Encounter reference
- Affected: `MedicationAdministration.context` and ICU medication administration Encounter joins
- Verified: norepinephrine_equivalent_dose attempt_0001 embedded Pathling probe over the authoritative Delta exposed `context.getReferenceKey(Encounter)` on all 20,404 ICU-coded MedicationAdministration resources and all 1,750 selected vasoactive resources; the raw resource schema has `context` and no `encounter` field.

## ICU MedicationAdministration has one medication coding per resource in the served Delta
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: norepinephrine_equivalent_dose attempt_0001 projected `medication.ofType(CodeableConcept).coding` and found 56,535 coding rows for 56,535 distinct MedicationAdministration keys overall, 20,404/20,404 for the ICU system, and 1,750/1,750 for the seven vasoactive codes.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: served `CodeSystem` resources and validation of ICU medication codes through a served terminology resource
- Verified: norepinephrine_equivalent_dose attempt_0001 embedded Pathling `src.read("CodeSystem")` raised `IllegalArgumentException: No data found for resource type: CodeSystem`; the seven exact codes were instead confirmed on served MedicationAdministration codings and `mimiciv_icu.d_items`.

## ICU MedicationAdministration does not serialize inputevent patientweight
- Affected: `MedicationAdministration.dosage`, `MedicationAdministration.supportingInformation`, and source `mimiciv_icu.inputevents.patientweight`
- Verified: norepinephrine_equivalent_dose attempt_0001 DuckDB source probe found patientweight non-null on all 1,750 selected inputevent rows, while the served MedicationAdministration schema had no patientweight element and `supportingInformation.reference` was populated on 0/1,750 selected resources and 0/20,404 ICU resources.

## ICU MedicationAdministration trims inputevent Quantity unit strings before serialization
- Affected: `MedicationAdministration.dosage.rateQuantity.unit`, `MedicationAdministration.dosage.rateQuantity.code`, `MedicationAdministration.dosage.dose.unit`, `MedicationAdministration.dosage.dose.code`, and source `inputevents.rateuom`/`amountuom`
- Verified: norepinephrine_equivalent_dose attempt_0001 checked `mimic-fhir/sql/fhir_medication_administration_icu.sql:13-15,85-99` and matched source/FHIR rate and amount units on all 1,750 selected rows; the Delta probe found the seven selected streams use `mcg/kg/min` or `units/hour` for rate and `mg` or `units` for amount.

## ICU MedicationAdministration omits `inputevents.patientweight` needed for weight-normalized rates
- Affected: `MedicationAdministration.dosage.rateQuantity` and canonical branches deriving `inputevents.rate / inputevents.patientweight`
- Verified: norepinephrine_equivalent_dose attempt_0003 full-data judge review confirmed the exhaustive upstream projection/resource construction at `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` carries no patientweight or exact equivalent; the downstream divergence included one missing phenylephrine-dependent interval, while `mimic-iv/concepts/medication/phenylephrine.sql:5-7` requires the denominator for `mcg/min` rows.
