## ICU MedicationAdministration has no inputevent identifier or linkorderid
- Affected: `MedicationAdministration.identifier` and recovery of `mimiciv_icu.inputevents.linkorderid`
- Verified: milrinone embedded Pathling/Spark probe over the authoritative Delta counted non-empty `identifier` on 0/20,404 ICU MedicationAdministration resources and 0/15 itemid `221986` resources; the ICU ETL writes no inputevent identifier or `linkorderid`.

## ICU MedicationAdministration coding is one coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: milrinone embedded Pathling/Spark probe counted 20,404 ICU coding rows for 20,404 distinct ICU resources and 15 rows for 15 distinct `221986` resources; ratios were 1.000 in both projections.

## ICU MedicationAdministration Quantity values are served at decimal scale six
- Affected: `MedicationAdministration.dosage.rateQuantity.value` and `MedicationAdministration.dosage.dose.value`
- Verified: milrinone embedded Pathling 9.6.0 schema reported both raw Delta fields as `decimal(32,6)`; all 15 target rate and amount values were within `1e-6` of the DuckDB source after FLOAT casts, but 0/15 were bitwise exact for either field.

## CodeSystem resources are absent from the authoritative Delta warehouse
- Affected: `CodeSystem` terminology resources and validation of ICU medication codes against a served CodeSystem
- Verified: milrinone embedded Pathling `src.read('CodeSystem')` raised `No data found for resource type: CodeSystem`; code `221986` was instead confirmed from served MedicationAdministration coding and DuckDB `d_items`.

## ICU MedicationAdministration effective times are normalized through TIMESTAMPTZ
- Affected: `MedicationAdministration.effectivePeriod.start`, `.end`, and rate-null `effectiveDateTime`
- Verified: milrinone attempt_0001 full-data comparison replayed all 2 endtime conflicts and both shifted `(stay_id,starttime)` key pairs as the America/New_York DST-gap transformation; upstream `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` casts and writes the effective endpoints, with zero residual after replay.
