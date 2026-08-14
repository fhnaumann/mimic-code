## ICU MedicationAdministration does not serialize inputevent linkorderid
- Affected: `MedicationAdministration.identifier` and the source `inputevents.linkorderid` linkage
- Verified: vasopressin attempt_0001 embedded Pathling probe over the authoritative demo Delta found identifier non-empty on 0/56,535 MedicationAdministration resources, while the DuckDB target query found `linkorderid` non-null on 55/55 `itemid=222315` rows; `mimic-fhir/sql/fhir_medication_administration_icu.sql:19-23,38-69` writes no identifier.

## ICU MedicationAdministration has one medication coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: vasopressin attempt_0001 embedded Pathling `forEach: medication.ofType(CodeableConcept).coding` projection returned 56,535 coding rows for 56,535 distinct resources overall, 20,404/20,404 for the ICU medication system, and 55/55 for code `222315`.

## ICU MedicationAdministration dosage Quantity values are decimal(32,6) in served Delta
- Affected: `MedicationAdministration.dosage.dose.value` and `MedicationAdministration.dosage.rateQuantity.value`
- Verified: vasopressin attempt_0001 embedded Pathling 9.6.0 schema reported both raw Quantity values as `decimal(32,6)`; the materialized ViewDefinition aliases were string-like and the 55-row DuckDB comparison agreed within `rtol=1e-6, atol=1e-6` for both rate and amount.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: `CodeSystem` terminology resources and served validation of ICU medication codes
- Verified: vasopressin attempt_0001 `src.read("CodeSystem")` raised `No data found for resource type: CodeSystem`; the exact system/code was instead observed on 55/55 target MedicationAdministration codings and is sourced by `mimic-fhir/sql/codesystem/cs-medication-icu.sql` from `d_items`.
