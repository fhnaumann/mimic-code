# Mismatch diagnostician evidence

- Concept: `phenylephrine`; attempt: `0002`.
- Diagnosis: proceed to the equivalence judge; no implementation retry and no carryover invalidation.
- The Period mapping is correct: ICU ETL writes rate-bearing `effectivePeriod.start/end` at `mimic-fhir/sql/fhir_medication_administration_icu.sql:61-66`, with dateTime fallback at `:68-69`.
- `vaso_amount` is sourced from `dosage.dose.value`, written from `inputevents.amount` at `mimic-fhir/sql/fhir_medication_administration_icu.sql:12,85-90`; the served Quantity precision is limited to decimal scale six.
- The 46 machine-attributed timestamp conflicts are consistent with the upstream `TIMESTAMPTZ` cast at `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`; pre-cast wall times are unrecoverable.
- The remaining stay-only residual conflicts are pairing amplification in the unkeyed comparator from timestamp/Quantity multiset/order perturbations, not evidence of a Period or SQL mapping bug.
- `patientweight` is absent from the ETL projection (`:7-23,38-100`) while `rateuom` survives (`:91-98`), so the one `mcg/min` row is correctly emitted as typed NULL `vaso_rate`; `linkorderid` is also absent and correctly typed NULL.
- Curated notes were checked; the provisional phenylephrine fragment lead was independently verified and not cited. No dataset-wide fragment entry was appended and no carryover stage was invalidated.
