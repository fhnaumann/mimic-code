## Evidence

Concept: `enzyme`.

The prober read the source carryover, loop contract, curated MIMIC notes, relevant provisional lab fragments, demo Delta via embedded Pathling/Spark, and upstream FHIR ETL SQL. It wrote and recorded reusable mapping at `mimic-iv/concepts_fhir/carryover/enzyme/fhir-prober.md`.

The authoritative Observation code system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`; all eleven source itemids were present and must be filtered as exact strings with system before casting. Quantity values are materialized string-like and require DOUBLE casts. The probe found 5,825 targeted observations, 5,792 positive numeric source-equivalent rows, and 1,411 positive specimen groups. All positive rows had specimen references; hospital Encounter references were present on 4,036/5,792 positive rows. Specimen identifiers provide the grouping spine, Patient identifier values provide `subject_id`, and hospital Encounter identifier values provide nullable `hadm_id` via LEFT JOIN.

The probe verified exact demo aggregate agreement for all 1,411 groups, including all eleven analytes and grouped `hadm_id`. Specimen collection MAX charttime matched the filtered source MAX on all groups before FHIR serialization; one DST-gap timestamp was shifted by the upstream ETL from 02:52 to 03:52. DateTime is populated on all targeted observations; instant and Period variants are absent. No new dataset-wide quirk was found and nothing was appended to `MIMIC_NOTES.d/enzyme.md`.

No ViewDefinition, concept SQL, or commit was created at this stage.
