# Evidence: fhir-prober (reused carryover)

The FHIR mapping was reused from `mimic-iv/concepts_fhir/carryover/inflammation/fhir-prober.md` under the controller's carryover ledger. It maps item `50889` under the exact `mimic-d-labitems` coding system to laboratory `Observation` resources; joins Observation subject/specimen/encounter reference keys to `Patient`, `Specimen`, and hospital `Encounter` identifier spines; filters only positive Quantity values with no comparator; groups by the lab Specimen identifier; and uses a LEFT join for nullable `hadm_id`. FHIR dateTime values are cast directly to `TIMESTAMP_NTZ`. Resource keys are retained for output as required by the reopened instruction.

Artifact reused: `mimic-iv/concepts_fhir/carryover/inflammation/fhir-prober.md`.
