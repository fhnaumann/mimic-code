# Mismatch diagnostician evidence

Concept: `dobutamine`  
Attempt: `0002`  
Classification: upstream transformation loss; no retry required

The diagnostician inspected the full comparison, both ViewDefinitions,
`concept.sql`, `unrepresentable.json`, the canonical source, carryover
analyses, curated notes/fragments, and the relevant upstream ETL.

The residual `only_candidate`/`only_oracle` rows are the same administration
whose natural key was changed by DST normalization: oracle
`(stay_id=37725403, starttime=2165-03-10 02:28)` versus candidate `03:28`.
The adjacent endtime conflict is the same transformation. The upstream
statement is `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,
61-65`, which casts both source endpoints through `TIMESTAMPTZ` and writes
only the transformed values to `MedicationAdministration.effectivePeriod`.
Line 20 constructs an opaque UUID from `stay_id-orderid-itemid`, so it does
not preserve either source timestamp; no FHIR query can recover the original
wall time or distinguish it from a genuine 03:28 administration.

The port itself uses the exact medication system/code, correct cardinality,
ICU Encounter identifier join, both effective choices, and
`TIMESTAMP_NTZ`; no fix is indicated and no carryover stage was invalidated.

The diagnostician appended this dataset-wide finding to the owned fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/dobutamine.md`, heading
`ICU MedicationAdministration effective periods irreversibly normalize
DST-gap wall times`.
