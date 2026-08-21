Concept `suspicion_of_infection`; fhir-prober evidence.

Mappings and checks:

- The completed `antibiotic` dependency is sourced through MedicationRequest/Medication/Patient/hospital Encounter/ICU Encounter.
- `subject_id`, `hadm_id`, and nullable `stay_id` map from the respective MIMIC identifier systems and are cast from identifier strings to integers; dependency resource keys are retained for equality joins.
- Antibiotic drug names map from the `mimic-medication-name` Medication identifier. Start/stop times map from MedicationRequest validity-period endpoints and are cast to `TIMESTAMP_NTZ`.
- `micro_specimen_id` maps from Specimen identifier system `.../identifier/specimen-micro`. Micro-test Observations use the microbiology-test code system, subject Patient reference, Specimen reference, dateTime effective time, and `hasMember` references to microbiology-organism Observations. Organism code/system/display and Specimen type/collection are projected as needed.
- Confirmed demo counts: micro-test 1,893 resources/codings, micro-organism 338, micro susceptibility 1,036 (unused), Specimens 1,336, and 227 positive specimen groups; all relevant per-code/group checks matched the DuckDB source. The literal `org_itemid != 90856` filter had zero source and FHIR matches in demo. Forty-five date-only specimen cultures had absent collection dateTime in both source/FHIR characterization.
- Dependency probe: 17,552 MedicationRequests, 15,225 pharmacy-backed, 14,574 validity periods, 1,480 name-bearing Medications, 314 mixes with 634 ingredient references. Invalid/reversed dependency validity periods caused 48/903 demo antibiotic rows to lack FHIR start/end; 31 also lacked stay_id, affecting 602 suspicion rows across 25 subjects. This is evidence for the full-data judge, not an early terminal decision. `prescriptions.drug_type` is absent and inherited from the dependency boundary.
- Resource IDs were used only for equality joins; none were parsed, regenerated, hardcoded, or used to infer source values.

The agent read `MIMIC_NOTES.md` and all supplied sibling fragments as provisional leads; it did not edit the curated notes file. It appended two dataset-wide findings to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/suspicion_of_infection.md`: microbiology Specimen identifiers carry `micro_specimen_id`, and absent Specimen collection dateTime identifies date-only cultures.

Reusable mapping artifact: `mimic-iv/concepts_fhir/carryover/suspicion_of_infection/fhir-prober.md`.
