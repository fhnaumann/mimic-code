## Evidence block — `vasopressin`

Read `MIMIC_NOTES.md`, canonical Observation ViewDefinition, source analysis, ICU MedicationAdministration ETL, and provisional fragments: `dobutamine`, `dopamine`, `epinephrine`, `milrinone`, `norepinephrine`, `phenylephrine`, `icustay_times`, and `README`. Sibling claims were independently verified against the demo Delta; none was adopted solely as fact.

Source table mapping: `mimiciv_icu.inputevents` → `MedicationAdministration`; identifier joins use `MedicationAdministration.context` → `Encounter`, with an optional subject join to `Patient`.

Verified mappings: medication coding filter system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`, code `222315`, display `Vasopressin`; `context.getReferenceKey(Encounter)` joined to `Encounter.getResourceKey()` and ICU encounter identifier value for `stay_id`; Patient reference and patient identifier for `subject_id`; `dosage.rate` Quantity value/unit and `dosage.dose` Quantity value; both effective Period endpoints plus effective dateTime fallback, coalesced and cast to `TIMESTAMP_NTZ`. Quantity aliases materialize as strings and raw values are decimal(32,6). `linkorderid` has no FHIR equivalent and must be a typed NULL; `orderid` and resource keys are opaque and cannot be inverted.

Demo verification found 55 source rows and 55 FHIR rows, 55/55 common `(stay_id,starttime)` keys, no unmatched or duplicate keys, endtime agreement 55/55, rate agreement within tolerance 55/55 (maximum absolute difference `4.74945068163e-7`), and amount agreement within tolerance 55/55 (maximum absolute difference `2.00000000206e-6`). All target rows used effectivePeriod; effectiveDateTime was 0/55. Source `rateuom` was `units/hour` on 55/55; `units/min` was 0/55.

Dataset-wide findings appended to `MIMIC_NOTES.d/vasopressin.md`: missing `linkorderid`, one coding per ICU MedicationAdministration, six-decimal Quantity precision, and absent CodeSystem resources. Carryover was written and recorded at `mimic-iv/concepts_fhir/carryover/vasopressin/fhir-prober.md` and `carryover.json`. No implementation or commit was performed.
