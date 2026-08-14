# Evidence: fhir-prober (reused carryover)

The reusable FHIR mapping was read from `mimic-iv/concepts_fhir/carryover/oxygen_delivery/fhir-prober.md`. It maps chartevents Observations by the exact chartevents coding system and code, linked Patient/ICU Encounter identifiers, effective dateTime, Quantity values, categorical valueString, and issued/storetime. It verifies repeated same-item resources and preserves the `(subject_id, charttime)` grouping semantics. No new FHIR probe was spawned because carryover was valid.
