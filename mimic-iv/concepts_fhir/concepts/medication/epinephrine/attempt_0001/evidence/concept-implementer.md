# Concept-implementer evidence

The implementer read the contract, coding policy, curated notes, all current
notes fragments, both epinephrine carryover analyses, the oracle manifest, and
proven medication ViewDefinitions. It created the frozen implementation
artifacts:

- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

The MedicationAdministration ViewDefinition filters the exact ICU medication
coding system and source code `221289`, projects the resource and Encounter
reference support keys, both effective[x] variants, and Quantity dose/rate
values. The Encounter ViewDefinition selects the ICU identifier system for
`stay_id`. SQL preserves all selected rows, left-joins Encounter, emits typed
NULL INTEGER for unrepresentable `linkorderid`, casts quantities to FLOAT, and
parses/coalesces FHIR datetimes with TIMESTAMP_NTZ. Static JSON, label, and SQL
checks passed. No new dataset-wide note was appended and no prior artifact was
edited or committed.
